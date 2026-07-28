"""6. Risk Dashboard — drawdown, streaks, risk of ruin."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from analytics import equity_series, trades_json_to_df
from config import DEFAULT_MAX_WEEKLY_LOSS_R, DEFAULT_RISK_PCT_PER_TRADE
from strategy import risk_of_ruin_approx
from gui.analysis_support import get_matching_analysis_report, render_report_required_panel
from gui.glossary import HELP, METRIC_LABELS
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.ui_preferences import preference_callback, restore_widget


def render(embedded: bool = False):
  if not embedded:
    render_page_header(ALL_ITEMS["analysis"])

  if render_report_required_panel(key_prefix="risk_rep"):
    return

  report = get_matching_analysis_report()
  assert report is not None

  cfg = report.get("config", {})
  o = report["overall_oos"]
  restore_widget(
    "risk_pct_slider",
    float(cfg.get("risk_pct_per_trade", DEFAULT_RISK_PCT_PER_TRADE)),
    preference_key="analysis.risk_pct",
  )
  risk_pct = st.sidebar.slider(
    "Rủi ro % mỗi lệnh (giả định)", 0.25, 3.0,
    step=0.25, key="risk_pct_slider",
    on_change=preference_callback("risk_pct_slider", "analysis.risk_pct"),
    help="Dùng để ước lượng xác suất phá sản — không phải khuyến nghị vốn thực tế.",
  )
  restore_widget(
    "max_week_r", DEFAULT_MAX_WEEKLY_LOSS_R,
    preference_key="analysis.max_week_r",
  )
  max_weekly_r = st.sidebar.number_input(
    "Giới hạn lỗ tuần (R)", 1.0, 20.0, key="max_week_r",
    on_change=preference_callback("max_week_r", "analysis.max_week_r"),
    help=HELP["r_unit"],
  )

  trades_df = trades_json_to_df(report.get("trades", []))
  ruin_pct = o.get("risk_of_ruin_pct", 0)
  if not trades_df.empty and "r" in trades_df.columns:
    rs = trades_df["r"].astype(float)
    wins = rs > 0
    wr = float(wins.mean())
    aw = float(rs[wins].mean()) if wins.any() else 0.0
    al = float(abs(rs[~wins].mean())) if (~wins).any() else 1.0
    ruin_pct = round(risk_of_ruin_approx(wr, aw, al, risk_pct) * 100, 1)

  c1, c2, c3, c4, c5 = st.columns(5)
  c1.metric(METRIC_LABELS["max_drawdown_r"], f"{o.get('max_drawdown_r', 0)}R")
  c2.metric(METRIC_LABELS["max_win_streak"], o.get("max_win_streak", "—"))
  c3.metric(METRIC_LABELS["max_loss_streak"], o.get("max_loss_streak", "—"))
  c4.metric(METRIC_LABELS["risk_of_ruin_pct"], f"{ruin_pct}%")
  c5.metric("Rủi ro/lệnh", f"{risk_pct}%")

  eq = equity_series(trades_df)
  if not eq.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=eq["entry"], y=eq["equity_r"], name="Equity R", fill="tozeroy"))
    fig.add_trace(go.Scatter(x=eq["entry"], y=-eq["drawdown_r"], name="Drawdown", line=dict(color="red")))
    fig.update_layout(height=400, title="Lợi nhuận & sụt giảm (R)", margin=dict(l=40, r=20, t=40, b=40))
    st.plotly_chart(fig, use_container_width=True)

  st.subheader("Kiểm tra giới hạn lỗ theo tuần")
  if "weekly_log" in report:
    import pandas as pd
    wdf = pd.DataFrame([w for w in report["weekly_log"] if "oos_r" in w])
    if not wdf.empty:
      breach = wdf[wdf["oos_r"] <= -max_weekly_r]
      st.caption(f"Tuần vượt -{max_weekly_r}R: **{len(breach)}** / {len(wdf)}")
      if len(breach):
        st.dataframe(breach[["week_start", "oos_r", "oos_trades"]], hide_index=True)

  if "holdout_forward" in report:
    st.subheader("Giai đoạn test cuối (không dùng khi tối ưu)")
    h = report["holdout_forward"]["metrics"]
    st.json(h)

  st.info(
    f"Với rủi ro **{risk_pct}%**/lệnh và sụt giảm tối đa **{o.get('max_drawdown_r')}R**, "
    f"chuỗi thua dài nhất **{o.get('max_loss_streak')}** lệnh · tổng **{o.get('total_r')}R**. "
    "Xác suất phá sản là **ước lượng thống kê** (expectancy) — không có nghĩa strategy chắc chắn phá sản."
  )
