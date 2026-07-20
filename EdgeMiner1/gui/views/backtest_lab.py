"""2. Backtest Lab — chạy walk-forward theo Trade Profile."""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analytics import (
  equity_series, rolling_win_rate, trades_json_to_df,
  weekly_r_histogram, yearly_breakdown,
)
from gui.components import constraint_checklist, kpi_row, warn_kb_leak, warn_no_costs
from gui.glossary import HELP, METRIC_LABELS, backtest_kpi_items
from gui.long_task_background import start_job
from gui.long_task_ui import render_task_status, task_blocks_ui
from gui.services import load_backtest_report
from gui.trade_profile import get_profile_run_params, render_profile_card
from gui.workspace import report_matches_workspace


def _equity_chart(eq_df):
  if eq_df.empty:
    return None
  fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
                      subplot_titles=("Lợi nhuận tích lũy (R)", "Sụt giảm (R)"))
  fig.add_trace(go.Scatter(x=eq_df["entry"], y=eq_df["equity_r"], name="Equity",
                           line=dict(color="#2ecc71", width=2)), row=1, col=1)
  fig.add_trace(go.Scatter(x=eq_df["entry"], y=eq_df["drawdown_r"], name="Sụt giảm",
                           fill="tozeroy", line=dict(color="#e74c3c")), row=2, col=1)
  fig.update_layout(height=480, margin=dict(l=40, r=20, t=40, b=40), showlegend=False)
  return fig


def _rolling_wr_chart(rw_df):
  if rw_df.empty:
    return None
  fig = go.Figure()
  fig.add_trace(go.Scatter(x=rw_df["entry"], y=rw_df["rolling_wr"], line=dict(color="#3498db")))
  fig.add_hline(y=60, line_dash="dash", line_color="gray", annotation_text="60%")
  fig.update_layout(title="Tỷ lệ thắng 20 lệnh gần nhất", height=280, margin=dict(l=40, r=20, t=40, b=40))
  return fig


def _weekly_hist(df):
  if df.empty:
    return None
  colors = ["#2ecc71" if r >= 0 else "#e74c3c" for r in df["oos_r"]]
  fig = go.Figure(go.Bar(x=df["week"], y=df["oos_r"], marker_color=colors))
  fig.update_layout(title="Lợi nhuận theo tuần (R)", height=280, margin=dict(l=40, r=20, t=40, b=40))
  fig.update_xaxes(tickangle=45)
  return fig


