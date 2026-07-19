"""Improved RSI zone entry resolution — delay, candle confirm, divergence."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

EntryStrategy = Literal[
    "touch",
    "delay_1",
    "delay_2",
    "delay_3",
    "delay_5",
    "confirm_candle",
    "confirm_delay1",
    "touch_div",
    "touch_h4",
    "touch_confirm",
    "ema_touch_2",
    "ema_touch_3",
    "ema_reject_2",
    "ema_reject_3",
    "ema_reject_3_pb10",
]

EntryFilter = Literal["bullish", "rsi_rising", "deep_touch", "above_ema50", "rsi_turning", "min_ema_sep"]

MIN_EMA_SEP_PIPS = 15.0

DEFAULT_MAX_WAIT = 6
EMA_TOUCH_MAX_WAIT = 96
DIV_LOOKAHEAD_SEC = 48 * 3600  # 48 H1 bars
EMA_TOUCH_TOLERANCE_PIPS = 2.0
EMA_TOUCH_PULLBACK_PIPS = 8.0
EMA_ENTRY_PULLBACK_PIPS = 10.0
EMA_PULLBACK_WAIT_BARS = 24
EMA_TOUCH_MIN_GAP_BARS = 2
EMA_COLS = ("ema50", "ema200", "ema800")


def _body(row: pd.Series) -> float:
    return abs(float(row["close"]) - float(row["open"]))


def _range(row: pd.Series) -> float:
    return float(row["high"]) - float(row["low"])


def is_bullish_engulfing(df: pd.DataFrame, i: int) -> bool:
    if i < 1:
        return False
    cur, prev = df.iloc[i], df.iloc[i - 1]
    if float(cur["close"]) <= float(cur["open"]):
        return False
    if float(prev["close"]) >= float(prev["open"]):
        return False
    return float(cur["close"]) >= float(prev["open"]) and float(cur["open"]) <= float(prev["close"])


def is_bearish_engulfing(df: pd.DataFrame, i: int) -> bool:
    if i < 1:
        return False
    cur, prev = df.iloc[i], df.iloc[i - 1]
    if float(cur["close"]) >= float(cur["open"]):
        return False
    if float(prev["close"]) <= float(prev["open"]):
        return False
    return float(cur["open"]) >= float(prev["close"]) and float(cur["close"]) <= float(prev["open"])


def is_hammer(df: pd.DataFrame, i: int) -> bool:
    row = df.iloc[i]
    rng = _range(row)
    if rng <= 0:
        return False
    body = _body(row)
    lower_wick = min(float(row["open"]), float(row["close"])) - float(row["low"])
    upper_wick = float(row["high"]) - max(float(row["open"]), float(row["close"]))
    return (
        float(row["close"]) > float(row["open"])
        and lower_wick >= body * 1.5
        and upper_wick <= body * 0.6
        and body / rng <= 0.45
    )


def is_shooting_star(df: pd.DataFrame, i: int) -> bool:
    row = df.iloc[i]
    rng = _range(row)
    if rng <= 0:
        return False
    body = _body(row)
    upper_wick = float(row["high"]) - max(float(row["open"]), float(row["close"]))
    lower_wick = min(float(row["open"]), float(row["close"])) - float(row["low"])
    return (
        float(row["close"]) < float(row["open"])
        and upper_wick >= body * 1.5
        and lower_wick <= body * 0.6
        and body / rng <= 0.45
    )


def _bullish_pattern(df: pd.DataFrame, i: int) -> bool:
    return is_bullish_engulfing(df, i) or is_hammer(df, i)


def _bearish_pattern(df: pd.DataFrame, i: int) -> bool:
    return is_bearish_engulfing(df, i) or is_shooting_star(df, i)


def _has_bullish_div_near(touch_time: int, divergences: list[dict[str, Any]] | None) -> bool:
    if not divergences:
        return False
    for d in divergences:
        if d.get("type") != "bullish":
            continue
        end = int(d.get("end_time", 0))
        if abs(end - touch_time) <= DIV_LOOKAHEAD_SEC:
            return True
    return False


def _ema_value(row: pd.Series, col: str) -> float | None:
    v = row.get(col)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return float(v)


def _resistance_emas(row: pd.Series) -> list[tuple[str, float]]:
    """EMAs above price — kháng cự khi long."""
    close = float(row["close"])
    out: list[tuple[str, float]] = []
    for col in EMA_COLS:
        v = _ema_value(row, col)
        if v is not None and v > close:
            out.append((col, v))
    return sorted(out, key=lambda x: x[1])


def _support_emas(row: pd.Series) -> list[tuple[str, float]]:
    """EMAs below price — hỗ trợ khi short."""
    close = float(row["close"])
    out: list[tuple[str, float]] = []
    for col in EMA_COLS:
        v = _ema_value(row, col)
        if v is not None and v < close:
            out.append((col, v))
    return sorted(out, key=lambda x: x[1], reverse=True)


def _is_ema_rejection(row: pd.Series, zone: Literal["low", "high"], tolerance_pips: float) -> tuple[bool, float | None]:
    """Chạm EMA và bị từ chối (đóng cửa phía bên kia EMA)."""
    tol = tolerance_pips / 10_000
    if zone == "low":
        emas = _resistance_emas(row)
        if not emas:
            return False, None
        level = min(v for _, v in emas)
        touched = float(row["high"]) >= level - tol
        rejected = float(row["close"]) < level
        return touched and rejected, level
    emas = _support_emas(row)
    if not emas:
        return False, None
    level = max(v for _, v in emas)
    touched = float(row["low"]) <= level + tol
    rejected = float(row["close"]) > level
    return touched and rejected, level


def _is_ema_resistance_touch(row: pd.Series, zone: Literal["low", "high"], tolerance_pips: float) -> bool:
    """Giá H1 phản ứng kháng cự/hỗ trợ tại EMA."""
    tol = tolerance_pips / 10_000
    high = float(row["high"])
    low = float(row["low"])
    if zone == "low":
        emas = _resistance_emas(row)
        if not emas:
            return False
        target = min(v for _, v in emas)
        return high >= target - tol
    emas = _support_emas(row)
    if not emas:
        return False
    target = max(v for _, v in emas)
    return low <= target + tol


def _touch_pullback_ok(
    df: pd.DataFrame,
    prev_i: int,
    cur_i: int,
    zone: Literal["low", "high"],
    pullback_pips: float,
) -> bool:
    """Giá đã rời xa EMA giữa hai lần chạm."""
    if cur_i <= prev_i + EMA_TOUCH_MIN_GAP_BARS:
        return False
    pb = pullback_pips / 10_000
    window = df.iloc[prev_i + 1 : cur_i]
    if window.empty:
        return False
    row_prev = df.iloc[prev_i]
    if zone == "low":
        emas = _resistance_emas(row_prev)
        if not emas:
            return True
        level = min(v for _, v in emas)
        return float(window["low"].min()) <= level - pb
    emas = _support_emas(row_prev)
    if not emas:
        return True
    level = max(v for _, v in emas)
    return float(window["high"].max()) >= level + pb


def find_ema_touch_entry(
    df: pd.DataFrame,
    touch_i: int,
    zone: Literal["low", "high"],
    target_touch: int,
    *,
    max_wait_bars: int = EMA_TOUCH_MAX_WAIT,
    tolerance_pips: float = EMA_TOUCH_TOLERANCE_PIPS,
    separation_pips: float = EMA_TOUCH_PULLBACK_PIPS,
    require_rejection: bool = False,
    entry_pullback_pips: float | None = None,
) -> int | None:
    """
    Sau RSI chạm vùng: đếm lần giá H1 phản ứng EMA (lần 1 bỏ qua).
    - require_rejection: phải bị từ chối tại EMA (nến đóng dưới/trên EMA).
    - entry_pullback_pips: sau lần chạm thứ N, chờ giá hồi lại rồi mới vào.
    """
    if touch_i < 0 or touch_i >= len(df) - 1 or target_touch < 2:
        return None

    end = min(len(df) - 1, touch_i + max_wait_bars)
    touch_count = 0
    last_touch_i: int | None = None

    for j in range(touch_i + 1, end + 1):
        row = df.iloc[j]
        if require_rejection:
            ok, level = _is_ema_rejection(row, zone, tolerance_pips)
            if not ok or level is None:
                continue
        elif not _is_ema_resistance_touch(row, zone, tolerance_pips):
            continue
        else:
            emas = _resistance_emas(row) if zone == "low" else _support_emas(row)
            level = min(v for _, v in emas) if zone == "low" else max(v for _, v in emas)

        if last_touch_i is not None and not _touch_pullback_ok(
            df, last_touch_i, j, zone, separation_pips
        ):
            continue
        touch_count += 1
        last_touch_i = j
        if touch_count == target_touch:
            if entry_pullback_pips is not None:
                pb = entry_pullback_pips / 10_000
                wait_end = min(len(df) - 1, j + EMA_PULLBACK_WAIT_BARS)
                for k in range(j + 1, wait_end + 1):
                    rk = df.iloc[k]
                    if zone == "low" and float(rk["low"]) <= level - pb:
                        return k
                    if zone == "high" and float(rk["high"]) >= level + pb:
                        return k
                return j + 1 if j + 1 < len(df) else None
            return j

    return None


def resolve_entry_index(
    df: pd.DataFrame,
    touch_i: int,
    zone: Literal["low", "high"],
    strategy: EntryStrategy,
    *,
    max_wait_bars: int = DEFAULT_MAX_WAIT,
    touch_time: int | None = None,
    divergences: list[dict[str, Any]] | None = None,
    h4_trend_up: bool | None = None,
) -> int | None:
    """Return H1 bar index to enter, or None if strategy not satisfied."""
    if touch_i < 0 or touch_i >= len(df) - 1:
        return None

    direction_up = zone == "low"

    if strategy == "touch":
        return touch_i

    if strategy == "delay_1":
        return touch_i + 1 if touch_i + 1 < len(df) else None

    if strategy == "delay_2":
        return touch_i + 2 if touch_i + 2 < len(df) else None

    if strategy == "delay_3":
        return touch_i + 3 if touch_i + 3 < len(df) else None

    if strategy == "delay_5":
        return touch_i + 5 if touch_i + 5 < len(df) else None

    if strategy == "touch_h4":
        if zone == "low" and not h4_trend_up:
            return None
        if zone == "high" and h4_trend_up:
            return None
        return touch_i

    if strategy == "touch_div":
        if touch_time is None:
            row = df.iloc[touch_i]
            touch_time = int(row.name.timestamp()) if hasattr(row.name, "timestamp") else None
        if zone == "low" and not _has_bullish_div_near(touch_time or 0, divergences):
            return None
        return touch_i

    end = min(len(df) - 1, touch_i + max_wait_bars)

    if strategy == "confirm_candle":
        for j in range(touch_i + 1, end + 1):
            ok = _bullish_pattern(df, j) if direction_up else _bearish_pattern(df, j)
            if ok:
                return j
        return None

    if strategy == "confirm_delay1":
        j = touch_i + 1
        if j >= len(df):
            return None
        ok = _bullish_pattern(df, j) if direction_up else _bearish_pattern(df, j)
        return j if ok else None

    if strategy == "touch_confirm":
        for j in range(touch_i + 1, end + 1):
            ok = _bullish_pattern(df, j) if direction_up else _bearish_pattern(df, j)
            if ok:
                return j
        return None

    if strategy == "ema_touch_2":
        return find_ema_touch_entry(df, touch_i, zone, 2, max_wait_bars=EMA_TOUCH_MAX_WAIT)

    if strategy == "ema_touch_3":
        return find_ema_touch_entry(df, touch_i, zone, 3, max_wait_bars=EMA_TOUCH_MAX_WAIT)

    if strategy == "ema_reject_2":
        return find_ema_touch_entry(
            df, touch_i, zone, 2, max_wait_bars=EMA_TOUCH_MAX_WAIT, require_rejection=True
        )

    if strategy == "ema_reject_3":
        return find_ema_touch_entry(
            df, touch_i, zone, 3, max_wait_bars=EMA_TOUCH_MAX_WAIT, require_rejection=True
        )

    if strategy == "ema_reject_3_pb10":
        return find_ema_touch_entry(
            df,
            touch_i,
            zone,
            3,
            max_wait_bars=EMA_TOUCH_MAX_WAIT,
            require_rejection=True,
            entry_pullback_pips=EMA_ENTRY_PULLBACK_PIPS,
        )

    return None


def swing_stop_pips(
    df: pd.DataFrame,
    entry_i: int,
    direction: Literal["long", "short"],
    lookback: int = 12,
    buffer_pips: float = 2.0,
    min_pips: float = 15.0,
    max_pips: float = 45.0,
) -> float:
    """SL distance from swing low/high before entry."""
    start = max(0, entry_i - lookback)
    window = df.iloc[start : entry_i + 1]
    entry = float(df.iloc[entry_i]["close"])
    buf = buffer_pips / 10_000

    if direction == "long":
        swing = float(window["low"].min()) - buf
        pips = (entry - swing) * 10_000
    else:
        swing = float(window["high"].max()) + buf
        pips = (swing - entry) * 10_000

    return float(np.clip(pips, min_pips, max_pips))


def check_entry_filters(
    df: pd.DataFrame,
    entry_i: int,
    touch_i: int,
    zone: Literal["low", "high"],
    filters: list[EntryFilter] | None,
) -> bool:
    """Điều kiện bổ sung tại nến vào lệnh."""
    if not filters:
        return True
    entry = df.iloc[entry_i]
    touch = df.iloc[touch_i]
    for f in filters:
        if f == "bullish":
            if float(entry["close"]) <= float(entry["open"]):
                return False
        elif f == "rsi_rising":
            t_rsi = float(touch.get("rsi14_h4", np.nan))
            e_rsi = float(entry.get("rsi14_h4", np.nan))
            if np.isnan(t_rsi) or np.isnan(e_rsi) or e_rsi <= t_rsi:
                return False
        elif f == "deep_touch" and zone == "low":
            if float(touch.get("rsi14_h4", 99)) > 30.0:
                return False
        elif f == "above_ema50" and zone == "low":
            ema50 = float(entry.get("ema50", np.nan))
            if np.isnan(ema50) or float(entry["close"]) < ema50:
                return False
        elif f == "rsi_turning" and zone == "low":
            if entry_i < 1:
                return False
            prev = df.iloc[entry_i - 1]
            e_rsi = float(entry.get("rsi14_h4", np.nan))
            p_rsi = float(prev.get("rsi14_h4", np.nan))
            if np.isnan(e_rsi) or np.isnan(p_rsi) or e_rsi <= p_rsi:
                return False
        elif f == "min_ema_sep":
            ema50 = float(entry.get("ema50", np.nan))
            ema200 = float(entry.get("ema200", np.nan))
            if np.isnan(ema50) or np.isnan(ema200):
                return False
            if abs(ema50 - ema200) * 10_000 < MIN_EMA_SEP_PIPS:
                return False
    return True
