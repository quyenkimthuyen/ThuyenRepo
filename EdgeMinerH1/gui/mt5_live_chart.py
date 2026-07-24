"""TradingView-style chart sourced only from ForgeBridge EA snapshots."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from mt5_bridge.protocol import bars_path, connection_path, read_json

TV_BG = "#131722"
TV_GRID = "#363a45"
TV_TEXT = "#d1d4dc"
TV_UP = "#26a69a"
TV_DOWN = "#ef5350"
TV_ENTRY = "#2962ff"
TV_SL = "#f23645"
TV_TP = "#089981"
TV_LIVE = "#f7c948"


def _parse_mt5_time(value) -> pd.Timestamp | None:
  if value is None or value == "":
    return None
  try:
    ts = pd.to_datetime(str(value), format="%Y.%m.%d %H:%M:%S", errors="coerce")
    if pd.isna(ts):
      ts = pd.to_datetime(str(value), format="%Y.%m.%d %H:%M", errors="coerce")
    if pd.isna(ts):
      ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
      ts = ts.tz_convert(None)
    return ts
  except (TypeError, ValueError):
    return None


def load_ea_chart_data(max_bars: int = 336) -> tuple[pd.DataFrame, dict]:
  """Load EA M15 history and replace the latest candle with its live snapshot."""
  history = read_json(bars_path()) or {}
  connection = read_json(connection_path()) or {}
  rows = list(history.get("bars") or []) if isinstance(history, dict) else []
  current = connection.get("bar") if isinstance(connection, dict) else None
  if isinstance(current, dict):
    rows.append(current)
  if not rows:
    return pd.DataFrame(), connection

  frame = pd.DataFrame(rows)
  required = {"time", "open", "high", "low", "close"}
  if not required.issubset(frame.columns):
    return pd.DataFrame(), connection

  frame["_time"] = frame["time"].map(_parse_mt5_time)
  frame = frame.dropna(subset=["_time"]).copy()
  for col in ("open", "high", "low", "close", "tick_volume"):
    if col in frame:
      frame[col] = pd.to_numeric(frame[col], errors="coerce")
  frame = frame.dropna(subset=["open", "high", "low", "close"])
  frame = frame.sort_values("_time").drop_duplicates("_time", keep="last")
  frame = frame.set_index("_time").tail(max(24, int(max_bars)))
  frame = frame.rename(columns={
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "tick_volume": "Volume",
  })
  if "Volume" not in frame:
    frame["Volume"] = 0
  return frame, connection


def connection_health(connection: dict, stale_after_seconds: float = 10.0) -> dict:
  path = connection_path()
  age = None
  try:
    age = max(0.0, datetime.now().timestamp() - path.stat().st_mtime)
  except OSError:
    pass
  fresh = age is not None and age <= stale_after_seconds
  terminal_connected = bool(connection.get("connected"))
  return {
    "online": fresh and terminal_connected,
    "fresh": fresh,
    "age_seconds": age,
    "terminal_connected": terminal_connected,
    "trade_allowed": bool(
      connection.get("terminal_trade_allowed")
      and connection.get("account_trade_allowed")
    ),
  }


def _add_trade(fig: go.Figure, trade: dict, chart_start, chart_end) -> None:
  """Draw entry / SL / TP / exit like Paper Trade `_add_order_overlays`."""
  entry_time = _parse_mt5_time(
    trade.get("entry_time") or trade.get("entry") or trade.get("signal_time")
  )
  entry = trade.get("entry_px") if trade.get("entry_px") is not None else trade.get("entry")
  if entry_time is None or entry is None:
    return
  try:
    entry = float(entry)
  except (TypeError, ValueError):
    return

  exit_time = _parse_mt5_time(trade.get("exit_time") or trade.get("exit"))
  status = str(trade.get("status") or "CLOSED").upper()
  signal = status == "SIGNAL"
  line_end = exit_time if exit_time is not None else chart_end
  if line_end < chart_start or entry_time > chart_end:
    return
  line_start = max(entry_time, chart_start)
  direction = str(trade.get("direction") or trade.get("dir") or "").upper()
  is_long = direction in ("BUY", "LONG")

  try:
    sl = float(trade["sl"]) if trade.get("sl") is not None else None
  except (TypeError, ValueError):
    sl = None
  try:
    tp = float(trade["tp"]) if trade.get("tp") is not None else None
  except (TypeError, ValueError):
    tp = None

  line_dash = "dash" if signal else "dot"
  risk_fill = "rgba(255,193,7,0.08)" if signal else "rgba(242,54,69,0.12)"
  rew_fill = "rgba(255,193,7,0.06)" if signal else "rgba(8,153,129,0.10)"
  sl_color = "#ffc107" if signal else TV_SL
  tp_color = "#ffc107" if signal else TV_TP

  if sl is not None and tp is not None:
    risk_y0, risk_y1 = (sl, entry) if is_long else (entry, sl)
    rew_y0, rew_y1 = (entry, tp) if is_long else (tp, entry)
    fig.add_shape(
      type="rect", xref="x", yref="y", row=1, col=1,
      x0=line_start, x1=line_end, y0=risk_y0, y1=risk_y1,
      fillcolor=risk_fill, line=dict(width=0),
    )
    fig.add_shape(
      type="rect", xref="x", yref="y", row=1, col=1,
      x0=line_start, x1=line_end, y0=rew_y0, y1=rew_y1,
      fillcolor=rew_fill, line=dict(width=0),
    )
    for y, color, label in ((sl, sl_color, "SL"), (tp, tp_color, "TP")):
      fig.add_trace(go.Scatter(
        x=[line_start, line_end], y=[y, y],
        mode="lines",
        line=dict(color=color, width=1.5, dash=line_dash),
        showlegend=False,
        hovertemplate=f"{label}: %{{y:.5f}}<extra></extra>",
      ), row=1, col=1)
      fig.add_annotation(
        x=line_end, y=y, xref="x", yref="y",
        text=f"{label} {y:.5f}",
        showarrow=False, font=dict(size=9, color=color),
        xanchor="left", xshift=4,
        row=1, col=1,
      )

  if signal:
    signal_t = _parse_mt5_time(trade.get("signal_time")) or entry_time
    if signal_t >= chart_start:
      fig.add_trace(go.Scatter(
        x=[signal_t], y=[entry],
        mode="markers+text",
        marker=dict(symbol="diamond", size=16, color="#ffc107", line=dict(width=2, color="white")),
        text=["🔔 SIGNAL"],
        textposition="top center" if is_long else "bottom center",
        textfont=dict(size=10, color="#ffc107"),
        showlegend=False,
        hovertemplate=(
          f"Tín hiệu {direction}<br>%{{x}}<br>"
          f"Entry dự kiến: {entry}<br>SL: {sl}<br>TP: {tp}<extra></extra>"
        ),
      ), row=1, col=1)
    if entry_time >= chart_start:
      fig.add_trace(go.Scatter(
        x=[entry_time], y=[entry],
        mode="markers+text",
        marker=dict(symbol="circle-open", size=12, color="#ffc107", line=dict(width=2)),
        text=[f"ENTRY? {entry:.5f}"],
        textposition="middle right",
        textfont=dict(size=9, color="#ffc107"),
        showlegend=False,
        hovertemplate="Entry dự kiến<br>%{x} @ %{y:.5f}<extra></extra>",
      ), row=1, col=1)
  elif entry_time >= chart_start:
    marker_symbol = "triangle-up" if is_long else "triangle-down"
    marker_color = TV_UP if is_long else TV_DOWN
    fig.add_trace(go.Scatter(
      x=[entry_time], y=[entry],
      mode="markers+text",
      marker=dict(symbol=marker_symbol, size=14, color=marker_color, line=dict(width=1, color="white")),
      text=[f"ENTRY {entry:.5f}"],
      textposition="top center" if is_long else "bottom center",
      textfont=dict(size=9, color=TV_ENTRY),
      showlegend=False,
      hovertemplate=(
        f"Entry<br>%{{x}}<br>{direction} @ %{{y:.5f}}<br>"
        f"SL: {sl}<br>TP: {tp}<extra></extra>"
      ),
    ), row=1, col=1)

  exit_px = trade.get("exit_px")
  if (
    not signal and status == "CLOSED"
    and exit_time is not None and exit_px is not None
    and exit_time >= chart_start
  ):
    reason = trade.get("reason") or ""
    r_val = trade.get("r") or 0
    exit_color = TV_TP if r_val > 0 else TV_SL
    fig.add_trace(go.Scatter(
      x=[exit_time], y=[float(exit_px)],
      mode="markers+text",
      marker=dict(symbol="x", size=10, color=exit_color, line=dict(width=2)),
      text=[f"EXIT {float(exit_px):.5f}" + (f" ({reason})" if reason else "")],
      textposition="bottom center",
      textfont=dict(size=9, color=exit_color),
      showlegend=False,
      hovertemplate=f"Exit: %{{y:.5f}}<br>R={trade.get('r')}<extra></extra>",
    ), row=1, col=1)
  elif status == "OPEN":
    fig.add_annotation(
      x=entry_time, y=entry, xref="x", yref="y",
      text="● OPEN", showarrow=True, arrowhead=2,
      font=dict(size=10, color="#ffeb3b"),
      bgcolor="rgba(0,0,0,0.6)", bordercolor="#ffeb3b",
      row=1, col=1,
    )


def build_ea_chart(
  frame: pd.DataFrame,
  connection: dict,
  trades: list[dict],
  *,
  title: str = "EURUSD H1 · XM MT5 live",
) -> go.Figure | None:
  if frame.empty:
    return None

  has_volume = "Volume" in frame and frame["Volume"].fillna(0).sum() > 0
  if has_volume:
    fig = make_subplots(
      rows=2, cols=1, shared_xaxes=True,
      row_heights=[0.80, 0.20], vertical_spacing=0.03,
    )
  else:
    fig = make_subplots(rows=1, cols=1)

  fig.add_trace(go.Candlestick(
    x=frame.index,
    open=frame["Open"], high=frame["High"],
    low=frame["Low"], close=frame["Close"],
    increasing_line_color=TV_UP, decreasing_line_color=TV_DOWN,
    increasing_fillcolor=TV_UP, decreasing_fillcolor=TV_DOWN,
    name="EURUSD", showlegend=False,
  ), row=1, col=1)

  if has_volume:
    colors = [
      TV_UP if close >= open_ else TV_DOWN
      for open_, close in zip(frame["Open"], frame["Close"])
    ]
    fig.add_trace(go.Bar(
      x=frame.index, y=frame["Volume"],
      marker_color=colors, opacity=0.45, showlegend=False,
    ), row=2, col=1)
    fig.update_yaxes(title_text="Vol", row=2, col=1)

  chart_start, chart_end = frame.index[0], frame.index[-1]
  for trade in trades:
    _add_trade(fig, trade, chart_start, chart_end)

  bid = connection.get("bid")
  ask = connection.get("ask")
  if bid is not None and ask is not None:
    mid = (float(bid) + float(ask)) / 2
    fig.add_hline(
      y=mid, line_width=1, line_dash="dash", line_color=TV_LIVE,
      annotation_text=f"LIVE {mid:.5f}",
      annotation_font_color=TV_LIVE, row=1, col=1,
    )

  fig.update_layout(
    title=dict(text=title, font=dict(size=14, color=TV_TEXT)),
    template="plotly_dark",
    paper_bgcolor=TV_BG,
    plot_bgcolor=TV_BG,
    font=dict(color=TV_TEXT, size=11),
    height=620 if has_volume else 560,
    margin=dict(l=8, r=96, t=48, b=32),
    hovermode="x unified",
    xaxis_rangeslider_visible=False,
    uirevision="mt5-live-chart",
  )
  fig.update_xaxes(
    gridcolor=TV_GRID, showgrid=True, zeroline=False,
    rangebreaks=[dict(bounds=["sat", "mon"])],
  )
  fig.update_yaxes(gridcolor=TV_GRID, showgrid=True, zeroline=False, side="right")
  fig.update_yaxes(title_text="Price", row=1, col=1)
  return fig
