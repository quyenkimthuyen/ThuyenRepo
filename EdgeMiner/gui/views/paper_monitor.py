"""7. Paper / Live Monitor — tín hiệu tuần hiện tại."""
from __future__ import annotations

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from gui.services import get_paper_monitor


def render():
  st.header("Paper / Live Monitor")
  st.caption("Tín hiệu tuần hiện tại — paper trade trước khi live")

  use_kb = st.toggle("Dùng KB", value=False, key="pm_kb")
  spread = st.slider("Spread (pips)", 0.0, 3.0, DEFAULT_SPREAD_PIPS, 0.1, key="pm_spread")
  slip = st.slider("Slippage (pips)", 0.0, 2.0, DEFAULT_SLIPPAGE_PIPS, 0.1, key="pm_slip")

  if st.button("Refresh monitor", type="primary"):
    st.session_state.pop("monitor_state", None)

  with st.spinner("Cập nhật..."):
    state = st.session_state.get("monitor_state") or get_paper_monitor(
      use_learning=use_kb, spread_pips=spread, slippage_pips=slip,
    )
    st.session_state["monitor_state"] = state

  if state.get("error"):
    st.error(state["error"])
    return

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Tuần", state["week_start"])
  c2.metric("Lệnh tuần", f"{state['week_trades_taken']}/{state['strategy']['max_trades_per_week']}")
  c3.metric("Slots còn", state["slots_remaining"])
  c4.metric("Session", "ACTIVE" if state["in_session"] else "OFF")

  st.caption(f"Bar cuối: {state['last_bar']} | WR tuần: {state['week_wr']}% | R: {state['week_total_r']}")

  st.subheader("Strategy đang dùng")
  st.json(state["strategy"])

  col_a, col_b = st.columns(2)
  with col_a:
    st.subheader("Tín hiệu tuần này")
    if state["signals_this_week"]:
      st.dataframe(state["signals_this_week"], hide_index=True, use_container_width=True)
    else:
      st.caption("Chưa có tín hiệu.")
  with col_b:
    st.subheader("Lệnh đã khớp (backtest tuần)")
    if state["recent_trades"]:
      st.dataframe(state["recent_trades"], hide_index=True, use_container_width=True)
    else:
      st.caption("Chưa có lệnh tuần này.")

  st.warning(
    "⚠️ Đây là **paper monitor** trên data lịch sử/bar gần nhất — "
    "chưa kết nối broker. So sánh fill thật trước khi live."
  )
