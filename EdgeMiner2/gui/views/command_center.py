"""Tổng quan — tiến độ quy trình + KPI + điều hướng nhanh."""
from __future__ import annotations

import streamlit as st

from analytics import direction_bias, trades_json_to_df, yearly_breakdown
from gui.components import constraint_checklist, kpi_row, status_banner, warn_long_bias, warn_no_costs
from gui.glossary import METRIC_LABELS, backtest_kpi_items
from gui.navigation import ALL_ITEMS
from gui.services import load_backtest_report, load_data_meta, load_kb, load_learning_report, refresh_market_data
from gui.ui_preferences import set_widget_preference
from gui.workflow_ui import render_workflow_panel
from gui.workspace import report_matches_workspace


def render():
  from gui.page_chrome import render_page_header
  render_page_header(ALL_ITEMS["home"], show_profile=False)

  data_meta = load_data_meta()
  if not data_meta.get("bars"):
    st.error("**Chưa có dữ liệu giá** — bấm **Refresh data** bên dưới trước khi học KB.")

  render_workflow_panel()

  st.divider()

  report = load_backtest_report()
  learning = load_learning_report()
  kb = load_kb()
  kb_summary = learning.get("kb_summary", {}) if learning else {
    "genomes": len(kb.genomes),
    "rules": len(kb.rule_stats),
    "ml_samples": len(kb.ml_experience),
  }

  status_banner(report, kb_summary, data_meta)
  warn_no_costs()

  if report and report_matches_workspace(report):
    o = report["overall_oos"]
    y = report["last_1_year"]
    items = backtest_kpi_items(o, y)
    items.append((METRIC_LABELS["trades_per_week"], f"{o['trades_per_week']}", f"{o['n_trades']} lệnh"))
    kpi_row(items)

    with st.expander("Mục tiêu & OOS theo năm", expanded=False):
      constraint_checklist(report.get("constraints_met", {}))
      trades_df = trades_json_to_df(report.get("trades", []))
      if not trades_df.empty:
        st.dataframe(yearly_breakdown(trades_df), use_container_width=True, hide_index=True)
        bias = direction_bias(trades_df)
        if not bias.empty and "LONG" in bias["dir"].values:
          pct = bias.loc[bias["dir"] == "LONG", "pct"].iloc[0]
          warn_long_bias(pct)
  elif report:
    st.caption("_Có backtest cũ nhưng không khớp Trade Model đang chọn._")

  from gui.ui_theme import icon_btn

  st.subheader("Đi tới")
  c1, c2, c3 = st.columns(3)
  with c1:
    if icon_btn("Học & tối ưu", key="cc_nav_learning", icon=":material/school:"):
      set_widget_preference("nav_page", "learning", "navigation.page")
      from gui.views.learning_hub import _default_learning_tab
      set_widget_preference(
        "learning_tab", _default_learning_tab(), "navigation.learning_tab",
      )
      st.rerun()
  with c2:
    if icon_btn("Paper", key="cc_nav_paper", icon=":material/monitoring:"):
      set_widget_preference("nav_page", "paper", "navigation.page")
      st.rerun()
  with c3:
    if icon_btn("Refresh data", key="cc_refresh", icon=":material/sync:"):
      with st.spinner("Tải Dukascopy..."):
        refresh_market_data()
      st.success("Đã cập nhật data cache")
      st.rerun()
