"""Phân tích — chọn Trade Model, xem Risk / Nhật ký / Chiến lược."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.trade_model import render_model_picker
from gui.ui_theme import icon_btn
from gui.views import risk_dashboard, trade_journal, strategy_inspector


TAB_KEYS = ["risk", "journal", "strategy"]
TAB_LABELS = {
  "risk": "Rủi ro",
  "journal": "Nhật ký",
  "strategy": "Chiến lược",
}
TAB_ICONS = {
  "risk": ":material/shield:",
  "journal": ":material/receipt_long:",
  "strategy": ":material/candlestick_chart:",
}


def _render_subview(module):
  import inspect
  sig = inspect.signature(module.render)
  if "embedded" in sig.parameters:
    module.render(embedded=True)
  else:
    module.render()


def render():
  render_page_header(ALL_ITEMS["analysis"], show_profile=False)

  model = render_model_picker(key="analysis_tm_pick", label="Trade Model")
  if not model:
    return

  pick = st.session_state.get("analysis_tab", "risk")
  if pick not in TAB_KEYS:
    pick = "risk"
  st.session_state["analysis_tab"] = pick

  cols = st.columns(3)
  for col, tab_key in zip(cols, TAB_KEYS):
    with col:
      if icon_btn(
        TAB_LABELS[tab_key],
        key=f"analysis_tab_{tab_key}",
        icon=TAB_ICONS[tab_key],
        active=(pick == tab_key),
      ):
        st.session_state["analysis_tab"] = tab_key
        st.rerun()

  selected = st.session_state.get("analysis_tab", pick)

  st.divider()
  st.session_state["_analysis_hub"] = True
  try:
    if selected == "risk":
      _render_subview(risk_dashboard)
    elif selected == "journal":
      _render_subview(trade_journal)
    else:
      _render_subview(strategy_inspector)
  finally:
    st.session_state.pop("_analysis_hub", None)
