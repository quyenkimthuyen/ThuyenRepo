"""KB & Học — tạo KB profile, học epoch."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from kb_profiles import (
  DEFAULT_PROFILE_ID, delete_profile, get_profile, list_disk_profile_ids,
  list_profiles, purge_orphan_snapshots,
)
from gui.components import (
  settings_era_presets, list_kb_profiles_df, suggested_oos_range,
)
from gui.services import load_learning_report
from gui.long_task_background import start_job
from gui.long_task_ui import render_task_status, task_blocks_ui
from gui.trade_profile import format_trade_profile_label, get_active_trade_profile
from gui.ui_preferences import (
  preference_callback,
  restore_widget,
  set_widget_preference,
)
from gui.charts import show_plotly
from gui.workspace import set_active_from_preset, set_active_workspace


def _list_era_profiles():
  from kb_profiles import list_era_profiles
  return list_era_profiles()


def _epoch_chart(history: list[dict], *, title: str = "Tiến bộ qua từng vòng học"):
  if not history:
    return None
  epochs = [h["epoch"] for h in history]
  fig = go.Figure()
  fig.add_trace(go.Scatter(x=epochs, y=[h["win_rate_pct"] for h in history],
                           name="WR%", line=dict(color="#3498db")))
  fig.add_trace(go.Scatter(x=epochs, y=[h["total_r"] for h in history],
                           name="Total R", yaxis="y2", line=dict(color="#2ecc71")))
  fig.update_layout(
    title=title,
    yaxis=dict(title="Tỷ lệ thắng %"),
    yaxis2=dict(title="Tổng R", overlaying="y", side="right"),
    height=320, margin=dict(l=40, r=40, t=50, b=40),
  )
  return fig


def _render_kb_results():
  """Kết quả học — chọn bất kỳ KB profile đã có qua dropdown."""
  from gui.components import _profile_label
  from kb_profiles import get_profile, list_era_profiles, load_kb

  import pandas as pd

  learning = st.session_state.get("learning_report") or load_learning_report()
  profiles = list_era_profiles()
  if not profiles and not learning:
    return

  st.markdown("#### Kết quả học")

  label_to_id: dict[str, str] = {}
  for p in profiles:
    label_to_id[_profile_label(p)] = p["id"]

  # Báo cáo phiên gần nhất có thể trỏ profile chưa kịp vào index era.
  latest_pid = str((learning or {}).get("kb_profile") or "").strip()
  if latest_pid and latest_pid not in label_to_id.values():
    meta = get_profile(latest_pid) or {
      "id": latest_pid,
      "name": latest_pid,
      "trained_from": (learning or {}).get("trained_from"),
      "trained_to": (learning or {}).get("trained_to"),
      "epochs": len((learning or {}).get("epoch_history") or []),
    }
    label_to_id[_profile_label(meta)] = latest_pid

  if not label_to_id:
    st.caption("Chưa có KB để xem — chạy học trước.")
    return

  options = list(label_to_id.keys())
  default_idx = 0
  if latest_pid:
    for i, (label, pid) in enumerate(label_to_id.items()):
      if pid == latest_pid:
        default_idx = i
        break

  restore_widget(
    "hub_result_kb",
    options[default_idx],
    preference_key="training.result_kb",
    options=options,
  )

  picked = st.selectbox(
    "Chọn KB để xem kết quả",
    options,
    key="hub_result_kb",
    on_change=preference_callback("hub_result_kb", "training.result_kb"),
    help="Xem lịch sử vòng học của mọi profile KB đã có.",
  )
  pid = label_to_id[picked]
  meta = get_profile(pid) or {}

  history: list[dict] = []
  source = "kb"
  try:
    kb = load_kb(pid)
    history = list(kb.epoch_history or [])
  except Exception:
    history = []

  if not history and learning and str(learning.get("kb_profile") or "") == pid:
    history = list(learning.get("epoch_history") or [])
    source = "session"

  trained_from = meta.get("trained_from")
  trained_to = meta.get("trained_to")
  is_latest_session = bool(learning and latest_pid == pid)
  if is_latest_session:
    trained_from = trained_from or learning.get("trained_from")
    trained_to = trained_to or learning.get("trained_to")
    st.caption(
      f"Profile **{pid}** · {trained_from or '?'} → {trained_to or '?'} · "
      f"**phiên học gần nhất**"
    )
  else:
    st.caption(
      f"Profile **{pid}** · {trained_from or '?'} → {trained_to or '?'}"
    )

  if not history:
    st.info("Profile này chưa có lịch sử vòng học.")
    return

  st.caption(
    f"{len(history)} vòng · nguồn: "
    + ("file KB" if source == "kb" else "báo cáo phiên gần nhất")
  )
  st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
  from gui.app_settings import kb_profile_label
  chart_name = f"Tiến bộ vòng học · {kb_profile_label(pid)} ({pid})"
  fig = _epoch_chart(history, title=chart_name)
  if fig:
    show_plotly(fig, chart_name, key=f"hub_epoch_chart_{pid}")


def _tab_profiles():
  st.subheader("Danh sách profile bộ nhớ")
  st.caption("_Ẩn «Bộ nhớ chung» (profile cũ) — chỉ hiện giai đoạn era đã học._")
  pdf = list_kb_profiles_df()
  if pdf.empty:
    st.info("Chưa có profile. Dùng tab **Học bộ nhớ** để tạo profile đầu tiên.")
  else:
    show = [c for c in ["giai_doan", "id", "trained_from", "trained_to", "epochs", "exists"] if c in pdf.columns]
    st.dataframe(pdf[show], use_container_width=True, hide_index=True)

  sel = st.selectbox(
    "Xem snapshot epoch của profile",
    [p["id"] for p in list_profiles() if p.get("exists") and p["id"] != DEFAULT_PROFILE_ID],
    key="hub_snap_profile",
  ) if list_profiles() else None
  if sel:
    from kb_profiles import list_snapshots
    import pandas as pd
    snaps = [s for s in list_snapshots(sel) if s.get("cumulative")]
    if snaps:
      st.dataframe(pd.DataFrame(snaps)[["cumulative", "label", "win_rate_pct", "total_r"]],
                   use_container_width=True, hide_index=True)
    else:
      st.caption("Chưa có snapshot từng epoch — chạy học mới để tạo ep001, ep002, …")

  st.markdown("#### Giai đoạn học (theo Cài đặt)")
  presets = settings_era_presets()
  if not presets:
    st.info("Chưa có giai đoạn học — cấu hình tại **Cài đặt**.")
  for label, pid, lf, lt, of, ot in presets:
    exists = any(p["id"] == pid and p.get("exists") for p in list_profiles())
    icon = "✅" if exists else "○"
    c1, c2 = st.columns([3, 1])
    with c1:
      st.caption(f"{icon} **{label}** — học `{lf}→{lt}`, backtest OOS `{of}→{ot}`")
    with c2:
      if st.button("Dùng preset", key=f"preset_{pid}"):
        set_active_from_preset(label, pid, lf, lt, of, ot)
        st.session_state["hub_learn_name"] = label.split("→")[0].strip()
        st.session_state["hub_tab"] = 1
        st.rerun()

  st.divider()
  c1, c2 = st.columns(2)
  with c1:
    del_candidates = [p["id"] for p in list_profiles() if p["id"] != DEFAULT_PROFILE_ID]
    if del_candidates:
      del_id = st.selectbox("Xóa profile", del_candidates, key="hub_del")
      if st.button("Xóa profile", type="secondary", key="hub_del_btn"):
        delete_profile(del_id)
        st.warning(f"Đã xóa **{del_id}**")
        st.rerun()
  with c2:
    pick = st.selectbox(
      "Chọn profile → backtest",
      [p["id"] for p in _list_era_profiles()],
      key="hub_goto_bt",
    ) if _list_era_profiles() else None
    if pick and st.button("Chạy Backtest →", key="hub_goto_bt_btn"):
      of, ot = suggested_oos_range(pick)
      set_active_workspace(kb_profile=pick, oos_from=of, oos_to=ot)
      st.session_state["nav_page"] = "learning"
      st.session_state["learning_tab"] = "grid"
      st.rerun()


def _tab_merge():
  from gui.components import _profile_label
  from kb_profiles import DEFAULT_PROFILE_ID, merge_kb_profiles

  st.subheader("Ghép nhiều giai đoạn thành một profile")
  st.caption(
    "Gộp kinh nghiệm (rules, genomes, ML) từ **2+ giai đoạn** đã học "
    "thành profile mới — dùng khi muốn «tập» nhiều era."
  )

  candidates = _list_era_profiles()
  if len(candidates) < 2:
    st.info("Cần ít nhất 2 giai đoạn đã học — tạo/học ở tab **Huấn luyện** trước.")
    return

  label_to_id = {_profile_label(p): p["id"] for p in candidates}
  picked_labels = st.multiselect(
    "Chọn giai đoạn nguồn (2+)",
    list(label_to_id.keys()),
    key="hub_merge_sources",
  )
  source_ids = [label_to_id[l] for l in picked_labels]

  c1, c2 = st.columns(2)
  with c1:
    new_id = st.text_input(
      "ID profile mới",
      value="era_merged",
      key="hub_merge_id",
      help="VD: era_merged_2022_2025",
    )
  with c2:
    new_name = st.text_input(
      "Tên hiển thị",
      value="Giai đoạn ghép",
      key="hub_merge_name",
    )
  overwrite = st.checkbox("Ghi đè nếu ID đã tồn tại", key="hub_merge_overwrite")

  if picked_labels:
    st.caption("**Sẽ ghép:** " + " · ".join(picked_labels))

  if st.button("🔗 Ghép thành profile mới", type="primary", key="hub_merge_run"):
    try:
      entry = merge_kb_profiles(
        source_ids,
        new_id.strip(),
        new_name.strip(),
        overwrite=overwrite,
      )
      st.success(
        f"Đã tạo **{entry.get('name')}** (`{entry.get('id')}`) · "
        f"học {entry.get('trained_from') or '?'} → {entry.get('trained_to') or '?'}"
      )
      st.session_state["nav_page"] = "learning"
      st.session_state["learning_tab"] = "train_kb"
      st.rerun()
    except ValueError as e:
      st.error(str(e))


def _tab_learn():
  from gui.app_settings import default_learning_era, get_settings, resolve_learning_eras

  st.subheader("Huấn luyện bộ nhớ kinh nghiệm")
  s = get_settings()
  era = default_learning_era(s)
  loops = int(s.get("learning_loops") or 4)
  era_labels = ", ".join(e["label"] for e in resolve_learning_eras(s)) or "—"
  st.caption(
    f"Theo **Cài đặt**: giai đoạn **{era_labels}** · "
    f"**{loops}** vòng học · kiểm chứng **{s.get('backtest_from')} → {s.get('backtest_to')}**"
  )

  render_task_status(key_prefix="hub_learn")
  running = task_blocks_ui("hub_learn")

  st.markdown("**Chọn nhanh giai đoạn từ Cài đặt**")
  presets = settings_era_presets()
  pcols = st.columns(min(len(presets), 3) or 1)
  for i, (label, pid, lf, lt, _of, _ot) in enumerate(presets):
    with pcols[i % len(pcols)]:
      if st.button(label, key=f"hub_pick_{pid}", use_container_width=True):
        set_widget_preference("hub_learn_id", pid, "training.profile_id")
        set_widget_preference(
          "hub_learn_name", label.split("→")[0].strip(), "training.profile_name",
        )
        set_widget_preference("hub_learn_from", lf, "training.learn_from")
        set_widget_preference("hub_learn_until", lt, "training.learn_until")
        set_widget_preference("hub_epochs", loops, "training.epochs")
        st.rerun()

  field_defaults = {
    "hub_learn_id": (era["kb_profile"], "training.profile_id"),
    "hub_learn_name": (era["label"], "training.profile_name"),
    "hub_learn_from": (era["learn_from"], "training.learn_from"),
    "hub_learn_until": (era["learn_until"], "training.learn_until"),
    "hub_epochs": (loops, "training.epochs"),
    "hub_reset": (False, "training.reset"),
  }
  for widget_key, (default, pref_key) in field_defaults.items():
    restore_widget(widget_key, default, preference_key=pref_key)

  c1, c2 = st.columns(2)
  with c1:
    new_id = st.text_input(
      "Profile ID", key="hub_learn_id",
      on_change=preference_callback("hub_learn_id", "training.profile_id"),
    )
    new_name = st.text_input(
      "Tên hiển thị", key="hub_learn_name",
      on_change=preference_callback("hub_learn_name", "training.profile_name"),
    )
    learn_from = st.text_input(
      "Học từ", key="hub_learn_from",
      on_change=preference_callback("hub_learn_from", "training.learn_from"),
    )
  with c2:
    learn_until = st.text_input(
      "Học đến", key="hub_learn_until",
      on_change=preference_callback("hub_learn_until", "training.learn_until"),
    )
    epochs = st.number_input(
      "Số vòng học", 1, 12, key="hub_epochs",
      on_change=preference_callback("hub_epochs", "training.epochs"),
      help="Theo Cài đặt — chỉnh tại **Cài đặt**.",
    )
    reset = st.checkbox(
      "Reset profile trước khi học", key="hub_reset",
      on_change=preference_callback("hub_reset", "training.reset"),
    )

  existing = get_profile(new_id.strip())
  if existing and existing.get("exists"):
    st.info(f"Profile **{new_id}** đã tồn tại — học tiếp sẽ **cộng dồn** KB (trừ khi bật Reset).")

  if st.button(
    "▶ Học & lưu profile",
    type="primary",
    key="hub_learn_run",
    disabled=running,
  ):
    try:
      start_job(
        "learning",
        {
          "epochs": int(epochs),
          "reset_kb": reset,
          "kb_profile": new_id.strip(),
          "kb_name": new_name,
          "from_date": learn_from,
          "until_date": learn_until or None,
        },
        label=f"Học KB · {new_id.strip()}",
      )
      st.toast("Học KB đã bắt đầu chạy nền")
      st.rerun()
    except RuntimeError as e:
      st.error(str(e))

  with st.expander("Reset dữ liệu KB", expanded=False):
    st.caption(
      "Xóa file bộ nhớ + snapshot trên đĩa (kể cả orphan). Không xóa giai đoạn trong **Cài đặt**. "
      "Profile `default` không xóa được."
    )
    eras = resolve_learning_eras(s)
    era_ids = [e["kb_profile"] for e in eras if e.get("kb_profile")]
    all_profiles = [
      p["id"] for p in list_profiles()
      if p.get("id") and p["id"] != DEFAULT_PROFILE_ID and p.get("exists")
    ]
    disk_ids = [pid for pid in list_disk_profile_ids() if pid != DEFAULT_PROFILE_ID]
    options = sorted(set(era_ids) | set(all_profiles) | set(disk_ids))
    also_related = st.checkbox(
      "Cũng xóa backtest/report + file Trade Model orphan",
      key="hub_kb_reset_related",
    )
    if not options and not also_related:
      st.caption("Chưa có profile KB / snapshot để xóa.")
    else:
      pick_reset = st.multiselect(
        "Profile cần xóa",
        options,
        default=[pid for pid in era_ids if pid in options],
        key="hub_kb_reset_pick",
      ) if options else []
      confirm_kb = st.checkbox(
        "Xác nhận xóa vĩnh viễn dữ liệu đã chọn",
        key="hub_kb_reset_confirm",
      )
      if st.button(
        "Xóa dữ liệu KB đã chọn",
        type="secondary",
        icon=":material/delete_forever:",
        key="hub_kb_reset_btn",
        disabled=running or not confirm_kb or (not pick_reset and not also_related),
      ):
        deleted = []
        for pid in pick_reset:
          if delete_profile(pid):
            deleted.append(pid)
        orphans = purge_orphan_snapshots()
        notes = []
        if deleted:
          notes.append(f"KB: {', '.join(deleted)}")
        if orphans:
          notes.append(f"orphan snap: {', '.join(orphans)}")
        try:
          from gui.services import BACKTEST_REPORT, LEARNING_REPORT, load_learning_report
          from run_backtest import REPORT_DIR
          lr = load_learning_report() or {}
          if (not pick_reset or lr.get("kb_profile") in deleted) and LEARNING_REPORT.exists():
            LEARNING_REPORT.unlink()
            st.session_state.pop("learning_report", None)
          if also_related:
            from gui.report_store import clear_all_reports
            from gui.trade_model import purge_orphan_model_artifacts
            n_rpt = clear_all_reports()
            tm_files = purge_orphan_model_artifacts()
            for path in (BACKTEST_REPORT, REPORT_DIR / "oos_trades.csv"):
              if path.exists():
                path.unlink()
            st.session_state.pop("backtest_report", None)
            notes.append(f"reports={n_rpt}, tm_orphan={len(tm_files)}")
        except Exception:
          pass
        try:
          from gui.workspace import load_workspace_file, save_workspace_file
          ws = load_workspace_file() or {}
          if ws.get("kb_profile") in set(deleted) | set(orphans):
            ws["kb_profile"] = DEFAULT_PROFILE_ID
            ws["kb_snapshot"] = None
            ws["label"] = "Chưa chọn trade model"
            save_workspace_file(ws)
            st.session_state.pop("active_workspace", None)
        except Exception:
          pass
        if notes:
          st.success("Đã xóa — " + "; ".join(notes))
        else:
          st.warning("Không xóa được dữ liệu nào.")
        st.rerun()

  _render_kb_results()


def render_training_only():
  """Tab huấn luyện — gọi từ Learning hub."""
  from gui.app_settings import get_settings, resolve_learning_eras

  s = get_settings()
  loops = int(s.get("learning_loops") or 4)
  eras = ", ".join(e["label"] for e in resolve_learning_eras(s)) or "—"
  st.caption(
    f"Mặc định **{loops} vòng học** · giai đoạn **{eras}** theo Cài đặt — chỉnh tại **Cài đặt**."
  )

  _tab_learn()


def render():
  """Legacy full page — chuyển sang Learning hub."""
  import streamlit as st
  set_widget_preference("nav_page", "learning", "navigation.page")
  set_widget_preference("learning_tab", "train_kb", "navigation.learning_tab")
  st.rerun()
