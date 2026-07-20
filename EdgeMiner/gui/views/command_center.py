"""1. Command Center — dashboard tổng quan cho trader."""
from __future__ import annotations

import streamlit as st

from analytics import direction_bias, trades_json_to_df, yearly_breakdown
from gui.app_settings import format_settings_summary, get_settings
from gui.glossary import METRIC_LABELS, backtest_kpi_items
from gui.components import constraint_checklist, kpi_row, status_banner, warn_long_bias, warn_no_costs
from gui.live_workflow import assess_workflow
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header, render_workflow_cards
from gui.services import load_backtest_report, load_data_meta, load_kb, load_learning_report, refresh_market_data
from gui.trade_model import format_model_oneline, get_active_trade_model
from gui.workflow_ui import render_workflow_panel
from gui.workspace import report_matches_workspace


def render():
  render_page_header(ALL_ITEMS["home"], show_profile=False)

  m = get_active_trade_model()
  if m:
    st.info(f"📦 **Trade model:** {format_model_oneline(m)}")
  else:
    st.warning("Chưa chọn trade model — chạy **Học → Grid Search** và tạo model.")

  st.caption(format_settings_summary(get_settings()))

  render_workflow_panel()

  st.divider()

  report = load_backtest_report()
  learning = load_learning_report()
  kb = load_kb()
  data_meta = load_data_meta()

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
    st.warning("Có backtest cũ nhưng **không khớp trade model** — tạo model mới từ Grid Search.")
  else:
    wf = assess_workflow()
    if wf["current_step"] == 1:
      st.info("Bắt đầu **Bước 1** — huấn luyện bộ nhớ & Grid Search.")
    else:
      st.info("Chưa có backtest. Mở **Học & tối ưu → Grid Search**.")

  st.subheader("Đi tới")
  render_workflow_cards()

  st.divider()
  c1, c2, c3 = st.columns(3)
  with c1:
    if st.button("🔎 Học & tối ưu", use_container_width=True, key="cc_go_learning"):
      st.session_state["nav_page"] = "learning"
      st.session_state["learning_tab"] = "grid"
      st.rerun()
  with c2:
    if st.button("⚙️ Cài đặt", use_container_width=True, key="cc_go_settings"):
      st.session_state["nav_page"] = "settings"
      st.rerun()
  with c3:
    if st.button("🔄 Refresh data", use_container_width=True, key="cc_refresh"):
      with st.spinner("Tải Dukascopy..."):
        refresh_market_data()
      st.success("Đã cập nhật data cache")
      st.rerun()
