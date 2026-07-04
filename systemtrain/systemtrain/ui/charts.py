"""Biểu đồ Plotly — phong cách TradingView, hỗ trợ multi-strategy."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from systemtrain.indicators.library import ema
from systemtrain.ui.meta import STRATEGIES, STRATEGY_ORDER

# TradingView dark theme palette
TV = {
    "bg": "#131722",
    "panel": "#1e222d",
    "grid": "#363a45",
    "border": "#434651",
    "text": "#d1d4dc",
    "text_muted": "#787b86",
    "bull": "#089981",
    "bear": "#f23645",
    "bull_wick": "#089981",
    "bear_wick": "#f23645",
    "volume_up": "rgba(8,153,129,0.45)",
    "volume_down": "rgba(242,54,69,0.45)",
    "ema50": "#ff9800",
    "ema200": "#2196f3",
    "equity": "#7e57c2",
}


def strategy_color(name: str) -> str:
    return STRATEGIES.get(name, {}).get("chart_color", "#787b86")


def _slice_df(df: pd.DataFrame, max_bars: int) -> pd.DataFrame:
    return df.iloc[-max_bars:].copy() if len(df) > max_bars else df


def _has_volume(df: pd.DataFrame) -> bool:
    return "volume" in df.columns and df["volume"].sum() > 0


def _add_candles(fig: go.Figure, df: pd.DataFrame, row: int = 1) -> None:
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="EURUSD",
            increasing_line_color=TV["bull"],
            increasing_fillcolor=TV["bull"],
            decreasing_line_color=TV["bear"],
            decreasing_fillcolor=TV["bear"],
            whiskerwidth=0.5,
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def _add_volume(fig: go.Figure, df: pd.DataFrame, row: int) -> None:
    colors = [
        TV["volume_up"] if c >= o else TV["volume_down"]
        for o, c in zip(df["open"], df["close"])
    ]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["volume"],
            name="Volume",
            marker_color=colors,
            showlegend=False,
        ),
        row=row,
        col=1,
    )


def _add_emas(fig: go.Figure, df: pd.DataFrame, row: int = 1) -> None:
    if len(df) <= 200:
        return
    c = df["close"]
    fig.add_trace(
        go.Scatter(
            x=df.index, y=ema(c, 50), name="EMA 50",
            line=dict(width=1.2, color=TV["ema50"]),
            hovertemplate="EMA50: %{y:.5f}<extra></extra>",
        ),
        row=row, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=ema(c, 200), name="EMA 200",
            line=dict(width=1.2, color=TV["ema200"]),
            hovertemplate="EMA200: %{y:.5f}<extra></extra>",
        ),
        row=row, col=1,
    )


def _add_strategy_trades(
    fig: go.Figure,
    trades: list,
    strategy: str,
    color: str,
    df_index: set,
    row: int = 1,
    show_lines: bool = True,
) -> None:
    """Marker entry/exit + đường position (TradingView style)."""
    long_x, long_y, short_x, short_y = [], [], [], []
    exit_x, exit_y, exit_colors, exit_text = [], [], [], []

    for t in trades:
        if t.entry_time not in df_index:
            continue

        if t.direction == 1:
            long_x.append(t.entry_time)
            long_y.append(t.entry_price)
        else:
            short_x.append(t.entry_time)
            short_y.append(t.entry_price)

        if show_lines and t.is_closed and t.exit_time is not None:
            win = t.pnl > 0
            line_color = "rgba(8,153,129,0.55)" if win else "rgba(242,54,69,0.55)"
            fig.add_trace(
                go.Scatter(
                    x=[t.entry_time, t.exit_time],
                    y=[t.entry_price, t.exit_price],
                    mode="lines",
                    line=dict(color=line_color, width=1.5, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=row, col=1,
            )
            exit_x.append(t.exit_time)
            exit_y.append(t.exit_price)
            exit_colors.append("#089981" if win else "#f23645")
            exit_text.append(f"{strategy} exit {t.pnl:+.0f}$")

    label = strategy
    if long_x:
        fig.add_trace(
            go.Scatter(
                x=long_x, y=long_y,
                mode="markers+text" if len(long_x) <= 12 else "markers",
                name=f"{label} Long",
                text=["▲"] * len(long_x) if len(long_x) <= 12 else None,
                textposition="bottom center",
                textfont=dict(size=11, color=color),
                marker=dict(
                    symbol="triangle-up", size=13, color=color,
                    line=dict(width=1, color=TV["bg"]),
                ),
                hovertemplate=f"<b>{label}</b> LONG<br>%{{x}}<br>%{{y:.5f}}<extra></extra>",
            ),
            row=row, col=1,
        )
    if short_x:
        fig.add_trace(
            go.Scatter(
                x=short_x, y=short_y,
                mode="markers+text" if len(short_x) <= 12 else "markers",
                name=f"{label} Short",
                text=["▼"] * len(short_x) if len(short_x) <= 12 else None,
                textposition="top center",
                textfont=dict(size=11, color=color),
                marker=dict(
                    symbol="triangle-down", size=13, color=color,
                    line=dict(width=1, color=TV["bg"]),
                ),
                hovertemplate=f"<b>{label}</b> SHORT<br>%{{x}}<br>%{{y:.5f}}<extra></extra>",
            ),
            row=row, col=1,
        )
    if exit_x:
        fig.add_trace(
            go.Scatter(
                x=exit_x, y=exit_y,
                mode="markers",
                name=f"{label} Exit",
                marker=dict(symbol="circle-open", size=9, color=exit_colors, line=dict(width=2)),
                text=exit_text,
                hovertemplate="%{text}<br>%{x}<br>%{y:.5f}<extra></extra>",
            ),
            row=row, col=1,
        )


def _add_equity(fig: go.Figure, all_trades: list, equity: float, row: int) -> None:
    closed = [t for t in all_trades if t.is_closed]
    if not closed:
        return
    bal = equity
    times = [closed[0].entry_time]
    vals = [bal]
    for t in sorted(closed, key=lambda x: x.exit_time or x.entry_time):
        bal += t.pnl
        times.append(t.exit_time)
        vals.append(bal)
    fig.add_trace(
        go.Scatter(
            x=times, y=vals, name="Equity",
            line=dict(color=TV["equity"], width=2),
            fill="tozeroy",
            fillcolor="rgba(126,87,194,0.12)",
            hovertemplate="Equity: $%{y:.2f}<extra></extra>",
        ),
        row=row, col=1,
    )


def _apply_tv_layout(fig: go.Figure, title: str, rows: int, equity_row: int) -> None:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=TV["text"]), x=0.01, xanchor="left"),
        height=780 if rows >= 3 else 720,
        template=None,
        paper_bgcolor=TV["bg"],
        plot_bgcolor=TV["panel"],
        font=dict(family="Trebuchet MS, Roboto, sans-serif", color=TV["text"], size=11),
        margin=dict(l=8, r=60, t=48, b=8),
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, x=0,
            bgcolor="rgba(30,34,45,0.8)", bordercolor=TV["border"], borderwidth=1,
            font=dict(size=10),
        ),
        dragmode="pan",
    )
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=TV["grid"],
        showline=True, linewidth=1, linecolor=TV["border"],
        tickfont=dict(color=TV["text_muted"]),
        spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor=TV["text_muted"],
        rangeslider=dict(visible=True, bgcolor=TV["panel"], thickness=0.04),
        row=1, col=1,
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor=TV["grid"],
        showline=True, linewidth=1, linecolor=TV["border"],
        tickfont=dict(color=TV["text_muted"]),
        side="right",
        spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor=TV["text_muted"],
        row=1, col=1,
    )
    if rows >= 3:
        fig.update_xaxes(showgrid=False, showticklabels=False, row=2, col=1)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TV["grid"], side="right", row=2, col=1)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=TV["grid"], row=equity_row, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TV["grid"], side="right", row=equity_row, col=1)
    # Hide rangeslider on sub-rows
    for r in range(2, rows + 1):
        fig.update_xaxes(rangeslider_visible=False, row=r, col=1)


def make_tradingview_chart(
    df: pd.DataFrame,
    strategy_trades: dict[str, list] | None = None,
    *,
    trades: list | None = None,
    strategy_name: str = "",
    title: str = "",
    show_ema: bool = True,
    show_volume: bool = True,
    equity: float = 1000.0,
    max_bars: int = 2000,
) -> go.Figure:
    """Candlestick TradingView-style + multi-strategy markers."""
    df = _slice_df(df, max_bars)
    df_index = set(df.index)

    if strategy_trades is None:
        strategy_trades = {strategy_name or "Strategy": trades or []}

    use_vol = show_volume and _has_volume(df)
    row_heights = [0.62, 0.14, 0.24] if use_vol else [0.72, 0.28]
    rows = 3 if use_vol else 2
    equity_row = 3 if use_vol else 2
    subtitles = [title or "EURUSD 1H", "Volume", "Equity"] if use_vol else [title or "EURUSD 1H", "Equity"]

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=row_heights,
        subplot_titles=subtitles,
    )

    _add_candles(fig, df, row=1)
    if show_ema:
        _add_emas(fig, df, row=1)
    if use_vol:
        _add_volume(fig, df, row=2)

    for sname in STRATEGY_ORDER:
        if sname not in strategy_trades:
            continue
        _add_strategy_trades(fig, strategy_trades[sname], sname, strategy_color(sname), df_index, row=1)

    all_trades = [t for ts in strategy_trades.values() for t in ts]
    _add_equity(fig, all_trades, equity, row=equity_row)
    _apply_tv_layout(fig, title, rows, equity_row)
    return fig


def make_strategy_chart(
    df: pd.DataFrame,
    trades: list,
    title: str = "",
    show_ema: bool = True,
    max_bars: int = 2000,
) -> go.Figure:
    """Backward-compatible single-strategy chart."""
    name = title.split("—")[0].strip() if "—" in title else "Strategy"
    return make_tradingview_chart(
        df,
        {name: trades},
        title=title,
        show_ema=show_ema,
        max_bars=max_bars,
    )


def metrics_cards_html(metrics: dict) -> str:
    n = metrics.get("trade_count", 0)
    wr = metrics.get("win_rate", 0)
    pf = metrics.get("profit_factor", 0)
    ret = metrics.get("total_return", 0)
    return f"**{n}** lệnh · WR **{wr:.1%}** · PF **{pf:.2f}** · Return **{ret:+.1%}**"


def metrics_all_html(results: dict[str, dict[str, Any]]) -> str:
    parts = []
    total_ret = 0.0
    total_n = 0
    for sname in STRATEGY_ORDER:
        if sname not in results:
            continue
        m = results[sname]["metrics"]
        color = strategy_color(sname)
        parts.append(
            f"<span style='color:{color}'><b>{sname}</b></span>: "
            f"{m.get('trade_count', 0)}t · WR {m.get('win_rate', 0):.0%} · {m.get('total_return', 0):+.1%}"
        )
        total_ret += m.get("total_return", 0)
        total_n += m.get("trade_count", 0)
    parts.append(f"**Tổng:** {total_n} lệnh · {total_ret:+.1%}")
    return " &nbsp;|&nbsp; ".join(parts)
