"""1. Command Center — dashboard tổng quan cho trader."""
from __future__ import annotations

import streamlit as st

from analytics import direction_bias, trades_json_to_df, yearly_breakdown
from gui.app_settings import format_settings_summary, get_settings
from gui.glossary import METRIC_LABELS, backtest_kpi_items
from gui.components import constraint_checklist, kpi_row, status_banner, warn_long_bias, warn_no_costs
from gui.live_workflow import WORKFLOW_STEPS, assess_workflow
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_workflow_cards
from gui.services import load_backtest_report, load_data_meta, load_kb, load_learning_report, refresh_market_data
from gui.trade_model import format_model_oneline, get_active_trade_model
from gui.workflow_ui import render_workflow_panel
from gui.workspace import report_matches_workspace


def _render_next_action():
  from gui.grid_search_engine import grid_readiness, load_latest_grid_run

  wf = assess_workflow()
  cur = wf["current_step"]
  spec = WORKFLOW_STEPS[cur - 1]
  r = grid_readiness()

  if cur == 1:
    st.warning(
      f"**Bước tiếp theo — {spec['title']}**  \n"
      f"Học 3 giai đoạn KB (mỗi giai đoạn **{get_settings().get('learning_loops', 4)}** vòng). "
      f"Hiện **{r['ready_combos']}/{r['expected_combos']}** combo sẵn sàng cho Grid Search."
    )
    if r["missing_profiles"]:
      for m in r["missing_profiles"]:
        st.markdown(f"- Chưa học: **{m['label']}** (`{m['id']}`)")
    if r["under_trained"]:
      for u in r["under_trained"]:
        st.markdown(f"- Chưa đủ vòng: **{u['label']}** ({u['epochs_have']}/{u['epochs_needed']})")
    c1, c2 = st.columns(2)
    with c1:
      if st.button("→ Huấn luyện bộ nhớ", key="cc_go_train_kb", use_container_width=True):
        st.session_state["nav_page"] = "learning"
        st.session_state["learning_tab"] = "train_kb"
        st.rerun()
    with c2:
      if st.button("→ Cài đặt", key="cc_go_settings", use_container_width=True):
        st.session_state["nav_page"] = "settings"
        st.rerun()
  elif cur == 2:
    st.warning(
      f"**Bước tiếp theo — {spec['title']}**  \n"
      "Bộ nhớ đã sẵn sàng — chạy Grid Search (**36 combo** theo Cài đặt)."
    )
  elif cur == 3:
    n = wf.get("grid_rows", 0)
    st.warning(
      f"**Bước tiếp theo — {spec['title']}**  \n"
      f"Đã có **{n}** kết quả grid — chọn combo tốt → **Tạo Trade Model**."
    )
  elif cur == 4:
    st.warning(
      f"**Bước tiếp theo — {spec['title']}**  \n"
      "Chọn Trade Model → mở **Giám sát paper** ≥3 tuần."
    )
  else:
    st.info("Đã hoàn thành các bước chính — xem lại paper trước khi live.")


def render():
  item = ALL_ITEMS["home"]
  st.header(item.label)
  st.caption(item.hint)
  st.caption("Data → ① Huấn luyện KB → ② Grid Search → ③ Trade Model → Paper → Live")

  m = get_active_trade_model()
  if m:
    st.success(f"📦 **Trade model đang dùng:** {format_model_oneline(m)}")
  else:
    st.info("Chưa chọn trade model — hoàn thành quy trình bên dưới (Học KB → Grid → Model).")
    _render_next_action()

  st.caption(format_settings_summary(get_settings()))

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
    st.warning("Có backtest cũ nhưng **không khớp trade model** — tạo model mới từ Grid Search.")

  st.subheader("Đi tới nhanh")
  render_workflow_cards()

  c1, c2, c3, c4 = st.columns(4)
  with c1:
    if st.button("① Cài đặt", use_container_width=True, key="cc_go_settings"):
      st.session_state["nav_page"] = "settings"
      st.rerun()
  with c2:
    if st.button("② Học KB", use_container_width=True, key="cc_go_train"):
      st.session_state["nav_page"] = "learning"
      st.session_state["learning_tab"] = "train_kb"
      st.rerun()
  with c3:
    if st.button("② Grid Search", use_container_width=True, key="cc_go_grid"):
      st.session_state["nav_page"] = "learning"
      st.session_state["learning_tab"] = "grid"
      st.rerun()
  with c4:
    if st.button("🔄 Refresh data", use_container_width=True, key="cc_refresh"):
      with st.spinner("Tải Dukascopy..."):
        refresh_market_data()
      st.success("Đã cập nhật data cache")
      st.rerun()
