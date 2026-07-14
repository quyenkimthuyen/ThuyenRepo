"""Detect RSI H4 divergences and measure reversal outcomes."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd


def _bar_timestamp(ts: pd.Timestamp) -> int:
    return int(ts.timestamp())


def _pip_move(price_delta: float) -> float:
    return abs(price_delta) * 10_000


def _h4_points(df: pd.DataFrame) -> pd.DataFrame:
    work = df[["high", "low", "close", "rsi14_h4"]].copy()
    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC")
    return work.resample("4h", label="right", closed="right").agg(
        {"high": "max", "low": "min", "close": "last", "rsi14_h4": "last"}
    ).dropna(subset=["close", "rsi14_h4"])


def _pivot_indices(h4: pd.DataFrame, column: str, mode: Literal["low", "high"], span: int) -> list[int]:
    values = h4[column].to_numpy(dtype=float)
    out: list[int] = []
    for i in range(span, len(values) - span):
        window = values[i - span : i + span + 1]
        center = values[i]
        if mode == "low" and center == np.min(window) and np.count_nonzero(window == center) == 1:
            out.append(i)
        elif mode == "high" and center == np.max(window) and np.count_nonzero(window == center) == 1:
            out.append(i)
    return out


def _entry_index(df: pd.DataFrame, ts: pd.Timestamp) -> int | None:
    loc = df.index.get_indexer([ts], method="nearest")[0]
    return int(loc) if loc >= 0 else None


def _measure_reversal(
    df: pd.DataFrame,
    ts: pd.Timestamp,
    direction: Literal["bullish", "bearish"],
    horizon_bars: int,
    min_reversal_pips: float,
) -> dict[str, Any]:
    entry_i = _entry_index(df, ts)
    if entry_i is None or entry_i >= len(df) - 1:
        return {"reversed": False, "move_pips": 0.0, "bars_to_extreme": None}

    close = float(df.iloc[entry_i]["close"])
    fwd = df.iloc[entry_i + 1 : entry_i + 1 + horizon_bars]
    if fwd.empty:
        return {"reversed": False, "move_pips": 0.0, "bars_to_extreme": None}

    if direction == "bullish":
        move = float(fwd["high"].max()) - close
        adverse = close - float(fwd["low"].min())
        bars = int(fwd["high"].values.argmax()) + 1
    else:
        move = close - float(fwd["low"].min())
        adverse = float(fwd["high"].max()) - close
        bars = int(fwd["low"].values.argmin()) + 1

    move_pips = _pip_move(move)
    return {
        "reversed": bool(move_pips >= min_reversal_pips and move > adverse),
        "move_pips": round(move_pips, 1),
        "adverse_pips": round(_pip_move(adverse), 1),
        "bars_to_extreme": bars,
    }


def find_rsi_divergences(
    df: pd.DataFrame,
    *,
    pivot_span: int = 2,
    min_pivot_gap: int = 3,
    max_pivot_gap: int = 80,
    min_rsi_delta: float = 1.0,
    min_price_delta_pips: float = 8.0,
    horizon_bars: int = 48,
    min_reversal_pips: float = 20.0,
) -> list[dict[str, Any]]:
    """Classic divergence: price makes a new extreme while RSI weakens."""
    h4 = _h4_points(df)
    if len(h4) < pivot_span * 2 + 3:
        return []

    divergences: list[dict[str, Any]] = []

    lows = _pivot_indices(h4, "low", "low", pivot_span)
    for a, b in zip(lows, lows[1:]):
        if b - a < min_pivot_gap or b - a > max_pivot_gap:
            continue
        first = h4.iloc[a]
        second = h4.iloc[b]
        price_delta_pips = (float(first["low"]) - float(second["low"])) * 10_000
        rsi_delta = float(second["rsi14_h4"]) - float(first["rsi14_h4"])
        if price_delta_pips >= min_price_delta_pips and rsi_delta >= min_rsi_delta:
            measure = _measure_reversal(df, h4.index[b], "bullish", horizon_bars, min_reversal_pips)
            divergences.append({
                "type": "bullish",
                "direction": "bullish",
                "start_time": _bar_timestamp(h4.index[a]),
                "end_time": _bar_timestamp(h4.index[b]),
                "price_start": round(float(first["low"]), 5),
                "price_end": round(float(second["low"]), 5),
                "rsi_start": round(float(first["rsi14_h4"]), 2),
                "rsi_end": round(float(second["rsi14_h4"]), 2),
                "price_delta_pips": round(price_delta_pips, 1),
                "rsi_delta": round(rsi_delta, 2),
                **measure,
            })

    highs = _pivot_indices(h4, "high", "high", pivot_span)
    for a, b in zip(highs, highs[1:]):
        if b - a < min_pivot_gap or b - a > max_pivot_gap:
            continue
        first = h4.iloc[a]
        second = h4.iloc[b]
        price_delta_pips = (float(second["high"]) - float(first["high"])) * 10_000
        rsi_delta = float(first["rsi14_h4"]) - float(second["rsi14_h4"])
        if price_delta_pips >= min_price_delta_pips and rsi_delta >= min_rsi_delta:
            measure = _measure_reversal(df, h4.index[b], "bearish", horizon_bars, min_reversal_pips)
            divergences.append({
                "type": "bearish",
                "direction": "bearish",
                "start_time": _bar_timestamp(h4.index[a]),
                "end_time": _bar_timestamp(h4.index[b]),
                "price_start": round(float(first["high"]), 5),
                "price_end": round(float(second["high"]), 5),
                "rsi_start": round(float(first["rsi14_h4"]), 2),
                "rsi_end": round(float(second["rsi14_h4"]), 2),
                "price_delta_pips": round(price_delta_pips, 1),
                "rsi_delta": round(rsi_delta, 2),
                **measure,
            })

    return sorted(divergences, key=lambda d: d["end_time"])


def summarize_divergences(divergences: list[dict[str, Any]]) -> dict[str, Any]:
    def row(kind: str | None = None) -> dict[str, Any]:
        subset = [d for d in divergences if kind is None or d["type"] == kind]
        reversed_n = sum(1 for d in subset if d["reversed"])
        bars = [d["bars_to_extreme"] for d in subset if d["bars_to_extreme"] is not None]
        return {
            "count": len(subset),
            "reversals": reversed_n,
            "reversal_rate": round(reversed_n / len(subset) * 100, 1) if subset else 0.0,
            "avg_move_pips": round(float(np.mean([d["move_pips"] for d in subset])) if subset else 0.0, 1),
            "avg_adverse_pips": round(float(np.mean([d["adverse_pips"] for d in subset])) if subset else 0.0, 1),
            "avg_bars_to_extreme": round(float(np.mean(bars)) if bars else 0.0, 1),
        }

    return {
        "overall": row(),
        "bullish": row("bullish"),
        "bearish": row("bearish"),
    }
