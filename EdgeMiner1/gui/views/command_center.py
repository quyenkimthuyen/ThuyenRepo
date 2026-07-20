"""1. Command Center — dashboard tổng quan cho trader."""
from __future__ import annotations

import streamlit as st

from analytics import direction_bias, trades_json_to_df, yearly_breakdown
from gui.glossary import METRIC_LABELS, backtest_kpi_items
from gui.components import constraint_checklist, kpi_row, status_banner, warn_long_bias, warn_no_costs
from gui.live_workflow import assess_workflow
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header, render_workflow_cards
from gui.services import load_backtest_report, load_data_meta, load_kb, load_learning_report, refresh_market_data
from gui.trade_profile import format_trade_profile_label, format_trade_profile_oneline, get_active_trade_profile
from gui.workflow_ui import render_workflow_panel
from gui.workspace import report_matches_workspace


def render():
  render_page_header(ALL_ITEMS["home"], show_profile=False)

  tp = get_active_trade_profile()
  st.info(f"📋 **{format_trade_profile_label(tp)}** — {format_trade_profile_oneline(tp)}")

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
    st.warning("Có backtest cũ nhưng **không khớp trade profile** — chạy lại trong Nghiên cứu.")
  else:
    wf = assess_workflow()
    if wf["current_step"] == 1:
      st.info("Bắt đầu **Bước 1** ở trên — baseline KB OFF trước khi tin vào bộ nhớ.")
    else:
      st.info("Chưa có backtest cho profile này. Mở **Nghiên cứu → Kiểm chứng**.")

  st.subheader("Đi tới")
  render_workflow_cards()

  st.divider()
  c1, c2, c3 = st.columns(3)
  with c1:
    if st.button("🔬 Mở Nghiên cứu", use_container_width=True, key="cc_go_research"):
      st.session_state["nav_page"] = "research"
      st.session_state["research_tab"] = "backtest"
      st.rerun()
  with c2:
    if st.button("🧠 KB & Học", use_container_width=True, key="cc_go_kb"):
      st.session_state["nav_page"] = "kb"
      st.rerun()
  with c3:
    if st.button("🔄 Refresh data", use_container_width=True, key="cc_refresh"):
      with st.spinner("Tải Dukascopy..."):
        refresh_market_data()
      st.success("Đã cập nhật data cache")
      st.rerun()
