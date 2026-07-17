"""5. Learning Center — epochs, KB profiles theo giai đoạn."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st
import pandas as pd

from kb_profiles import list_profiles, delete_profile, DEFAULT_PROFILE_ID
from gui.services import execute_learning, load_learning_report
from gui.components import ERA_PRESETS, kb_profile_picker, list_kb_profiles_df


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
    title="Tiến bộ qua Epoch",
    yaxis=dict(title="Win Rate %"),
    yaxis2=dict(title="Total R", overlaying="y", side="right"),
    height=360, margin=dict(l=40, r=40, t=50, b=40),
  )
  return fig


def render():
  st.header("Learning Center")
  st.caption("Học KB nhanh — quản lý đầy đủ profiles tại **KB & Giai đoạn**")

  st.info("💡 Tạo nhiều KB theo giai đoạn, backtest OOS từng profile → mở trang **KB & Giai đoạn**.")

  st.subheader("KB Profiles hiện có")
  pdf = list_kb_profiles_df()
  if pdf.empty:
    st.caption("Chưa có profile.")
  else:
    show_cols = [c for c in ["id", "name", "trained_from", "trained_to", "epochs", "exists"] if c in pdf.columns]
    st.dataframe(pdf[show_cols], use_container_width=True, hide_index=True)

  with st.expander("➕ Tạo / học KB profile mới", expanded=True):
    preset = st.selectbox(
      "Preset giai đoạn",
      ["Tùy chỉnh"] + [p[0] for p in ERA_PRESETS],
      key="lc_preset",
    )
    preset_map = {p[0]: p for p in ERA_PRESETS}
    if preset != "Tùy chỉnh":
      _, pid, lf, lt, _, _ = preset_map[preset]
      default_id, default_name, default_from, default_until = pid, preset.split("→")[0].strip(), lf, lt
    else:
      default_id, default_name, default_from, default_until = "era_2022_2023", "Era 2022-2023", "2022-01-01", "2023-12-31"

    c1, c2 = st.columns(2)
    with c1:
      new_id = st.text_input("Profile ID", default_id, key="lc_new_id")
      new_name = st.text_input("Tên hiển thị", default_name, key="lc_new_name")
      learn_from = st.text_input("Data từ", default_from, key="lc_from")
    with c2:
      learn_until = st.text_input("Data đến", default_until, key="lc_until")
      epochs = st.number_input("Số epoch", 1, 30, 3, key="lc_epochs")
      reset = st.checkbox("Reset profile trước khi học", key="lc_reset")

    if st.button("▶ Học & lưu profile", type="primary", key="lc_learn_new"):
      prog = st.progress(0)

      def on_ep(ep, total, _):
        prog.progress(ep / total, text=f"Epoch {ep}/{total}")

      with st.spinner("Learning..."):
        execute_learning(
          epochs=int(epochs), reset_kb=reset,
          kb_profile=new_id.strip(), kb_name=new_name,
          from_date=learn_from, until_date=learn_until or None,
          on_epoch_done=on_ep,
        )
      prog.empty()
      st.success(f"Đã lưu profile **{new_id}** ({learn_from} → {learn_until})")
      st.rerun()

  del_candidates = [p["id"] for p in list_profiles() if p["id"] != DEFAULT_PROFILE_ID]
  if del_candidates:
    c1, c2 = st.columns([2, 1])
    with c1:
      del_id = st.selectbox("Xóa profile", del_candidates, key="lc_del_id")
    with c2:
      st.write("")
      if st.button("Xóa", key="lc_del_btn"):
        delete_profile(del_id)
        st.warning(f"Đã xóa {del_id}")
        st.rerun()

  st.divider()
  st.subheader("Học thêm epoch (profile hiện có)")
  c1, c2, c3, c4 = st.columns(4)
  with c1:
    quick_profile = kb_profile_picker("lc_quick", show_meta=True)
  with c2:
    quick_epochs = st.number_input("Epochs", 1, 20, 2, key="lc_quick_ep")
  with c3:
    quick_reset = st.checkbox("Reset", key="lc_quick_reset")
  with c4:
    st.write("")
    st.caption("Cộng dồn KB")

  if st.button("▶ Start Learning", use_container_width=True):
    prog = st.progress(0)
    p = next((x for x in list_profiles() if x["id"] == quick_profile), None)

    def on_ep(ep, total, _):
      prog.progress(ep / total, text=f"Epoch {ep}/{total}")

    with st.spinner("Learning..."):
      learning = execute_learning(
        epochs=int(quick_epochs), reset_kb=quick_reset,
        kb_profile=quick_profile or DEFAULT_PROFILE_ID,
        kb_name=p["name"] if p else None,
        from_date=p.get("trained_from") or "2022-01-01",
        until_date=p.get("trained_to"),
        on_epoch_done=on_ep,
      )
    st.session_state["learning_report"] = learning
    prog.empty()
    st.success("Hoàn tất")
    st.rerun()

  learning = st.session_state.get("learning_report") or load_learning_report()
  if learning:
    st.subheader("Kết quả lần chạy gần nhất")
    st.caption(
      f"Profile: **{learning.get('kb_profile', '?')}** · "
      f"{learning.get('trained_from')} → {learning.get('trained_to')}"
    )
    history = learning.get("epoch_history", [])
    if history:
      st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
      fig = _epoch_chart(history)
      if fig:
        st.plotly_chart(fig, use_container_width=True)
