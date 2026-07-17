"""6. Risk Dashboard — drawdown, streaks, risk of ruin."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from analytics import equity_series, trades_json_to_df
from config import DEFAULT_MAX_WEEKLY_LOSS_R, DEFAULT_RISK_PCT_PER_TRADE
from gui.services import load_backtest_report


def render():
  st.header("Risk Dashboard")
  st.caption("Drawdown, chuỗi thắng/thua, risk of ruin, giới hạn tuần")

  report = st.session_state.get("backtest_report") or load_backtest_report()
  if not report:
    st.info("Chạy backtest trước để xem risk metrics.")
    return

  cfg = report.get("config", {})
  o = report["overall_oos"]
  risk_pct = st.sidebar.slider(
    "Risk % mỗi lệnh (giả định)", 0.25, 3.0,
    float(cfg.get("risk_pct_per_trade", DEFAULT_RISK_PCT_PER_TRADE)),
    0.25, key="risk_pct_slider",
  )
  max_weekly_r = st.sidebar.number_input(
    "Max loss tuần (R)", 1.0, 20.0, DEFAULT_MAX_WEEKLY_LOSS_R, key="max_week_r",
  )

  c1, c2, c3, c4, c5 = st.columns(5)
  c1.metric("Max Drawdown", f"{o.get('max_drawdown_r', 0)}R")
  c2.metric("Max Win Streak", o.get("max_win_streak", "—"))
  c3.metric("Max Loss Streak", o.get("max_loss_streak", "—"))
  c4.metric("Risk of Ruin", f"{o.get('risk_of_ruin_pct', 0)}%")
  c5.metric("Risk/trade", f"{risk_pct}%")

  trades_df = trades_json_to_df(report.get("trades", []))
  eq = equity_series(trades_df)
  if not eq.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq["entry"], y=eq["equity_r"], name="Equity R", fill="tozeroy"))
    fig.add_trace(go.Scatter(x=eq["entry"], y=-eq["drawdown_r"], name="Drawdown", line=dict(color="red")))
    fig.update_layout(height=400, title="Equity & Drawdown (R)", margin=dict(l=40, r=20, t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)

  st.subheader("Weekly loss limit check")
  if "weekly_log" in report:
    import pandas as pd
    wdf = pd.DataFrame([w for w in report["weekly_log"] if "oos_r" in w])
    if not wdf.empty:
      breach = wdf[wdf["oos_r"] <= -max_weekly_r]
      st.caption(f"Tuần vượt -{max_weekly_r}R: **{len(breach)}** / {len(wdf)}")
      if len(breach):
        st.dataframe(breach[["week_start", "oos_r", "oos_trades"]], hide_index=True)

  if "holdout_forward" in report:
    st.subheader("Hold-out forward (chưa dùng khi optimize WF)")
    h = report["holdout_forward"]["metrics"]
    st.json(h)

  st.info(
    f"Với risk **{risk_pct}%**/lệnh và max DD **{o.get('max_drawdown_r')}R**, "
    f"chuỗi thua dài nhất **{o.get('max_loss_streak')}** lệnh. "
    "RoR là ước lượng — không thay thế quản lý vốn thực tế."
  )
