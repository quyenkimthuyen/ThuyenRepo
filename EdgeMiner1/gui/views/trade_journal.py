"""3. Trade Journal — danh sách lệnh + mini chart."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from analytics import (
  exit_reason_stats, direction_bias, filter_trades_df,
  ohlc_around_trade, trades_json_to_df,
)
from gui.components import warn_long_bias, warn_no_costs
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.services import get_ohlc_df, load_backtest_report
from gui.workspace import report_matches_workspace


def _trade_chart(window, trade_row) -> go.Figure | None:
  if window.empty:
    return None
  fig = go.Figure(data=[go.Candlestick(
    x=window.index,
    open=window["Open"], high=window["High"],
    low=window["Low"], close=window["Close"],
    name="EUR/USD H1",
  )])
  entry_t = trade_row["entry"]
  fig.add_vline(x=entry_t, line_dash="dot", line_color="yellow", annotation_text="Entry")
  if "entry_px" in trade_row:
    fig.add_hline(y=trade_row["entry_px"], line_dash="dash", line_color="white", opacity=0.5)
  if "sl" in trade_row and trade_row.get("sl"):
    fig.add_hline(y=trade_row["sl"], line_color="red", annotation_text="SL")
  if "tp" in trade_row and trade_row.get("tp"):
    fig.add_hline(y=trade_row["tp"], line_color="green", annotation_text="TP")
  fig.update_layout(
    title=f"{trade_row.get('dir')} | R={trade_row.get('r')} | {trade_row.get('reason')}",
    height=420, xaxis_rangeslider_visible=False,
    margin=dict(l=40, r=20, t=50, b=40),
  )
  return fig


def render():
  render_page_header(ALL_ITEMS["journal"])

  report = st.session_state.get("backtest_report") or load_backtest_report()
  warn_no_costs()

  if not report or not report.get("trades"):
    st.info("Chưa có lệnh. Chạy backtest trước.")
    return

  if not report_matches_workspace(report):
    st.warning("Journal đang hiển thị báo cáo **không khớp Trade Profile**.")

  trades_df = trades_json_to_df(report["trades"])

  bias = direction_bias(trades_df)
  if not bias.empty:
    st.dataframe(bias, use_container_width=True, hide_index=True)
    if "LONG" in bias["dir"].values:
      warn_long_bias(float(bias.loc[bias["dir"] == "LONG", "pct"].iloc[0]))

  c1, c2, c3, c4 = st.columns(4)
  years = ["All"] + sorted(trades_df["entry"].dt.year.unique().astype(str).tolist())
  with c1:
    year_f = st.selectbox("Năm", years, key="tj_year")
  with c2:
    dir_f = st.selectbox("Hướng", ["All", "LONG", "SHORT"], key="tj_dir")
  with c3:
    reason_f = st.selectbox(
      "Exit",
      ["All"] + sorted(trades_df["reason"].dropna().unique().tolist()),
      key="tj_reason",
    )
  with c4:
    sort_f = st.selectbox("Sắp xếp", ["Mới nhất", "R cao", "R thấp"], key="tj_sort")

  filtered = filter_trades_df(
    trades_df,
    year=int(year_f) if year_f != "All" else None,
    direction=dir_f if dir_f != "All" else None,
  )
  if reason_f != "All":
    filtered = filtered[filtered["reason"] == reason_f]

  if sort_f == "R cao":
    filtered = filtered.sort_values("r", ascending=False)
  elif sort_f == "R thấp":
    filtered = filtered.sort_values("r", ascending=True)
  else:
    filtered = filtered.sort_values("entry", ascending=False)

  st.caption(f"Hiển thị {len(filtered)} / {len(trades_df)} lệnh")

  col_l, col_r = st.columns([1.2, 1])
  with col_l:
    st.dataframe(
      filtered[["entry", "dir", "r", "pnl_pips", "reason", "entry_px", "exit_px"]],
      use_container_width=True, hide_index=True, height=400,
    )
  with col_r:
    st.subheader("Exit breakdown")
    st.dataframe(exit_reason_stats(trades_df), use_container_width=True, hide_index=True)

  st.divider()
  st.subheader("Chi tiết lệnh")
  if filtered.empty:
    st.warning("Không có lệnh sau filter.")
    return

  labels = [
    f"{row.entry.strftime('%Y-%m-%d %H:%M')} | {row.dir} | {row.r}R"
    for row in filtered.head(200).itertuples()
  ]
  idx = st.selectbox("Chọn lệnh", range(len(labels)), format_func=lambda i: labels[i], key="tj_pick")
  trade_row = filtered.iloc[idx]

  try:
    ohlc = get_ohlc_df()
    window = ohlc_around_trade(ohlc, trade_row["entry"], bars=48)
    fig = _trade_chart(window, trade_row)
    if fig:
      st.plotly_chart(fig, use_container_width=True)
  except Exception as e:
    st.caption(f"Không load được chart: {e}")

  st.json(trade_row.to_dict())
