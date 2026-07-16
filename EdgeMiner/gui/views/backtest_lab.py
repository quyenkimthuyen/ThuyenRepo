"""2. Backtest Lab — cấu hình, biểu đồ, walk-forward log."""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analytics import (
  equity_series, rolling_win_rate, trades_json_to_df,
  weekly_r_histogram, yearly_breakdown,
)
from gui.components import constraint_checklist, kpi_row, warn_kb_leak, warn_no_costs
from gui.services import execute_backtest, load_backtest_report


def _equity_chart(eq_df):
  if eq_df.empty:
    return None
  fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
                      subplot_titles=("Equity (R)", "Drawdown (R)"))
  fig.add_trace(go.Scatter(x=eq_df["entry"], y=eq_df["equity_r"], name="Equity",
                           line=dict(color="#2ecc71", width=2)), row=1, col=1)
  fig.add_trace(go.Scatter(x=eq_df["entry"], y=eq_df["drawdown_r"], name="DD",
                           fill="tozeroy", line=dict(color="#e74c3c")), row=2, col=1)
  fig.update_layout(height=480, margin=dict(l=40, r=20, t=40, b=40), showlegend=False)
  return fig


def _rolling_wr_chart(rw_df):
  if rw_df.empty:
    return None
  fig = go.Figure()
  fig.add_trace(go.Scatter(x=rw_df["entry"], y=rw_df["rolling_wr"], line=dict(color="#3498db")))
  fig.add_hline(y=60, line_dash="dash", line_color="gray", annotation_text="60%")
  fig.update_layout(title="Rolling 20-trade Win Rate", height=280, margin=dict(l=40, r=20, t=40, b=40))
  return fig


def _weekly_hist(df):
  if df.empty:
    return None
  colors = ["#2ecc71" if r >= 0 else "#e74c3c" for r in df["oos_r"]]
  fig = go.Figure(go.Bar(x=df["week"], y=df["oos_r"], marker_color=colors))
  fig.update_layout(title="Weekly OOS R", height=280, margin=dict(l=40, r=20, t=40, b=40))
  fig.update_xaxes(tickangle=45)
  return fig


def render():
  st.header("Backtest Lab")
  st.caption("Cấu hình walk-forward, biểu đồ equity/drawdown, log từng tuần")

  report = st.session_state.get("backtest_report") or load_backtest_report()
  warn_no_costs()

  with st.sidebar:
    st.subheader("Cấu hình Backtest")
    use_kb = st.toggle("Use Knowledge Base", value=False, key="lab_use_kb")
    train_months = st.selectbox("Train window (tháng)", [2, 3, 4, 6], index=1, key="lab_train")
    start_date = st.text_input("Start date", "2022-01-01", key="lab_start")
    spread = st.slider("Spread (pips)", 0.0, 3.0, 1.0, 0.1, key="lab_spread")
    slip = st.slider("Slippage (pips)", 0.0, 2.0, 0.3, 0.1, key="lab_slip")
    holdout = st.selectbox("Hold-out forward (tháng)", [0, 6, 12], index=0, key="lab_holdout")

    if st.button("Chạy Backtest", type="primary", use_container_width=True, key="lab_run"):
      if use_kb:
        warn_kb_leak(True)
      prog = st.progress(0)

      def on_prog(step, total, ws):
        prog.progress(step / total, text=f"WF {step}/{total}")

      with st.spinner("Walk-forward..."):
        report = execute_backtest(
          use_learning=use_kb,
          train_months=train_months,
          start_date=start_date,
          spread_pips=spread,
          slippage_pips=slip,
          holdout_months=holdout,
          on_progress=on_prog,
        )
      st.session_state["backtest_report"] = report
      prog.empty()
      st.rerun()

  if use_kb:
    warn_kb_leak(True)

  if not report:
    st.info("Chưa có báo cáo. Cấu hình sidebar và nhấn **Chạy Backtest**.")
    return

  cfg = report.get("config", {})
  st.caption(
    f"Spread: {cfg.get('spread_pips', '?')} pip · "
    f"Slippage: {cfg.get('slippage_pips', '?')} pip · "
    f"Hold-out: {cfg.get('holdout_months', 0)} tháng · "
    f"KB: {'ON' if cfg.get('use_learning_kb') else 'OFF'}"
  )

  if "holdout_forward" in report:
    h = report["holdout_forward"]["metrics"]
    st.success(
      f"Hold-out forward ({report['holdout_forward']['cutoff']}): "
      f"{h['n_trades']} lệnh | WR {h['win_rate_pct']}% | {h['total_r']}R"
    )

  o, y = report["overall_oos"], report["last_1_year"]
  kpi_row([
    ("OOS WR", f"{o['win_rate_pct']}%", None),
    ("RR", f"{o['avg_rr']}", None),
    ("Total R", f"{o['total_r']}", None),
    ("Max DD", f"{o.get('max_drawdown_r', 0)}R", None),
    ("PF", f"{o['profit_factor']}", None),
  ])

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

  st.subheader("Weekly Walk-Forward Log")
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
