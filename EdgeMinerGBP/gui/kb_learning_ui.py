"""Giao diện Huấn luyện KB — era cards + lịch sử báo cáo."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from gui.app_settings import LEARNING_ERA_OPTIONS, get_settings, resolve_learning_eras
from gui.kb_learning_store import (
  archive_learning_report,
  history_for_profile,
  load_archived_report,
  load_history_index,
)
from gui.long_task_background import start_job
from gui.long_task_ui import render_task_status, task_blocks_ui
from gui.services import load_learning_report
from kb_profiles import get_profile, list_snapshots


def _inject_kb_css():
  st.markdown(
    """
    <style>
    .kb-era-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 0.75rem;
      margin: 0.5rem 0 1rem;
    }
    .kb-era-card {
      border-radius: 12px;
      padding: 1rem;
      border: 1px solid rgba(128,128,128,0.28);
      background: rgba(52,152,219,0.06);
    }
    .kb-era-card.done { border-left: 4px solid #2ecc71; }
    .kb-era-card.partial { border-left: 4px solid #f39c12; }
    .kb-era-card.empty { border-left: 4px solid #95a5a6; }
    .kb-era-title { font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem; }
    .kb-era-meta { font-size: 0.82rem; opacity: 0.8; line-height: 1.45; }
    .kb-era-badge {
      display: inline-block; margin-top: 0.45rem; padding: 0.15rem 0.5rem;
      border-radius: 6px; font-size: 0.78rem; font-weight: 600;
    }
    .kb-era-badge.done { background: rgba(46,204,113,0.2); color: #2ecc71; }
    .kb-era-badge.partial { background: rgba(243,156,18,0.2); color: #f39c12; }
    .kb-era-badge.empty { background: rgba(149,165,166,0.2); color: #bdc3c7; }
    </style>
    """,
    unsafe_allow_html=True,
  )


def _era_status(era: dict, loops_needed: int) -> dict:
  pid = era["kb_profile"]
  p = get_profile(pid) or {}
  have = int(p.get("epochs") or 0) if p.get("exists") else 0
  snaps = [s for s in list_snapshots(pid, include_latest=False) if s.get("cumulative")]
  if have >= loops_needed:
    state, label = "done", f"✅ Đủ {have}/{loops_needed} vòng"
    css = "done"
  elif have > 0:
    state, label = "partial", f"⚠️ {have}/{loops_needed} vòng"
    css = "partial"
  else:
    state, label = "empty", "○ Chưa học"
    css = "empty"
  last_run = history_for_profile(pid)
  last_r = last_run[0].get("last_total_r") if last_run else None
  return {
    "profile_id": pid,
    "epochs_have": have,
    "epochs_need": loops_needed,
    "state": state,
    "label": label,
    "css": css,
    "snapshots": len(snaps),
    "last_r": last_r,
    "trained_from": p.get("trained_from"),
    "trained_to": p.get("trained_to"),
  }


def _epoch_chart(history: list[dict], *, key: str):
  if not history:
    return
  epochs = [h.get("epoch", i + 1) for i, h in enumerate(history)]
  fig = go.Figure()
  fig.add_trace(go.Scatter(
    x=epochs, y=[h.get("win_rate_pct", 0) for h in history],
    name="WR%", line=dict(color="#3498db", width=2),
  ))
  fig.add_trace(go.Scatter(
    x=epochs, y=[h.get("total_r", 0) for h in history],
    name="Total R", yaxis="y2", line=dict(color="#2ecc71", width=2),
  ))
  fig.update_layout(
    title="Tiến bộ qua từng vòng",
    height=300,
    margin=dict(l=40, r=40, t=45, b=35),
    yaxis=dict(title="WR%"),
    yaxis2=dict(title="R", overlaying="y", side="right"),
    legend=dict(orientation="h", y=1.12),
  )
  st.plotly_chart(fig, use_container_width=True, key=key)


def _render_era_cards(eras: list[dict], loops: int):
  cards_html = '<div class="kb-era-grid">'
  for era in eras:
    stt = _era_status(era, loops)
    r_txt = f"+{stt['last_r']:.1f}R" if stt["last_r"] is not None else "—"
    cards_html += (
      f'<div class="kb-era-card {stt["css"]}">'
      f'<div class="kb-era-title">{era["label"]}</div>'
      f'<div class="kb-era-meta">Học: {era["learn_from"]} → {era["learn_until"]}<br/>'
      f'Profile: <code>{stt["profile_id"]}</code><br/>'
      f'Lần học gần nhất: <b>{r_txt}</b></div>'
      f'<span class="kb-era-badge {stt["css"]}">{stt["label"]}</span>'
      f'</div>'
    )
  cards_html += "</div>"
  st.markdown(cards_html, unsafe_allow_html=True)

  st.markdown("**Chọn era để học**")
  cols = st.columns(min(len(eras), 3))
  for i, era in enumerate(eras):
    stt = _era_status(era, loops)
    with cols[i % len(cols)]:
      if st.button(
        f"▶ {era['label']}",
        key=f"kb_pick_{era['kb_profile']}",
        use_container_width=True,
        type="primary" if stt["state"] != "done" else "secondary",
      ):
        st.session_state["kb_selected_era_key"] = era["key"]
        st.session_state["kb_era_select"] = era["key"]
        st.rerun()


def _default_era_index(eras: list[dict], loops: int) -> int:
  pick = st.session_state.get("kb_selected_era_key")
  keys = [e["key"] for e in eras]
  if pick in keys:
    return keys.index(pick)
  for i, era in enumerate(eras):
    if _era_status(era, loops)["state"] != "done":
      return i
  return 0


def _render_train_form(eras: list[dict], loops: int):
  st.markdown("#### Chạy huấn luyện")
  running = task_blocks_ui("hub_learn")
  render_task_status(key_prefix="hub_learn")

  era_keys = [e["key"] for e in eras]
  idx = _default_era_index(eras, loops)
  pick_key = st.selectbox(
    "Giai đoạn học",
    era_keys,
    index=idx,
    format_func=lambda k: next(e["label"] for e in eras if e["key"] == k),
    key="kb_era_select",
    help="Chọn era từ Cài đặt — ngày học & profile khóa theo era.",
  )
  st.session_state["kb_selected_era_key"] = pick_key
  era = next(e for e in eras if e["key"] == pick_key)
  stt = _era_status(era, loops)

  st.info(
    f"**{era['label']}** · profile `{era['kb_profile']}` · "
    f"học **{era['learn_from']} → {era['learn_until']}** · {stt['label']}"
  )

  c1, c2, c3 = st.columns(3)
  c1.metric("Profile ID", era["kb_profile"])
  c2.metric("Học từ", era["learn_from"])
  c3.metric("Học đến", era["learn_until"])

  c4, c5 = st.columns(2)
  with c4:
    epochs = st.number_input(
      "Số vòng học",
      1, 12,
      loops,
      key="kb_form_epochs_input",
      help=f"Mặc định {loops} theo Cài đặt",
    )
  with c5:
    reset = st.checkbox("Reset profile trước khi học", key="kb_form_reset")

  if stt["epochs_have"] > 0 and not reset:
    st.caption(
      f"Profile đã có **{stt['epochs_have']}** vòng — học tiếp sẽ **cộng dồn** "
      "(bật Reset để học lại từ đầu)."
    )

  if st.button("▶ Bắt đầu học", type="primary", key="kb_run_learn", disabled=running):
    try:
      start_job(
        "learning",
        {
          "epochs": int(epochs),
          "reset_kb": reset,
          "kb_profile": era["kb_profile"],
          "kb_name": era["label"],
          "from_date": era["learn_from"],
          "until_date": era["learn_until"],
        },
        label=f"Học KB · {era['kb_profile']}",
      )
      st.toast("Đã bắt đầu học KB (chạy nền)")
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))


def _render_history():
  runs = load_history_index()
  st.markdown("#### Lịch sử học (không mất khi học era mới)")
  if not runs:
    st.caption("_Chưa có lịch sử — sau mỗi lần học, báo cáo được lưu tự động._")
    return

  import pandas as pd
  df = pd.DataFrame(runs)
  show_cols = [c for c in [
    "archived_at", "kb_profile", "epochs", "trained_from", "trained_to",
    "last_total_r", "last_win_rate_pct", "genomes",
  ] if c in df.columns]
  st.dataframe(
    df[show_cols].rename(columns={
      "archived_at": "Thời gian",
      "kb_profile": "Profile",
      "epochs": "Vòng",
      "trained_from": "Từ",
      "trained_to": "Đến",
      "last_total_r": "R (vòng cuối)",
      "last_win_rate_pct": "WR%",
      "genomes": "Genomes",
    }),
    use_container_width=True,
    hide_index=True,
    height=min(280, 80 + len(runs) * 36),
  )

  labels = {
    r["run_id"]: f"{r.get('archived_at', '')[:16]} · {r.get('kb_profile')} · {r.get('last_total_r', 0):+.1f}R"
    for r in runs
  }
  pick = st.selectbox("Xem báo cáo đã lưu", list(labels.keys()), format_func=lambda k: labels[k], key="kb_hist_pick")
  rep = load_archived_report(pick)
  if not rep:
    return
  hist = rep.get("epoch_history") or []
  if hist:
    import pandas as pd
    st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
    _epoch_chart(hist, key=f"kb_hist_chart_{pick}")
  summary = rep.get("kb_summary") or {}
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Genomes", summary.get("genomes", "—"))
  c2.metric("Rules", summary.get("rules", "—"))
  c3.metric("ML samples", summary.get("ml_samples", "—"))
  c4.metric("Best fitness", round(summary.get("best_fitness", 0), 1))


def _render_latest_report():
  learning = st.session_state.get("learning_report") or load_learning_report()
  if not learning:
    return
  st.markdown("#### Báo cáo mới nhất")
  st.caption(
    f"**{learning.get('kb_profile')}** · "
    f"{learning.get('trained_from')} → {learning.get('trained_to')} · "
    f"{learning.get('epochs')} vòng"
  )
  hist = learning.get("epoch_history") or []
  if hist:
    import pandas as pd
    st.dataframe(pd.DataFrame(hist), use_container_width=True, hide_index=True)
    _epoch_chart(hist, key="kb_latest_chart")


def render_kb_training_page():
  """Trang huấn luyện KB — thay thế UI cũ."""
  _inject_kb_css()
  s = get_settings()
  loops = int(s.get("learning_loops") or 4)
  eras = resolve_learning_eras(s)

  st.markdown(
    "Huấn luyện **bộ nhớ kinh nghiệm** cho từng giai đoạn. "
    "Mỗi era = một profile KB riêng — cần đủ vòng học trước khi **Grid Search**."
  )
  st.caption(
    f"Cài đặt: **{loops} vòng/era** · OOS kiểm chứng **{s.get('backtest_from')} → {s.get('backtest_to')}**"
  )

  from gui.grid_search_engine import grid_readiness
  r = grid_readiness()
  if r["kb_complete"]:
    st.success(f"✅ Sẵn sàng Grid Search — **{r['ready_combos']}/{r['expected_combos']}** combo")
  else:
    st.warning(
      f"Chưa đủ KB cho Grid — **{r['ready_combos']}/{r['expected_combos']}** combo. "
      "Học đủ vòng cho mỗi era bên dưới."
    )

  if not eras:
    st.error("Chưa chọn giai đoạn học — vào **Cài đặt**.")
    return

  _render_era_cards(eras, loops)

  tab_run, tab_hist, tab_latest = st.tabs(["▶ Chạy học", "📁 Lịch sử báo cáo", "🕐 Mới nhất"])

  with tab_run:
    _render_train_form(eras, loops)

  with tab_hist:
    _render_history()

  with tab_latest:
    _render_latest_report()
    if st.button("Lưu bản mới nhất vào lịch sử", key="kb_archive_latest"):
      lr = load_learning_report()
      if lr:
        rid = archive_learning_report(lr, note="manual")
        st.success(f"Đã lưu `{rid}`")
        st.rerun()
      else:
        st.warning("Chưa có learning_report.json")
