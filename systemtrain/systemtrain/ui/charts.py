"""Biểu đồ Plotly — nến + lệnh."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from systemtrain.indicators.library import ema


def make_strategy_chart(
    df: pd.DataFrame,
    trades: list,
    title: str = "",
    show_ema: bool = True,
    max_bars: int = 1500,
) -> go.Figure:
    """Candlestick + marker entry/exit + EMA50/200."""
    if len(df) > max_bars:
        df = df.iloc[-max_bars:]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.75, 0.25], subplot_titles=(title or "EURUSD 1H", "Equity"),
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"], high=df["high"], low=df["low"], close=df["close"],
            name="OHLC",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1, col=1,
    )

    if show_ema and len(df) > 200:
        c = df["close"]
        e50 = ema(c, 50)
        e200 = ema(c, 200)
        fig.add_trace(go.Scatter(x=df.index, y=e50, name="EMA50", line=dict(width=1, color="#ff9800")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=e200, name="EMA200", line=dict(width=1, color="#2196f3")), row=1, col=1)

    long_entry, long_exit, short_entry, short_exit = [], [], [], []
    for t in trades:
        if t.entry_time not in df.index:
            continue
        if t.direction == 1:
            long_entry.append((t.entry_time, t.entry_price))
            if t.exit_time is not None:
                long_exit.append((t.exit_time, t.exit_price))
        else:
            short_entry.append((t.entry_time, t.entry_price))
            if t.exit_time is not None:
                short_exit.append((t.exit_time, t.exit_price))

    if long_entry:
        fig.add_trace(go.Scatter(
            x=[x[0] for x in long_entry], y=[x[1] for x in long_entry],
            mode="markers", name="Long entry",
            marker=dict(symbol="triangle-up", size=12, color="#00c853"),
        ), row=1, col=1)
    if short_entry:
        fig.add_trace(go.Scatter(
            x=[x[0] for x in short_entry], y=[x[1] for x in short_entry],
            mode="markers", name="Short entry",
            marker=dict(symbol="triangle-down", size=12, color="#d50000"),
        ), row=1, col=1)
    if long_exit or short_exit:
        exits = long_exit + short_exit
        colors = ["#00c853"] * len(long_exit) + ["#d50000"] * len(short_exit)
        fig.add_trace(go.Scatter(
            x=[x[0] for x in exits], y=[x[1] for x in exits],
            mode="markers", name="Exit",
            marker=dict(symbol="x", size=9, color=colors),
        ), row=1, col=1)

    # Equity curve từ trades
    if trades:
        eq = 1000.0
        eq_times, eq_vals = [df.index[0]], [eq]
        for t in sorted(trades, key=lambda x: x.exit_time or x.entry_time):
            if t.is_closed:
                eq += t.pnl
                eq_times.append(t.exit_time)
                eq_vals.append(eq)
        fig.add_trace(
            go.Scatter(x=eq_times, y=eq_vals, name="Equity", line=dict(color="#7e57c2", width=2)),
            row=2, col=1,
        )

    fig.update_layout(
        height=680,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=40, t=60, b=40),
    )
    fig.update_xaxes(showgrid=True, gridwidth=0.5)
    fig.update_yaxes(showgrid=True, gridwidth=0.5)
    return fig


def metrics_cards_html(metrics: dict) -> str:
    n = metrics.get("trade_count", 0)
    wr = metrics.get("win_rate", 0)
    pf = metrics.get("profit_factor", 0)
    ret = metrics.get("total_return", 0)
    return (
        f"**{n}** lệnh · WR **{wr:.1%}** · PF **{pf:.2f}** · Return **{ret:+.1%}**"
    )
