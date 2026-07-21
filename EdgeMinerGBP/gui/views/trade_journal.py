"""Trade Journal — danh sách lệnh + chart."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from analytics import direction_bias, filter_trades_df, ohlc_around_trade, trades_json_to_df
from gui.analysis_support import get_matching_analysis_report, render_report_required_panel
from gui.analysis_viz import _show_chart, chart_exit_reasons, chart_r_distribution
from gui.components import warn_long_bias
from gui.services import get_ohlc_df


def _trade_chart(window, trade_row) -> go.Figure | None:
  if window.empty:
    return None
  fig = go.Figure(data=[go.Candlestick(
    x=window.index,
    open=window["Open"], high=window["High"],
    low=window["Low"], close=window["Close"],
    name="GBP/USD H1",
    increasing_line_color="#2ecc71",
    decreasing_line_color="#e74c3c",
  )])
  entry_t = trade_row["entry"]
  is_win = float(trade_row.get("r", 0)) > 0
  accent = "#2ecc71" if is_win else "#e74c3c"
  fig.add_vline(x=entry_t, line_dash="dot", line_color=accent, annotation_text="Entry")
  if trade_row.get("entry_px"):
    fig.add_hline(y=trade_row["entry_px"], line_dash="dash", line_color="#bdc3c7", opacity=0.6)
  if trade_row.get("sl"):
    fig.add_hline(y=trade_row["sl"], line_color="#e74c3c", annotation_text="SL")
  if trade_row.get("tp"):
    fig.add_hline(y=trade_row["tp"], line_color="#2ecc71", annotation_text="TP")
  fig.update_layout(
    title=f"{trade_row.get('dir')} · {trade_row.get('r'):+.2f}R · {trade_row.get('reason')}",
    height=440, xaxis_rangeslider_visible=False,
    margin=dict(l=40, r=20, t=50, b=40),
  )
  return fig


def render(embedded: bool = False):
  if render_report_required_panel(key_prefix="tj_rep"):
    return

  report = get_matching_analysis_report()
  if not report or not report.get("trades"):
    st.info("Báo cáo chưa có danh sách lệnh.")
    return

  trades_df = trades_json_to_df(report["trades"])
  wins = (trades_df["r"] > 0).sum()
  losses = len(trades_df) - wins

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Tổng lệnh", len(trades_df))
  m2.metric("Thắng / Thua", f"{wins} / {losses}")
  m3.metric("R trung bình", f"{trades_df['r'].mean():+.2f}")
  m4.metric("R tốt nhất", f"{trades_df['r'].max():+.2f}")

  bias = direction_bias(trades_df)
  if not bias.empty and "LONG" in bias["dir"].values:
    warn_long_bias(float(bias.loc[bias["dir"] == "LONG", "pct"].iloc[0]))

  st.markdown("##### Bộ lọc")
  c1, c2, c3, c4 = st.columns(4)
  years = ["All"] + sorted(trades_df["entry"].dt.year.unique().astype(str).tolist())
  with c1:
    year_f = st.selectbox("Năm", years, key="tj_year", label_visibility="collapsed")
  with c2:
    dir_f = st.selectbox("Hướng", ["All", "LONG", "SHORT"], key="tj_dir", label_visibility="collapsed")
  with c3:
    reason_f = st.selectbox(
      "Exit",
      ["All"] + sorted(trades_df["reason"].dropna().unique().tolist()),
      key="tj_reason", label_visibility="collapsed",
    )
  with c4:
    sort_f = st.selectbox(
      "Sắp xếp", ["Mới nhất", "R cao", "R thấp"],
      key="tj_sort", label_visibility="collapsed",
    )

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

  col_chart, col_exit = st.columns([1.2, 1])
  with col_chart:
    _show_chart(
      chart_r_distribution(filtered if len(filtered) > 5 else trades_df),
      "an_tj_rdist",
    )
  with col_exit:
    _show_chart(chart_exit_reasons(trades_df), "an_tj_exit")

  st.markdown(f"##### Danh sách · {len(filtered)} / {len(trades_df)} lệnh")

  display = filtered.head(80).copy()
  display["entry"] = display["entry"].dt.strftime("%Y-%m-%d %H:%M")
  display["tag"] = display.apply(
    lambda r: f"{'🟢' if r['r'] > 0 else '🔴'} {r['dir']} {r['r']:+.2f}R",
    axis=1,
  )
  st.dataframe(
    display[["tag", "entry", "pnl_pips", "reason", "entry_px", "exit_px"]].rename(
      columns={
        "tag": "Lệnh", "entry": "Thời gian", "pnl_pips": "Pips",
        "reason": "Thoát", "entry_px": "Vào", "exit_px": "Ra",
      },
    ),
    use_container_width=True, hide_index=True, height=320,
  )

  st.markdown("##### Chi tiết & biểu đồ nến")
  if filtered.empty:
    st.warning("Không có lệnh sau filter.")
    return

  labels = [
    f"{'🟢' if row.r > 0 else '🔴'} {row.entry.strftime('%Y-%m-%d %H:%M')} · {row.dir} · {row.r:+.2f}R"
    for row in filtered.head(200).itertuples()
  ]
  idx = st.selectbox("Chọn lệnh", range(len(labels)), format_func=lambda i: labels[i], key="tj_pick")
  trade_row = filtered.iloc[idx]

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Hướng", trade_row["dir"])
  c2.metric("R", f"{trade_row['r']:+.2f}")
  c3.metric("Pips", f"{trade_row.get('pnl_pips', 0):+.1f}")
  c4.metric("Thoát", str(trade_row.get("reason", "—"))[:20])

  try:
    ohlc = get_ohlc_df()
    window = ohlc_around_trade(ohlc, trade_row["entry"], bars=48)
    _show_chart(_trade_chart(window, trade_row), f"an_tj_candle_{idx}")
  except Exception as e:
    st.caption(f"Không load được chart: {e}")
