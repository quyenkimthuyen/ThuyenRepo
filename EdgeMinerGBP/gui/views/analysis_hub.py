"""Phân tích — dashboard báo cáo trực quan."""
from __future__ import annotations

import streamlit as st

from gui.analysis_support import get_matching_analysis_report, render_report_required_panel
from gui.analysis_viz import (
  inject_analysis_css,
  render_ab_decision_cards,
  render_config_pills,
  render_overview,
)
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.trade_model import format_model_label, render_model_picker
from gui.views import risk_dashboard, trade_journal, strategy_inspector


def _render_subview(module):
  import inspect
  sig = inspect.signature(module.render)
  if "embedded" in sig.parameters:
    module.render(embedded=True)
  else:
    module.render()


def render():
  inject_analysis_css()
  render_page_header(ALL_ITEMS["analysis"], show_profile=False)

  model = render_model_picker(key="analysis_tm_pick", label="Trade Model")
  if not model:
    return

  report = get_matching_analysis_report()
  if render_report_required_panel(key_prefix="an_rep"):
    return

  assert report is not None

  st.markdown(
    f'<div class="ff-hero"><span style="opacity:0.8">Báo cáo ·</span> '
    f'<b>{format_model_label(model)}</b></div>',
    unsafe_allow_html=True,
  )

  c_cfg, c_ab = st.columns([2.2, 1])
  with c_cfg:
    render_config_pills(report)
  with c_ab:
    render_ab_decision_cards()

  tab_over, tab_risk, tab_journal, tab_strat = st.tabs([
    "📊 Tổng quan",
    "🛡 Rủi ro",
    "📒 Nhật ký",
    "🧬 Chiến lược",
  ])

  with tab_over:
    render_overview(report)

  with tab_risk:
    st.session_state["_analysis_hub"] = True
    try:
      _render_subview(risk_dashboard)
    finally:
      st.session_state.pop("_analysis_hub", None)

  with tab_journal:
    st.session_state["_analysis_hub"] = True
    try:
      _render_subview(trade_journal)
    finally:
      st.session_state.pop("_analysis_hub", None)

  with tab_strat:
    st.session_state["_analysis_hub"] = True
    try:
      _render_subview(strategy_inspector)
    finally:
      st.session_state.pop("_analysis_hub", None)