def render(embedded: bool = False):
  embedded = embedded or bool(st.session_state.get("_research_hub"))
  if not embedded:
    st.header("Kiểm chứng backtest")

  render_profile_card(show_hint=not embedded)
  from gui.workflow_ui import render_baseline_hint
  render_baseline_hint()
  params = get_profile_run_params()
  job_status = render_task_status(key_prefix="bt_lab")
  running = task_blocks_ui("bt_lab")
  report = st.session_state.get("backtest_report") or load_backtest_report()
  warn_no_costs()

  col_run, col_adv = st.columns([1, 2])
  with col_run:
    if st.button(
      "▶ Chạy Backtest",
      type="primary",
      use_container_width=True,
      key="lab_run_main",
      disabled=running,
    ):
      if params["use_kb"]:
        warn_kb_leak(True)
      compare_off = bool(st.session_state.get("lab_compare_kb_off"))
      archive = bool(st.session_state.get("lab_archive", False))
      try:
        start_job(
          "backtest",
          {
            "use_learning": params["use_learning"],
            "train_months": params["train_months"],
            "start_date": st.session_state.get("lab_start", "2022-01-01"),
            "spread_pips": params["spread_pips"],
            "slippage_pips": params["slippage_pips"],
            "holdout_months": int(st.session_state.get("lab_holdout", 0)),
            "kb_profile": params["kb_profile"],
            "kb_snapshot": params["kb_snapshot"],
            "oos_from": params["oos_from"],
            "oos_to": params["oos_to"],
            "compare_kb_off": compare_off,
            "archive": archive,
          },
          label=f"Backtest · Train {params['train_months']}m",
        )
        st.toast("Backtest đã bắt đầu chạy nền")
        st.rerun()
      except RuntimeError as e:
        st.error(str(e))

  with col_adv:
    with st.expander("Tùy chọn nâng cao", expanded=False):
      st.text_input("Dữ liệu giá từ", "2022-01-01", key="lab_start")
      st.selectbox(
        "Giữ lại để test cuối (tháng)", [0, 6, 12], index=0, key="lab_holdout",
        help=HELP["holdout"],
      )
      st.checkbox("Lưu vào kho so sánh báo cáo", value=False, key="lab_archive",
                  help="Bật khi hoàn thành bước quy trình — để so sánh KB ON/OFF sau.")
      st.checkbox(
        "Chạy thêm không dùng bộ nhớ để so sánh", value=False, key="lab_compare_kb_off",
        help=HELP["kb_off"],
      )

  if not report:
    if job_status.get("running"):
      st.caption("Kết quả sẽ hiện khi backtest hoàn thành.")
    else:
      st.info("Nhấn **Chạy Backtest** — tham số lấy từ **Cấu hình giao dịch** (sidebar).")
    return

  if not report_matches_workspace(report):
    st.warning("Báo cáo **không khớp profile** hiện tại — chạy lại backtest.")

  compare = st.session_state.get("lab_kb_compare")
  if compare and "kb_off" in compare:
    import pandas as pd
    st.markdown("#### So sánh: có bộ nhớ vs không bộ nhớ")
    on, off = compare["kb_on"]["overall_oos"], compare["kb_off"]["overall_oos"]
    st.dataframe(pd.DataFrame([
      {"Chế độ": "Có bộ nhớ", METRIC_LABELS["win_rate_pct"]: on["win_rate_pct"],
       METRIC_LABELS["total_r"]: on["total_r"], METRIC_LABELS["max_drawdown_r"]: on.get("max_drawdown_r")},
      {"Chế độ": "Không bộ nhớ", METRIC_LABELS["win_rate_pct"]: off["win_rate_pct"],
       METRIC_LABELS["total_r"]: off["total_r"], METRIC_LABELS["max_drawdown_r"]: off.get("max_drawdown_r")},
    ]), use_container_width=True, hide_index=True)
    st.metric("Chênh lệch tổng R (có − không)", f"{on['total_r'] - off['total_r']:+.2f}R")

  cfg = report.get("config", {})
  kv = cfg.get("kb_validation", {})
  if kv.get("message"):
    st.caption(f"Kiểm tra bộ nhớ: {kv['message']}")

  if "holdout_forward" in report:
    h = report["holdout_forward"]["metrics"]
    st.success(
      f"Test cuối (từ {report['holdout_forward']['cutoff']}): "
      f"{h['n_trades']} lệnh | thắng {h['win_rate_pct']}% | {h['total_r']}R"
    )

  o, y = report["overall_oos"], report["last_1_year"]
  kpi_row(backtest_kpi_items(o, y))

  st.subheader("Mục tiêu (1 năm gần nhất)")
  constraint_checklist(report.get("constraints_met", {}))

  trades_df = trades_json_to_df(report.get("trades", []))
  eq_df = equity_series(trades_df)
  rw_df = rolling_win_rate(trades_df)

  c1, c2 = st.columns([2, 1])
  with c1:
    fig = _equity_chart(eq_df)
    if fig:
      st.plotly_chart(fig, use_container_width=True)
  with c2:
    st.subheader("Theo năm")
    st.dataframe(yearly_breakdown(trades_df), use_container_width=True, hide_index=True)

  c3, c4 = st.columns(2)
  with c3:
    fig2 = _rolling_wr_chart(rw_df)
    if fig2:
      st.plotly_chart(fig2, use_container_width=True)
  with c4:
    wh = weekly_r_histogram(report.get("weekly_log", []))
    fig3 = _weekly_hist(wh.tail(52) if len(wh) > 52 else wh)
    if fig3:
      st.plotly_chart(fig3, use_container_width=True)

  st.subheader("Nhật ký từng tuần (walk-forward)")
  wlog = [w for w in report.get("weekly_log", []) if "oos_trades" in w]
  if wlog:
    import pandas as pd
    wdf = pd.DataFrame(wlog)
    filt = st.selectbox("Lọc tuần", ["Tất cả", "Có lệnh", "Tuần lỗ (R<0)"], key="wlog_filt")
    if filt == "Có lệnh":
      wdf = wdf[wdf["oos_trades"] > 0]
    elif filt == "Tuần lỗ (R<0)":
      wdf = wdf[wdf["oos_r"] < 0]
    st.dataframe(wdf, use_container_width=True, hide_index=True, height=360)
  else:
    st.caption("Không có weekly log.")
