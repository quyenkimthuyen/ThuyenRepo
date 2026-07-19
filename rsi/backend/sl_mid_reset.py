"""Quy tắc lọc lệnh sau SL — reset vùng 50, skip 1, hoặc 2 SL → chờ vùng đối diện."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

from .zone_stats import DEFAULT_BANDS, in_band

MID_BAND = DEFAULT_BANDS["mid"]
LOW_BAND = DEFAULT_BANDS["low"]
HIGH_BAND = DEFAULT_BANDS["high"]
SlResetMode = Literal["none", "mid_zone", "skip_one", "two_sl_opposite"]


def _bar_index(df: pd.DataFrame, unix_sec: int) -> int | None:
    ts = pd.Timestamp(unix_sec, unit="s", tz="UTC")
    loc = df.index.get_indexer([ts], method="nearest")[0]
    return int(loc) if loc >= 0 else None


def opposite_band_for_zone(zone: Literal["low", "high"]) -> tuple[float, float]:
    return HIGH_BAND if zone == "low" else LOW_BAND


def rsi_visited_band_between(
    df: pd.DataFrame,
    start_i: int,
    end_i: int,
    band: tuple[float, float],
) -> bool:
    """RSI H4 đã vào band trong khoảng (start_i, end_i]."""
    if end_i <= start_i:
        return False
    for j in range(start_i + 1, min(len(df), end_i + 1)):
        rsi = float(df.iloc[j].get("rsi14_h4", np.nan))
        if not np.isnan(rsi) and in_band(rsi, band):
            return True
    return False


def rsi_visited_mid_between(df: pd.DataFrame, start_i: int, end_i: int, band: tuple[float, float] = MID_BAND) -> bool:
    return rsi_visited_band_between(df, start_i, end_i, band)


def filter_entries_sequential(
    df: pd.DataFrame,
    candidates: list[dict[str, Any]],
    *,
    sl_reset_mode: SlResetMode = "none",
    one_trade_at_a_time: bool = True,
    trade_zone: Literal["low", "high"] = "low",
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Lọc tín hiệu theo thời gian.
    - one_trade_at_a_time: không chồng lệnh
    - sl_reset_mode mid_zone: sau SL, chờ RSI về 48–52
    - sl_reset_mode skip_one: sau SL, bỏ qua đúng 1 tín hiệu tiếp theo
    - sl_reset_mode two_sl_opposite: sau 2 SL liên tiếp, chờ RSI về vùng đối diện
    """
    stats = {
        "skipped_overlap": 0,
        "skipped_sl_reset": 0,
        "skipped_sl_skip_one": 0,
        "skipped_sl_two_opposite": 0,
        "sl_losses": 0,
        "sl_two_opposite_triggers": 0,
    }
    if not candidates:
        return [], stats

    opposite_band = opposite_band_for_zone(trade_zone)
    ordered = sorted(candidates, key=lambda c: (c["entry_i"], c.get("touch_time", 0)))
    taken: list[dict[str, Any]] = []
    busy_until = 0
    sl_block_after_i: int | None = None
    skip_next_after_sl = False
    consecutive_sl = 0

    for cand in ordered:
        entry_i = cand["entry_i"]
        entry_time = cand["entry_time"]

        if one_trade_at_a_time and entry_time < busy_until:
            stats["skipped_overlap"] += 1
            continue

        if sl_reset_mode == "skip_one" and skip_next_after_sl:
            stats["skipped_sl_skip_one"] += 1
            skip_next_after_sl = False
            continue

        if sl_reset_mode == "mid_zone" and sl_block_after_i is not None:
            if not rsi_visited_mid_between(df, sl_block_after_i, entry_i):
                stats["skipped_sl_reset"] += 1
                continue
            sl_block_after_i = None

        if sl_reset_mode == "two_sl_opposite" and sl_block_after_i is not None:
            if not rsi_visited_band_between(df, sl_block_after_i, entry_i, opposite_band):
                stats["skipped_sl_two_opposite"] += 1
                continue
            sl_block_after_i = None
            consecutive_sl = 0

        sim = cand["sim"]
        taken.append(cand)
        busy_until = sim["exit_time"]

        if sim.get("exit_reason") == "sl":
            stats["sl_losses"] += 1
            consecutive_sl += 1
            exit_i = _bar_index(df, sim["exit_time"])
            if sl_reset_mode == "mid_zone" and exit_i is not None:
                sl_block_after_i = exit_i
            elif sl_reset_mode == "skip_one":
                skip_next_after_sl = True
            elif sl_reset_mode == "two_sl_opposite" and consecutive_sl >= 2 and exit_i is not None:
                sl_block_after_i = exit_i
                consecutive_sl = 0
                stats["sl_two_opposite_triggers"] += 1
        else:
            consecutive_sl = 0

    return taken, stats
