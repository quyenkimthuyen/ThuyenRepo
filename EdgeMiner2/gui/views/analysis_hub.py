"""Phân tích — chọn Trade Model, xem Risk / Nhật ký / Chiến lược."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.trade_model import render_model_picker
from gui.views import risk_dashboard, trade_journal, strategy_inspector


TAB_KEYS = ["risk", "journal", "strategy"]
TAB_LABELS = {
  "risk": "🛡 Quản trị rủi ro",
  "journal": "📒 Nhật ký lệnh",
  "strategy": "🧬 Chiến lược",
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

  st.markdown("Chọn **Trade Model** — mọi phân tích dựa trên backtest của model đó.")
  model = render_model_picker(key="analysis_tm_pick")
  if not model:
    return

  default_tab = st.session_state.get("analysis_tab", "risk")
  if default_tab not in TAB_KEYS:
    default_tab = "risk"
  tab_idx = TAB_KEYS.index(default_tab)

  selected_label = st.radio(
    "Tab",
    [TAB_LABELS[k] for k in TAB_KEYS],
    horizontal=True,
    index=tab_idx,
    key="analysis_tab_radio",
  )
  selected = TAB_KEYS[[TAB_LABELS[k] for k in TAB_KEYS].index(selected_label)]
  st.session_state["analysis_tab"] = selected

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
