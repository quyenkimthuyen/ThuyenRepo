"""Biểu đồ Plotly — phong cách TradingView, hỗ trợ multi-strategy."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from systemtrain.indicators.library import ema, rsi
from systemtrain.ui.chart_component import render_lightweight_chart
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


def _chart_profile(strategy: str) -> dict[str, Any]:
    return STRATEGIES.get(strategy, {}).get("chart", {})


def _bar_duration(df: pd.DataFrame) -> pd.Timedelta:
    if len(df) < 2:
        return pd.Timedelta(hours=1)
    return df.index[1] - df.index[0]


def _focus_df_around_trades(df: pd.DataFrame, trades: list, pad: int = 80) -> pd.DataFrame:
    """Thu hẹp vùng hiển thị quanh các lệnh để minh họa rõ hơn."""
    if not trades:
        return df
    locs = []
    for t in trades:
        if t.entry_time in df.index:
            locs.append(df.index.get_loc(t.entry_time))
    if not locs:
        return df
    i0 = max(0, min(locs) - pad)
    i1 = min(len(df), max(locs) + pad + 1)
    return df.iloc[i0:i1].copy()


def _slice_df(df: pd.DataFrame, max_bars: int) -> pd.DataFrame:
    return df.iloc[-max_bars:].copy() if len(df) > max_bars else df


def _has_volume(df: pd.DataFrame) -> bool:
    return "volume" in df.columns and df["volume"].sum() > 0


def _chart_time(value: Any) -> int:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return int(ts.timestamp())


def _line_points(start: Any, end: Any, value: float) -> list[dict[str, float | int]]:
    return [
        {"time": _chart_time(start), "value": float(value)},
        {"time": _chart_time(end), "value": float(value)},
    ]


def _series_points(series: pd.Series) -> list[dict[str, float | int]]:
    clean = series.dropna()
    return [
        {"time": _chart_time(idx), "value": float(value)}
        for idx, value in clean.items()
    ]


def _equity_points(trades: list, equity: float) -> list[dict[str, float | int]]:
    closed = [t for t in trades if t.is_closed]
    if not closed:
        return []
    balance = float(equity)
    points = [{"time": _chart_time(closed[0].entry_time), "value": balance}]
    for trade in sorted(closed, key=lambda x: x.exit_time or x.entry_time):
        balance += float(trade.pnl)
        points.append({"time": _chart_time(trade.exit_time), "value": balance})
    return points


def build_chart_payload(
    df: pd.DataFrame,
    strategy: str,
    trades: list,
    *,
    show_ema: bool | None = None,
    show_volume: bool = False,
    equity: float = 1000.0,
    max_bars: int = 2000,
    focus_trades: bool = False,
    focus_trade: Any | None = None,
    setup_signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Serialize OHLCV and trade overlays for the Lightweight Charts renderer."""
    profile = _chart_profile(strategy)
    work = _slice_df(df, max_bars)
    if focus_trade is not None:
        work = _focus_df_around_trades(work, [focus_trade], pad=120)
    elif focus_trades and trades:
        work = _focus_df_around_trades(work, trades)

    df_index = set(work.index)
    color = strategy_color(strategy)
    candles = [
        {
            "time": _chart_time(idx),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for idx, row in work[["open", "high", "low", "close"]].iterrows()
    ]

    volume: list[dict[str, float | int | str]] = []
    if show_volume and _has_volume(work):
        volume = [
            {
                "time": _chart_time(idx),
                "value": float(row["volume"]),
                "color": TV["volume_up"] if row["close"] >= row["open"] else TV["volume_down"],
            }
            for idx, row in work[["open", "close", "volume"]].iterrows()
        ]

    overlays: list[dict[str, Any]] = []
    use_ema = profile.get("show_ema", False) if show_ema is None else show_ema
    if use_ema and len(work) > 200:
        overlays.extend(
            [
                {"name": "EMA 50", "color": TV["ema50"], "width": 1, "data": _series_points(ema(work["close"], 50))},
                {"name": "EMA 200", "color": TV["ema200"], "width": 1, "data": _series_points(ema(work["close"], 200))},
            ]
        )

    indicator: dict[str, Any] | None = None
    if profile.get("show_rsi", False):
        indicator = {
            "name": "RSI 14",
            "color": TV["ema50"],
            "data": _series_points(rsi(work["close"], 14)),
        }

    markers: list[dict[str, Any]] = []
    trade_lines: list[dict[str, Any]] = []
    last_x = work.index[-1] if len(work) else None
    for signal in setup_signals or []:
        ts = pd.Timestamp(signal.get("time"))
        if ts not in df_index:
            continue
        direction = int(signal.get("direction", 0))
        is_long = direction == 1
        markers.append(
            {
                "time": _chart_time(ts),
                "position": "belowBar" if is_long else "aboveBar",
                "color": color,
                "shape": "arrowUp" if is_long else "arrowDown",
                "text": f"SETUP {strategy}",
            }
        )
    for trade in trades:
        if trade.entry_time not in df_index:
            continue

        is_long = trade.direction == 1
        markers.append(
            {
                "time": _chart_time(trade.entry_time),
                "position": "belowBar" if is_long else "aboveBar",
                "color": color,
                "shape": "arrowUp" if is_long else "arrowDown",
                "text": "LONG" if is_long else "SHORT",
            }
        )

        if trade.is_closed and trade.exit_time is not None:
            win = trade.pnl > 0
            markers.append(
                {
                    "time": _chart_time(trade.exit_time),
                    "position": "aboveBar" if is_long else "belowBar",
                    "color": TV["bull"] if win else TV["bear"],
                    "shape": "circle",
                    "text": f"{trade.pnl:+.0f}$",
                }
            )
            trade_lines.append(
                {
                    "name": "Trade path",
                    "color": "rgba(8,153,129,0.65)" if win else "rgba(242,54,69,0.65)",
                    "style": "dashed",
                    "width": 1,
                    "data": [
                        {"time": _chart_time(trade.entry_time), "value": float(trade.entry_price)},
                        {"time": _chart_time(trade.exit_time), "value": float(trade.exit_price)},
                    ],
                }
            )

        if profile.get("show_sl_tp", True) and last_x is not None:
            end_x = trade.exit_time if trade.exit_time is not None else last_x
            trade_lines.extend(
                [
                    {
                        "name": "SL",
                        "color": "rgba(242,54,69,0.85)",
                        "style": "dashed",
                        "width": 1,
                        "data": _line_points(trade.entry_time, end_x, trade.sl_price),
                    },
                    {
                        "name": "TP",
                        "color": "rgba(8,153,129,0.85)",
                        "style": "dotted",
                        "width": 1,
                        "data": _line_points(trade.entry_time, end_x, trade.tp_price),
                    },
                ]
            )

    closed = [t for t in trades if t.is_closed]
    pnl = sum(float(t.pnl) for t in closed)
    return {
        "symbol": "EURUSD",
        "strategy": strategy,
        "title": STRATEGIES.get(strategy, {}).get("title", strategy),
        "candles": candles,
        "volume": volume,
        "overlays": overlays,
        "indicator": indicator,
        "equity": _equity_points(closed, equity),
        "markers": markers,
        "trade_lines": trade_lines,
        "summary": {
            "bars": len(candles),
            "trades": len(closed),
            "pnl": pnl,
        },
    }


def build_multi_strategy_payload(
    df: pd.DataFrame,
    strategy_trades: dict[str, list],
    *,
    show_ema: bool = True,
    show_volume: bool = False,
    equity: float = 1000.0,
    max_bars: int = 2000,
    focus_trades: bool = False,
    focus_trade: Any | None = None,
    setup_signals: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Serialize one price chart with setup markers from many strategies."""
    all_trades = [trade for trades in strategy_trades.values() for trade in trades]
    work = _slice_df(df, max_bars)
    if focus_trade is not None:
        work = _focus_df_around_trades(work, [focus_trade], pad=120)
    elif focus_trades and all_trades:
        work = _focus_df_around_trades(work, all_trades)

    df_index = set(work.index)
    candles = [
        {
            "time": _chart_time(idx),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for idx, row in work[["open", "high", "low", "close"]].iterrows()
    ]

    volume: list[dict[str, float | int | str]] = []
    if show_volume and _has_volume(work):
        volume = [
            {
                "time": _chart_time(idx),
                "value": float(row["volume"]),
                "color": TV["volume_up"] if row["close"] >= row["open"] else TV["volume_down"],
            }
            for idx, row in work[["open", "close", "volume"]].iterrows()
        ]

    overlays: list[dict[str, Any]] = []
    if show_ema and len(work) > 200:
        overlays.extend(
            [
                {"name": "EMA 50", "color": TV["ema50"], "width": 1, "data": _series_points(ema(work["close"], 50))},
                {"name": "EMA 200", "color": TV["ema200"], "width": 1, "data": _series_points(ema(work["close"], 200))},
            ]
        )

    markers: list[dict[str, Any]] = []
    trade_lines: list[dict[str, Any]] = []
    last_x = work.index[-1] if len(work) else None
    for strategy, signals in (setup_signals or {}).items():
        color = strategy_color(strategy)
        for signal in signals:
            ts = pd.Timestamp(signal.get("time"))
            if ts not in df_index:
                continue
            direction = int(signal.get("direction", 0))
            is_long = direction == 1
            markers.append(
                {
                    "time": _chart_time(ts),
                    "position": "belowBar" if is_long else "aboveBar",
                    "color": color,
                    "shape": "arrowUp" if is_long else "arrowDown",
                    "text": f"SETUP {strategy}",
                }
            )
    for strategy, trades in strategy_trades.items():
        color = strategy_color(strategy)
        short_name = STRATEGIES.get(strategy, {}).get("id", strategy)[:10]
        profile = _chart_profile(strategy)
        for trade in trades:
            if trade.entry_time not in df_index:
                continue
            is_long = trade.direction == 1
            markers.append(
                {
                    "time": _chart_time(trade.entry_time),
                    "position": "belowBar" if is_long else "aboveBar",
                    "color": color,
                    "shape": "arrowUp" if is_long else "arrowDown",
                    "text": f"{strategy} {'LONG' if is_long else 'SHORT'}",
                }
            )
            if trade.is_closed and trade.exit_time is not None:
                win = trade.pnl > 0
                markers.append(
                    {
                        "time": _chart_time(trade.exit_time),
                        "position": "aboveBar" if is_long else "belowBar",
                        "color": color,
                        "shape": "circle",
                        "text": f"{short_name} {trade.pnl:+.0f}$",
                    }
                )
                trade_lines.append(
                    {
                        "name": f"{strategy} path",
                        "color": "rgba(8,153,129,0.45)" if win else "rgba(242,54,69,0.45)",
                        "style": "dashed",
                        "width": 1,
                        "data": [
                            {"time": _chart_time(trade.entry_time), "value": float(trade.entry_price)},
                            {"time": _chart_time(trade.exit_time), "value": float(trade.exit_price)},
                        ],
                    }
                )

            if profile.get("show_sl_tp", True) and last_x is not None:
                end_x = trade.exit_time if trade.exit_time is not None else last_x
                trade_lines.extend(
                    [
                        {
                            "name": f"{strategy} SL",
                            "color": "rgba(242,54,69,0.45)",
                            "style": "dashed",
                            "width": 1,
                            "data": _line_points(trade.entry_time, end_x, trade.sl_price),
                        },
                        {
                            "name": f"{strategy} TP",
                            "color": "rgba(8,153,129,0.45)",
                            "style": "dotted",
                            "width": 1,
                            "data": _line_points(trade.entry_time, end_x, trade.tp_price),
                        },
                    ]
                )

    closed = [trade for trade in all_trades if trade.is_closed]
    return {
        "symbol": "EURUSD",
        "strategy": "All",
        "title": "All Strategies Replay",
        "candles": candles,
        "volume": volume,
        "overlays": overlays,
        "indicator": None,
        "equity": _equity_points(closed, equity),
        "markers": sorted(markers, key=lambda item: item["time"]),
        "trade_lines": trade_lines,
        "summary": {
            "bars": len(candles),
            "trades": len(closed),
            "pnl": sum(float(trade.pnl) for trade in closed),
        },
    }


def render_professional_chart(
    df: pd.DataFrame,
    strategy: str,
    trades: list,
    *,
    chart_id: str,
    show_ema: bool | None = None,
    show_volume: bool = False,
    equity: float = 1000.0,
    max_bars: int = 2000,
    height: int = 640,
    focus_trades: bool = False,
    focus_trade: Any | None = None,
    setup_signals: list[dict[str, Any]] | None = None,
) -> None:
    payload = build_chart_payload(
        df,
        strategy,
        trades,
        show_ema=show_ema,
        show_volume=show_volume,
        equity=equity,
        max_bars=max_bars,
        focus_trades=focus_trades,
        focus_trade=focus_trade,
        setup_signals=setup_signals,
    )
    render_lightweight_chart(payload, height=height, key=f"lw-{chart_id}")


def render_professional_multi_strategy_chart(
    df: pd.DataFrame,
    strategy_trades: dict[str, list],
    *,
    chart_id: str,
    show_ema: bool = True,
    show_volume: bool = False,
    equity: float = 1000.0,
    max_bars: int = 2000,
    height: int = 640,
    focus_trades: bool = False,
    focus_trade: Any | None = None,
    setup_signals: dict[str, list[dict[str, Any]]] | None = None,
) -> None:
    payload = build_multi_strategy_payload(
        df,
        strategy_trades,
        show_ema=show_ema,
        show_volume=show_volume,
        equity=equity,
        max_bars=max_bars,
        focus_trades=focus_trades,
        focus_trade=focus_trade,
        setup_signals=setup_signals,
    )
    render_lightweight_chart(payload, height=height, key=f"lw-{chart_id}")


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
            showlegend=False,
        ),
        row=row, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, y=ema(c, 200), name="EMA 200",
            line=dict(width=1.2, color=TV["ema200"]),
            hovertemplate="EMA200: %{y:.5f}<extra></extra>",
            showlegend=False,
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
    """Marker entry/exit — tên chiến lược qua hover."""
    long_x, long_y, short_x, short_y = [], [], [], []
    exit_x, exit_y, exit_text = [], [], []

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
            line_color = "rgba(8,153,129,0.45)" if win else "rgba(242,54,69,0.45)"
            fig.add_trace(
                go.Scatter(
                    x=[t.entry_time, t.exit_time],
                    y=[t.entry_price, t.exit_price],
                    mode="lines",
                    line=dict(color=line_color, width=1, dash="dot"),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=row, col=1,
            )
            exit_x.append(t.exit_time)
            exit_y.append(t.exit_price)
            exit_text.append(f"{t.pnl:+.0f}$")

    entry_hover = f"<b>{strategy}</b><br>%{{customdata}}<br>%{{x}}<br>%{{y:.5f}}<extra></extra>"

    if long_x:
        fig.add_trace(
            go.Scatter(
                x=long_x, y=long_y,
                mode="markers",
                name=strategy,
                legendgroup=strategy,
                showlegend=False,
                customdata=["LONG"] * len(long_x),
                marker=dict(
                    symbol="triangle-up", size=10, color=color,
                    line=dict(width=0.5, color=TV["bg"]),
                ),
                hovertemplate=entry_hover,
            ),
            row=row, col=1,
        )

    if short_x:
        fig.add_trace(
            go.Scatter(
                x=short_x, y=short_y,
                mode="markers",
                name=strategy,
                legendgroup=strategy,
                showlegend=False,
                customdata=["SHORT"] * len(short_x),
                marker=dict(
                    symbol="triangle-down", size=10, color=color,
                    line=dict(width=0.5, color=TV["bg"]),
                ),
                hovertemplate=entry_hover,
            ),
            row=row, col=1,
        )

    if exit_x:
        fig.add_trace(
            go.Scatter(
                x=exit_x, y=exit_y,
                mode="markers",
                legendgroup=strategy,
                showlegend=False,
                marker=dict(symbol="circle-open", size=7, color=color, line=dict(width=1.5)),
                text=exit_text,
                hovertemplate="%{text}<br>%{x}<br>%{y:.5f}<extra></extra>",
            ),
            row=row, col=1,
        )


def _add_sl_tp_levels(
    fig: go.Figure,
    trades: list,
    df: pd.DataFrame,
    df_index: set,
    row: int = 1,
) -> None:
    """Vẽ SL/TP từ entry → exit (minh họa risk/reward từng lệnh)."""
    last_x = df.index[-1]
    for t in trades:
        if t.entry_time not in df_index:
            continue
        x1 = t.exit_time if t.exit_time is not None else last_x
        for price, color, dash in (
            (t.sl_price, "rgba(242,54,69,0.85)", "dash"),
            (t.tp_price, "rgba(8,153,129,0.85)", "dot"),
        ):
            fig.add_trace(
                go.Scatter(
                    x=[t.entry_time, x1],
                    y=[price, price],
                    mode="lines",
                    line=dict(color=color, width=1.2, dash=dash),
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=row, col=1,
            )


def _highlight_entry_bars(
    fig: go.Figure,
    df: pd.DataFrame,
    trades: list,
    color: str,
    row: int = 1,
) -> None:
    """Tô nến tín hiệu / entry (pin bar, wyckoff sweep, ema bounce)."""
    dur = _bar_duration(df)
    seen: set = set()
    for t in trades:
        if t.entry_time not in df.index:
            continue
        idx = df.index.get_loc(t.entry_time)
        for bar_i in (max(0, idx - 1), idx):
            ts = df.index[bar_i]
            if ts in seen:
                continue
            seen.add(ts)
            lo, hi = float(df.iloc[bar_i]["low"]), float(df.iloc[bar_i]["high"])
            fig.add_shape(
                type="rect",
                x0=ts, x1=ts + dur,
                y0=lo, y1=hi,
                fillcolor=color,
                opacity=0.18,
                line=dict(color=color, width=1),
                layer="below",
                row=row, col=1,
            )


def _add_rsi_panel(fig: go.Figure, df: pd.DataFrame, row: int) -> None:
    r = rsi(df["close"], 14)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=r, name="RSI",
            line=dict(color=TV["ema50"], width=1.2),
            showlegend=False,
            hovertemplate="RSI: %{y:.1f}<extra></extra>",
        ),
        row=row, col=1,
    )
    for lvl, c in ((30, TV["bull"]), (70, TV["bear"]), (50, TV["text_muted"])):
        fig.add_hline(y=lvl, line=dict(color=c, width=0.6, dash="dot"), row=row, col=1)


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
            showlegend=False,
        ),
        row=row, col=1,
    )


def _apply_tv_layout(
    fig: go.Figure,
    title: str,
    rows: int,
    equity_row: int,
    height: int | None = None,
    dragmode: str = "pan",
) -> None:
    layout_kw: dict[str, Any] = dict(
        title=None,
        autosize=True,
        showlegend=False,
        template=None,
        paper_bgcolor=TV["bg"],
        plot_bgcolor=TV["panel"],
        font=dict(family="Trebuchet MS, Roboto, sans-serif", color=TV["text"], size=11),
        margin=dict(l=4, r=52, t=12, b=4),
        hovermode="x unified",
        dragmode=dragmode,
        uirevision="tv-chart",
        hoverlabel=dict(bgcolor=TV["panel"], bordercolor=TV["border"], font_size=11),
    )
    if height is not None:
        layout_kw["height"] = height
    fig.update_layout(**layout_kw)
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor=TV["grid"],
        showline=True, linewidth=1, linecolor=TV["border"],
        tickfont=dict(color=TV["text_muted"], size=10),
        spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor=TV["text_muted"],
        rangeselector=dict(
            bgcolor=TV["panel"],
            activecolor=TV["border"],
            bordercolor=TV["border"],
            font=dict(color=TV["text"], size=10),
            buttons=[
                dict(count=1, label="1D", step="day", stepmode="backward"),
                dict(count=5, label="5D", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(step="all", label="All"),
            ],
        ),
        rangeslider=dict(visible=True, bgcolor=TV["panel"], thickness=0.055),
        fixedrange=False,
        row=1, col=1,
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor=TV["grid"],
        showline=True, linewidth=1, linecolor=TV["border"],
        tickfont=dict(color=TV["text_muted"], size=10),
        side="right",
        spikemode="across", spikesnap="cursor", spikethickness=1, spikecolor=TV["text_muted"],
        fixedrange=False,
        autorange=True,
        row=1, col=1,
    )
    if rows >= 3:
        fig.update_xaxes(showgrid=False, showticklabels=False, fixedrange=False, row=2, col=1)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TV["grid"], side="right", fixedrange=False, row=2, col=1)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor=TV["grid"], fixedrange=False, row=equity_row, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor=TV["grid"], side="right", fixedrange=False, row=equity_row, col=1)
    for r in range(2, rows + 1):
        fig.update_xaxes(rangeslider_visible=False, row=r, col=1)
    # Ẩn tiêu đề subplot (gây chồng chéo)
    for ann in fig.layout.annotations or []:
        ann.text = ""


PLOTLY_CHART_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
    "doubleClick": "reset+autosize",
    "modeBarButtonsToAdd": [
        "pan2d",
        "zoom2d",
        "zoomIn2d",
        "zoomOut2d",
        "autoScale2d",
        "resetScale2d",
    ],
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def render_resizable_plotly(
    fig: go.Figure,
    *,
    chart_id: str,
    default_height: int = 560,
) -> None:
    """Chart TradingView — hiển thị ổn định + kéo góc phải-dưới để resize."""
    fig.update_layout(height=default_height, autosize=True)
    st.plotly_chart(
        fig,
        use_container_width=True,
        config=PLOTLY_CHART_CONFIG,
        key=f"plotly-{chart_id}",
    )


def make_strategy_illustration_chart(strategy: str) -> go.Figure:
    """Small overview chart that explains each strategy visually."""
    color = strategy_color(strategy)
    idx = pd.date_range("2024-01-01", periods=18, freq="h")

    if strategy == "Wyckoff":
        close = [1.1000, 1.1010, 1.1004, 1.1012, 1.1006, 1.1014, 1.1008, 1.1011, 1.1002, 1.0984, 1.1007, 1.1018, 1.1028, 1.1035, 1.1042, 1.1048, 1.1054, 1.1060]
        note = "Sweep liquidity -> reclaim range"
        marker_i = 10
    elif strategy == "RSI Divergence":
        close = [1.1060, 1.1048, 1.1036, 1.1022, 1.1015, 1.1026, 1.1010, 1.0998, 1.1009, 1.1020, 1.1032, 1.1044, 1.1050, 1.1058, 1.1064, 1.1070, 1.1075, 1.1080]
        note = "Price lower low, RSI higher low"
        marker_i = 8
    elif strategy in ("EMA 50/200", "EMA Flow"):
        close = [1.1000, 1.1010, 1.1022, 1.1030, 1.1042, 1.1055, 1.1066, 1.1059, 1.1052, 1.1048, 1.1058, 1.1070, 1.1082, 1.1090, 1.1100, 1.1110, 1.1118, 1.1124]
        note = "Pullback to EMA50 inside trend"
        marker_i = 10
    else:
        close = [1.1030, 1.1026, 1.1020, 1.1012, 1.1008, 1.1002, 1.0994, 1.0988, 1.1004, 1.1014, 1.1022, 1.1032, 1.1040, 1.1048, 1.1054, 1.1060, 1.1064, 1.1068]
        note = "Long wick rejection at swing"
        marker_i = 8

    opens = [close[0]] + close[:-1]
    highs = [max(o, c) + 0.00045 for o, c in zip(opens, close)]
    lows = [min(o, c) - 0.00045 for o, c in zip(opens, close)]
    if strategy == "Pin Bar Elite":
        lows[marker_i] = min(lows[marker_i], close[marker_i] - 0.0026)
    if strategy == "Wyckoff":
        lows[marker_i - 1] = min(lows[marker_i - 1], close[marker_i - 1] - 0.0016)

    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": close}, index=idx)
    is_rsi_divergence = strategy == "RSI Divergence"
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.68, 0.32],
    ) if is_rsi_divergence else go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Setup",
            increasing_line_color=TV["bull"],
            increasing_fillcolor=TV["bull"],
            decreasing_line_color=TV["bear"],
            decreasing_fillcolor=TV["bear"],
            whiskerwidth=0.5,
            showlegend=False,
        ),
        row=1 if is_rsi_divergence else None,
        col=1 if is_rsi_divergence else None,
    )

    if strategy in ("EMA 50/200", "EMA Flow"):
        fast = pd.Series(close, index=idx).rolling(4, min_periods=1).mean()
        slow = pd.Series(close, index=idx).rolling(9, min_periods=1).mean() - 0.0009
        fig.add_trace(go.Scatter(x=idx, y=fast, mode="lines", line=dict(color=TV["ema50"], width=1.5), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=idx, y=slow, mode="lines", line=dict(color=TV["ema200"], width=1.5), hoverinfo="skip", showlegend=False))
    elif strategy == "RSI Divergence":
        rsi_demo = [42, 36, 30, 25, 22, 33, 29, 34, 41, 48, 54, 58, 61, 64, 66, 67, 68, 69]
        fig.add_trace(
            go.Scatter(x=[idx[4], idx[7]], y=[lows[4], lows[7]], mode="lines+markers", line=dict(color=TV["bear"], width=1.8, dash="dot"), marker=dict(size=6), hoverinfo="skip", showlegend=False),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=idx, y=rsi_demo, mode="lines", line=dict(color=TV["ema50"], width=1.5), hovertemplate="RSI: %{y:.0f}<extra></extra>", showlegend=False),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=[idx[4], idx[7]], y=[rsi_demo[4], rsi_demo[7]], mode="lines+markers", line=dict(color=TV["bull"], width=1.8, dash="dot"), marker=dict(size=6), hoverinfo="skip", showlegend=False),
            row=2,
            col=1,
        )
        for level in (30, 50, 70):
            fig.add_hline(y=level, line=dict(color=TV["grid"], width=0.8, dash="dot"), row=2, col=1)
    else:
        fig.add_hrect(
            y0=min(close[2:8]) - 0.0002,
            y1=max(close[2:8]) + 0.0002,
            fillcolor=color,
            opacity=0.08,
            line_width=0,
        )

    fig.add_trace(
        go.Scatter(
            x=[idx[marker_i]],
            y=[close[marker_i]],
            mode="markers+text",
            marker=dict(symbol="triangle-up", color=color, size=12, line=dict(color=TV["bg"], width=1)),
            text=["Entry"],
            textposition="top center",
            textfont=dict(color=TV["text"], size=10),
            hovertemplate=f"{strategy}<br>{note}<extra></extra>",
            showlegend=False,
        ),
        row=1 if is_rsi_divergence else None,
        col=1 if is_rsi_divergence else None,
    )
    fig.add_annotation(
        x=idx[1],
        y=max(highs),
        xanchor="left",
        yanchor="top",
        text=note,
        showarrow=False,
        font=dict(color=TV["text_muted"], size=10),
        bgcolor="rgba(19,23,34,0.75)",
        bordercolor=TV["border"],
        borderwidth=1,
    )
    fig.update_layout(
        height=210,
        margin=dict(l=4, r=20, t=8, b=4),
        paper_bgcolor=TV["bg"],
        plot_bgcolor=TV["panel"],
        font=dict(color=TV["text"], size=10),
        showlegend=False,
        hovermode="x",
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(showgrid=True, gridcolor=TV["grid"], showticklabels=False, fixedrange=True)
    fig.update_yaxes(showgrid=True, gridcolor=TV["grid"], side="right", fixedrange=True, tickfont=dict(color=TV["text_muted"], size=9))
    if is_rsi_divergence:
        fig.update_yaxes(range=[15, 75], row=2, col=1)
    return fig


def _inject_chart_resize_css() -> None:
    """CSS resize panel chart (native Streamlit plotly)."""
    if st.session_state.get("_chart_resize_css"):
        return
    st.session_state._chart_resize_css = True
    st.markdown(
        """
<style>
/* Panel chart — kéo góc phải-dưới để đổi cao/rộng */
[data-testid="stPlotlyChart"] {
    resize: both;
    overflow: hidden;
    min-height: 320px;
    min-width: 280px;
    max-height: 92vh;
    height: 560px;
    border: 1px solid #434651;
    border-radius: 4px;
    position: relative;
}
[data-testid="stPlotlyChart"]::after {
    content: "";
    position: absolute;
    right: 3px;
    bottom: 3px;
    width: 14px;
    height: 14px;
    border-right: 2px solid #787b86;
    border-bottom: 2px solid #787b86;
    pointer-events: none;
    z-index: 10;
}
[data-testid="stPlotlyChart"] iframe {
    width: 100% !important;
    height: 100% !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def make_strategy_detail_chart(
    df: pd.DataFrame,
    strategy: str,
    trades: list,
    *,
    show_ema: bool | None = None,
    show_volume: bool = False,
    equity: float = 1000.0,
    max_bars: int = 2000,
    height: int | None = None,
    focus_trades: bool = True,
    focus_trade: Any | None = None,
    dragmode: str = "pan",
) -> go.Figure:
    """Biểu đồ riêng từng chiến lược — overlay minh họa theo logic CL."""
    profile = _chart_profile(strategy)
    color = strategy_color(strategy)

    work = _slice_df(df, max_bars)
    if focus_trade is not None:
        work = _focus_df_around_trades(work, [focus_trade], pad=120)
    elif focus_trades and trades:
        work = _focus_df_around_trades(work, trades)

    df_index = set(work.index)
    use_ema = profile.get("show_ema", False) if show_ema is None else show_ema
    use_rsi = profile.get("show_rsi", False)
    use_vol = (not use_rsi) and show_volume and _has_volume(work)

    row_heights = [0.68, 0.12, 0.20] if (use_rsi or use_vol) else [0.76, 0.24]
    rows = 3 if (use_rsi or use_vol) else 2
    indicator_row = 2 if (use_rsi or use_vol) else None
    equity_row = 3 if (use_rsi or use_vol) else 2

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
    )

    _add_candles(fig, work, row=1)
    if use_ema:
        _add_emas(fig, work, row=1)
    if profile.get("show_sl_tp", True):
        _add_sl_tp_levels(fig, trades, work, df_index, row=1)
    if profile.get("highlight_entry_bar", False) and trades:
        _highlight_entry_bars(fig, work, trades, color, row=1)

    if use_rsi and indicator_row:
        _add_rsi_panel(fig, work, indicator_row)
    elif use_vol and indicator_row:
        _add_volume(fig, work, indicator_row)

    _add_strategy_trades(fig, trades, strategy, color, df_index, row=1)
    _add_equity(fig, trades, equity, row=equity_row)
    _apply_tv_layout(fig, strategy, rows, equity_row, height=height or 560, dragmode=dragmode)
    return fig


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
    height: int = 650,
    dragmode: str = "pan",
    focus_trade: Any | None = None,
) -> go.Figure:
    """Candlestick TradingView-style + multi-strategy markers."""
    df = _slice_df(df, max_bars)
    if focus_trade is not None:
        df = _focus_df_around_trades(df, [focus_trade], pad=120)
    df_index = set(df.index)

    if strategy_trades is None:
        strategy_trades = {strategy_name or "Strategy": trades or []}

    use_vol = show_volume and _has_volume(df)
    row_heights = [0.68, 0.12, 0.20] if use_vol else [0.76, 0.24]
    rows = 3 if use_vol else 2
    equity_row = 3 if use_vol else 2

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
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
    _apply_tv_layout(fig, title, rows, equity_row, height=height, dragmode=dragmode)
    return fig


def strategy_legend_html(active: list[str] | None = None) -> str:
    """Legend HTML ngoài chart — tránh che nến."""
    names = active or STRATEGY_ORDER
    parts = []
    for sname in names:
        c = strategy_color(sname)
        parts.append(
            f"<span style='color:{c};font-size:14px'>●</span> "
            f"<span style='color:{TV['text']};font-size:12px'>{sname}</span>"
        )
    parts.append("<span style='color:#787b86;font-size:11px'>▲ Long · ▼ Short · ○ Exit</span>")
    return "&nbsp;&nbsp;".join(parts)


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
