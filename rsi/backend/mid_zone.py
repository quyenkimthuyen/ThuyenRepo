"""RSI mid-zone (48–52) — continuation vs reversal in trend."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .zone_stats import ZoneConfig, _bar_timestamp, _measure_reversal, _zone_touch_events


def _find_mid_exit(df: pd.DataFrame, touch_i: int, band: tuple[float, float], max_bars: int) -> dict[str, int] | None:
    rsi = df["rsi14_h4"].to_numpy(dtype=float)
    lo, hi = band
    end = min(len(rsi) - 1, touch_i + max_bars)
    for j in range(touch_i + 1, end + 1):
        if np.isnan(rsi[j]) or np.isnan(rsi[j - 1]):
            continue
        cur, prev = float(rsi[j]), float(rsi[j - 1])
        was_in = any(lo <= float(rsi[k]) <= hi for k in range(touch_i, j) if not np.isnan(rsi[k]))
        if not was_in:
            continue
        if (prev <= hi and cur > hi) or (prev >= lo and cur < lo):
            return {"exit_i": j, "bars_to_exit": j - touch_i}
    return None


def analyze_mid_zone(df: pd.DataFrame, cfg: ZoneConfig | None = None) -> dict[str, Any]:
    cfg = cfg or ZoneConfig()
    band = cfg.mid
    indices = _zone_touch_events(df, "mid", band, cfg.cooldown_bars)
    events: list[dict[str, Any]] = []

    for i in indices:
        row = df.iloc[i]
        trend_up = bool(row.get("trend_up", False))
        h4_up = bool(row.get("h4_trend_up", False))
        trend_dir = "up" if h4_up else "down"

        # Continuation = price moves with H4 trend; reversal = against H4 trend
        cont_dir = "bullish" if h4_up else "bearish"
        rev_dir = "bearish" if h4_up else "bullish"

        cont = _measure_reversal(df, i, cont_dir, cfg.horizon_bars, cfg.min_reversal_pips)
        rev = _measure_reversal(df, i, rev_dir, cfg.horizon_bars, cfg.min_reversal_pips)

        exit_info = _find_mid_exit(df, i, band, cfg.exit_lookahead_bars)
        exit_cont = {"reversed": False, "move_pips": 0.0}
        exit_rev = {"reversed": False, "move_pips": 0.0}
        if exit_info:
            exit_cont = _measure_reversal(df, exit_info["exit_i"], cont_dir, cfg.horizon_bars, cfg.min_reversal_pips)
            exit_rev = _measure_reversal(df, exit_info["exit_i"], rev_dir, cfg.horizon_bars, cfg.min_reversal_pips)

        events.append({
            "time": _bar_timestamp(df, i),
            "rsi": round(float(row["rsi14_h4"]), 1),
            "close": float(row["close"]),
            "h4_trend_up": h4_up,
            "trend_dir": trend_dir,
            "continuation": cont["reversed"],
            "continuation_pips": cont.get("move_pips", 0),
            "reversal": rev["reversed"],
            "reversal_pips": rev.get("move_pips", 0),
            "exit_signal": exit_info is not None,
            "exit_continuation": exit_cont["reversed"] if exit_info else False,
            "exit_reversal": exit_rev["reversed"] if exit_info else False,
        })

    up_events = [e for e in events if e["h4_trend_up"]]
    down_events = [e for e in events if not e["h4_trend_up"]]

    def rate(subset: list[dict[str, Any]], key: str) -> float:
        if not subset:
            return 0.0
        return round(sum(1 for e in subset if e[key]) / len(subset) * 100, 1)

    return {
        "band": list(band),
        "touches": len(events),
        "summary": {
            "continuation_rate": rate(events, "continuation"),
            "reversal_rate": rate(events, "reversal"),
            "exit_continuation_rate": rate([e for e in events if e["exit_signal"]], "exit_continuation"),
            "exit_reversal_rate": rate([e for e in events if e["exit_signal"]], "exit_reversal"),
        },
        "by_trend": {
            "h4_up": {
                "samples": len(up_events),
                "continuation_rate": rate(up_events, "continuation"),
                "reversal_rate": rate(up_events, "reversal"),
                "note": "Pullback vùng 50 trong uptrend — kỳ vọng tiếp diễn tăng",
            },
            "h4_down": {
                "samples": len(down_events),
                "continuation_rate": rate(down_events, "continuation"),
                "reversal_rate": rate(down_events, "reversal"),
                "note": "Pullback vùng 50 trong downtrend — kỳ vọng tiếp diễn giảm",
            },
        },
        "events": events,
    }
