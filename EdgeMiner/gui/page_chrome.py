"""Shared page chrome — header gọn + Trade Model."""
from __future__ import annotations

import streamlit as st

from gui.navigation import NavItem
from gui.trade_model import format_model_oneline, get_active_trade_model
from gui.workspace import report_matches_workspace


def render_page_header(
  item: NavItem,
  *,
  show_profile: bool = True,
  show_workspace: bool | None = None,
  compact_workspace: bool = True,
):
  """Tiêu đề trang + trade model một dòng."""
  if show_workspace is not None:
    show_profile = show_workspace
  st.header(item.label)
  if item.hint:
    st.caption(item.hint)
  if show_profile:
    render_profile_strip(compact=compact_workspace)


def render_profile_strip(*, compact: bool = True):
  from gui.services import load_backtest_report

  m = get_active_trade_model()
  if not m:
    st.caption("📦 _Chưa chọn trade model_")
    return
  line = format_model_oneline(m)
  report = load_backtest_report()
  if report:
    o = report.get("overall_oos") or {}
    match = report_matches_workspace(report)
    if match:
      line += f" · Backtest **{o.get('total_r', '—')}R** (✓)"
    else:
      line += " · _Chưa có backtest cho model này_"
  if compact:
    st.caption(f"📦 {line}")
  else:
    st.info(f"📦 {line}")


# Alias tương thích
render_workspace_strip = render_profile_strip


def render_workflow_cards():
  """Thẻ điều hướng nhanh trên Tổng quan."""
  from gui.services import load_backtest_report
  from gui.trade_model import get_active_trade_model

  m = get_active_trade_model()
  report = load_backtest_report()
  has_report = bool(report and report_matches_workspace(report))

  cards = [
    ("📡", "Giám sát paper", "paper", "Tín hiệu tuần này"),
    ("🔎", "Học & tối ưu", "learning", "Grid Search · Trade Models"),
    ("⚙️", "Cài đặt", "settings", "Train · giai đoạn · kiểm chứng"),
    ("📊", "Phân tích", "analysis", "Risk" if has_report else "Chọn trade model"),
  ]
  cols = st.columns(len(cards))
  for col, (icon, title, page_key, sub) in zip(cols, cards):
    with col:
      st.markdown(f"##### {icon} {title}")
      st.caption(sub)
      if st.button("Mở", key=f"wf_{page_key}", use_container_width=True):
        st.session_state["nav_page"] = page_key
        if page_key == "learning" and not has_report:
          st.session_state["learning_tab"] = "grid"
        st.rerun()
