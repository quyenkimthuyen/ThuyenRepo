from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.strategy.rsi_ema_v1.config import band, in_band, load_strategy_config
from backend.strategy.rsi_ema_v1.states import Direction, SetupId


def ema_h1_supports_long(row: pd.Series, *, tol_atr: float) -> bool:
    close = float(row["close"])
    ema50 = float(row.get("ema50", close))
    ema200 = float(row.get("ema200", close))
    atr_val = float(row.get("atr14", 0))
    if np.isnan(atr_val) or atr_val <= 0:
        return True
    tol = atr_val * tol_atr
    return close >= ema50 - tol or close >= ema200 - tol


def ema_h1_resists_short(row: pd.Series, *, tol_atr: float) -> bool:
    close = float(row["close"])
    ema50 = float(row.get("ema50", close))
    ema200 = float(row.get("ema200", close))
    atr_val = float(row.get("atr14", 0))
    if np.isnan(atr_val) or atr_val <= 0:
        return True
    tol = atr_val * tol_atr
    return close <= ema50 + tol or close <= ema200 + tol


def _rsi_bounce_up(rsi: float, prev: float, min_delta: float) -> bool:
    return rsi >= prev - 0.05 and rsi > prev - min_delta


def _rsi_bounce_down(rsi: float, prev: float, min_delta: float) -> bool:
    return rsi <= prev + 0.05 and rsi < prev + min_delta


def _count_mid_touches(rsi_arr: np.ndarray, start: int, end: int, mid: tuple[float, float]) -> int:
    touches = 0
    in_mid = False
    for j in range(start, end + 1):
        val = rsi_arr[j]
        if np.isnan(val):
            continue
        inside = in_band(float(val), mid)
        if inside and not in_mid:
            touches += 1
        in_mid = inside
    return touches


def setup1_long(rsi_arr: np.ndarray, i: int, mid: tuple[float, float], lookback: int, bounce_min: float) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi < lo or not _rsi_bounce_up(rsi, prev, bounce_min):
        return False
    start = max(1, i - lookback)
    broke_up = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) > hi for j in range(start, i))
    if not broke_up:
        return False
    return not any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) < lo for j in range(start, i + 1))


def setup1_short(rsi_arr: np.ndarray, i: int, mid: tuple[float, float], lookback: int, bounce_min: float) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi > hi or not _rsi_bounce_down(rsi, prev, bounce_min):
        return False
    start = max(1, i - lookback)
    broke_down = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) < lo for j in range(start, i))
    if not broke_down:
        return False
    return not any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) > hi for j in range(start, i + 1))


def setup2_long(
    rsi_arr: np.ndarray,
    i: int,
    mid: tuple[float, float],
    high: tuple[float, float],
    lookback: int,
    max_touches: int,
    bounce_min: float,
) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi < lo or not _rsi_bounce_up(rsi, prev, bounce_min):
        return False
    start = max(1, i - lookback)
    touched_high = any(not np.isnan(rsi_arr[j]) and in_band(float(rsi_arr[j]), high) for j in range(start, i))
    if not touched_high:
        return False
    was_above = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) > hi for j in range(start, i))
    if not was_above:
        return False
    touches = _count_mid_touches(rsi_arr, start, i, mid)
    return 1 <= touches <= max_touches


def setup2_short(
    rsi_arr: np.ndarray,
    i: int,
    mid: tuple[float, float],
    low: tuple[float, float],
    lookback: int,
    max_touches: int,
    bounce_min: float,
) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi > hi or not _rsi_bounce_down(rsi, prev, bounce_min):
        return False
    start = max(1, i - lookback)
    touched_low = any(not np.isnan(rsi_arr[j]) and in_band(float(rsi_arr[j]), low) for j in range(start, i))
    if not touched_low:
        return False
    was_below = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) < lo for j in range(start, i))
    if not was_below:
        return False
    touches = _count_mid_touches(rsi_arr, start, i, mid)
    return 1 <= touches <= max_touches


def detect_at_bar(df: pd.DataFrame, i: int, cfg: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if i < 2:
        return None
    cfg = load_strategy_config(cfg)
    lookback = int(cfg.get("lookback_bars", 120))
    tol = float(cfg.get("ema_tolerance_atr", 0.35))
    bounce_min = float(cfg.get("rsi_bounce_min", 0.1))
    setups_cfg = cfg.get("setups") or {}
    max_touches = int((setups_cfg.get("s2_extreme_bounce") or {}).get("max_mid_touches", 2))

    rsi_arr = df["rsi14_h4"].to_numpy(dtype=float)
    rsi = float(rsi_arr[i])
    if np.isnan(rsi):
        return None

    row = df.iloc[i]
    mid = band(cfg, "mid")
    high = band(cfg, "high")
    low = band(cfg, "low")

    candidates: list[dict[str, Any]] = []

    if (setups_cfg.get("s2_extreme_bounce") or {}).get("enabled", True):
        if setup2_long(rsi_arr, i, mid, high, lookback, max_touches, bounce_min) and ema_h1_supports_long(row, tol_atr=tol):
            candidates.append(
                {
                    "setup_id": SetupId.S2_EXTREME_BOUNCE.value,
                    "direction": Direction.LONG.value,
                    "rsi14_h4": round(rsi, 2),
                }
            )
        if setup2_short(rsi_arr, i, mid, low, lookback, max_touches, bounce_min) and ema_h1_resists_short(row, tol_atr=tol):
            candidates.append(
                {
                    "setup_id": SetupId.S2_EXTREME_BOUNCE.value,
                    "direction": Direction.SHORT.value,
                    "rsi14_h4": round(rsi, 2),
                }
            )

    if (setups_cfg.get("s1_break_retest") or {}).get("enabled", True):
        if setup1_long(rsi_arr, i, mid, lookback, bounce_min) and ema_h1_supports_long(row, tol_atr=tol):
            candidates.append(
                {
                    "setup_id": SetupId.S1_BREAK_RETEST.value,
                    "direction": Direction.LONG.value,
                    "rsi14_h4": round(rsi, 2),
                }
            )
        if setup1_short(rsi_arr, i, mid, lookback, bounce_min) and ema_h1_resists_short(row, tol_atr=tol):
            candidates.append(
                {
                    "setup_id": SetupId.S1_BREAK_RETEST.value,
                    "direction": Direction.SHORT.value,
                    "rsi14_h4": round(rsi, 2),
                }
            )

    if not candidates:
        return None

    # Setup 2 ưu tiên hơn setup 1 khi cả hai khớp (xu hướng đã có)
    candidates.sort(key=lambda c: 0 if c["setup_id"] == SetupId.S2_EXTREME_BOUNCE.value else 1)
    signal = candidates[0]
    return {
        **signal,
        "bar_index": i,
        "entry_time": df.index[i].isoformat(),
        "state_snapshot": {
            "setup_id": signal["setup_id"],
            "direction": signal["direction"],
            "rsi14_h4": signal["rsi14_h4"],
            "ema_ok": True,
            "lookback_bars": lookback,
        },
    }


def classify_for_direction(
    df: pd.DataFrame,
    i: int,
    direction: str,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    hit = detect_at_bar(df, i, cfg)
    if hit and hit["direction"] == direction:
        return hit
    return None
