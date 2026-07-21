"""KB & Học — tạo KB profile, học epoch."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from kb_profiles import DEFAULT_PROFILE_ID, delete_profile, get_profile, list_profiles
from gui.components import (
  settings_era_presets, list_kb_profiles_df, suggested_oos_range,
)
from gui.services import load_learning_report
from gui.long_task_background import start_job
from gui.long_task_ui import render_task_status, task_blocks_ui
from gui.trade_profile import format_trade_profile_label, get_active_trade_profile
from gui.workspace import set_active_from_preset, set_active_workspace


def _list_era_profiles():
  from kb_profiles import list_era_profiles
  return list_era_profiles()


def _epoch_chart(history: list[dict]):
  if not history:
    return None
  epochs = [h["epoch"] for h in history]
  fig = go.Figure()
  fig.add_trace(go.Scatter(x=epochs, y=[h["win_rate_pct"] for h in history],
                           name="WR%", line=dict(color="#3498db")))
  fig.add_trace(go.Scatter(x=epochs, y=[h["total_r"] for h in history],
                           name="Total R", yaxis="y2", line=dict(color="#2ecc71")))
  fig.update_layout(
    title="Tiến bộ qua từng vòng học",
    yaxis=dict(title="Tỷ lệ thắng %"),
    yaxis2=dict(title="Tổng R", overlaying="y", side="right"),
    height=320, margin=dict(l=40, r=40, t=50, b=40),
  )
  return fig


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
      st.session_state["learning_tab"] = "era"
      st.rerun()
    except ValueError as e:
      st.error(str(e))


def _tab_learn():
  from gui.app_settings import default_learning_era, get_settings

  st.subheader("Huấn luyện bộ nhớ kinh nghiệm")
  s = get_settings()
  era = default_learning_era(s)
  loops = int(s.get("learning_loops") or 4)
  st.caption(
    f"Theo **Cài đặt**: giai đoạn **{', '.join(s.get('learning_era_keys') or [])}** · "
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
        st.session_state["hub_learn_id"] = pid
        st.session_state["hub_learn_name"] = label.split("→")[0].strip()
        st.session_state["hub_learn_from"] = lf
        st.session_state["hub_learn_until"] = lt
        st.session_state["hub_epochs"] = loops
        st.rerun()

  c1, c2 = st.columns(2)
  with c1:
    new_id = st.text_input("Profile ID", st.session_state.get("hub_learn_id", era["kb_profile"]), key="hub_learn_id")
    new_name = st.text_input("Tên hiển thị", st.session_state.get("hub_learn_name", era["label"]), key="hub_learn_name")
    learn_from = st.text_input("Học từ", st.session_state.get("hub_learn_from", era["learn_from"]), key="hub_learn_from")
  with c2:
    learn_until = st.text_input("Học đến", st.session_state.get("hub_learn_until", era["learn_until"]), key="hub_learn_until")
    epochs = st.number_input("Số vòng học", 1, 12, loops, key="hub_epochs", help="Theo Cài đặt — chỉnh tại **Cài đặt**.")
    reset = st.checkbox("Reset profile trước khi học", key="hub_reset")

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

  learning = st.session_state.get("learning_report") or load_learning_report()
  if learning:
    st.markdown("#### Kết quả học gần nhất")
    st.caption(
      f"Profile **{learning.get('kb_profile')}** · "
      f"{learning.get('trained_from')} → {learning.get('trained_to')}"
    )
    history = learning.get("epoch_history", [])
    if history:
      import pandas as pd
      st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
      fig = _epoch_chart(history)
      if fig:
        st.plotly_chart(fig, use_container_width=True)


def render_training_only():
  """Tab huấn luyện — gọi từ Learning hub."""
  from gui.kb_learning_ui import render_kb_training_page
  render_kb_training_page()


def render():
  """Legacy full page — chuyển sang Learning hub."""
  import streamlit as st
  st.session_state["nav_page"] = "learning"
  st.session_state["learning_tab"] = "train_kb"
  st.rerun()
