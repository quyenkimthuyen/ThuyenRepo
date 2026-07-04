"""
Wyckoff failed break (Spring / Upthrust) on 1H entry, 4H trend filter.

v4: quan sát 4H — chỉ long khi 4H bullish, short khi 4H bearish.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr


@dataclass
class WyckoffConfig:
    consolidation_days: int = 2
    min_wick_range_ratio: float = 0.30
    min_wick_candle_ratio: float = 0.45
    max_range_atr_mult: float = 12.0
    max_range_pct: float = 0.016
    max_adx: float = 40.0
    min_range_touches: int = 2
    min_sweep_atr: float = 0.10
    max_sweep_range_ratio: float = 0.45
    rr: float = 2.0
    session_start: int = 7
    session_end: int = 18
    cooldown_bars: int = 6
    max_trades_per_day: int = 2
    close_reclaim_buffer: float = 0.15
    entry_delay_bars: int = 0
    use_htf_filter: bool = True
    htf_mode: str = "strict"  # off | soft | strict | stack | trend_adx
    min_htf_adx: float = 22.0
    require_range_compression: bool = False
    require_hammer_shape: bool = True
    sl_buffer_pips: float = 1.0
    pip_size: float = 0.0001

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> WyckoffConfig:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def preset(cls, name: str) -> WyckoffConfig:
        """quality = ít lệnh WR cao | high_wr = thêm lệnh giữ WR~50% | balanced = nhiều lệnh."""
        if name == "balanced":
            return cls(
                consolidation_days=2,
                min_wick_range_ratio=0.25,
                min_wick_candle_ratio=0.40,
                max_adx=45.0,
                min_range_touches=2,
                min_sweep_atr=0.08,
                max_sweep_range_ratio=0.50,
                close_reclaim_buffer=0.18,
                entry_delay_bars=1,
                cooldown_bars=3,
                max_trades_per_day=3,
                use_htf_filter=True,
                htf_mode="trend_adx",
                min_htf_adx=24.0,
                rr=2.0,
            )
        if name == "high_wr":
            return cls(
                consolidation_days=2,
                min_wick_range_ratio=0.25,
                max_adx=42.0,
                entry_delay_bars=1,
                cooldown_bars=3,
                use_htf_filter=True,
                htf_mode="stack",
                rr=2.0,
            )
        # quality — stack 4H, return OOS cao nhất
        return cls(
            consolidation_days=2,
            min_wick_range_ratio=0.25,
            max_adx=35.0,
            entry_delay_bars=1,
            use_htf_filter=True,
            htf_mode="stack",
            rr=2.0,
        )


@dataclass
class WyckoffSignal:
    signal_bar: int
    entry_bar: int
    direction: int
    sl_price: float
    range_high: float
    range_low: float
    range_size: float
    wick_ratio: float


def _consolidation_bars(cfg: WyckoffConfig) -> int:
    return cfg.consolidation_days * 24


def _count_touches(highs: np.ndarray, lows: np.ndarray, rh: float, rl: float, rng: float) -> int:
    if rng <= 0:
        return 0
    band = 0.15 * rng
    touch_hi = int(np.sum(highs >= rh - band))
    touch_lo = int(np.sum(lows <= rl + band))
    if touch_hi < 1 or touch_lo < 1:
        return 0
    return min(touch_hi, touch_lo)


def _is_sideways(adx_vals: np.ndarray, i: int, n: int, max_adx: float) -> bool:
    window = adx_vals[i - n : i]
    window = window[~np.isnan(window)]
    if len(window) < n // 2:
        return True
    return float(np.mean(window)) <= max_adx


def _range_compression(highs: np.ndarray, lows: np.ndarray, i: int, n: int) -> bool:
    mid = n // 2
    h1, l1 = highs[i - n : i - mid], lows[i - n : i - mid]
    h2, l2 = highs[i - mid : i], lows[i - mid : i]
    r1 = h1.max() - l1.min()
    r2 = h2.max() - l2.min()
    if r1 <= 0:
        return True
    return r2 <= r1 * 1.20


def _htf_allows(df: pd.DataFrame, i: int, direction: int, cfg: WyckoffConfig) -> bool:
    """Chỉ vào lệnh theo chiều xu hướng 4H (đã shift, không lookahead)."""
    if not cfg.use_htf_filter or cfg.htf_mode == "off":
        return True
    if "__htf_trend" not in df.columns:
        return True

    trend = df["__htf_trend"].iat[i]
    if np.isnan(trend):
        return False

    mode = cfg.htf_mode
    if mode == "soft":
        return trend >= 0 if direction == 1 else trend <= 0

    if mode == "strict":
        return trend >= 1 if direction == 1 else trend <= -1

    if mode == "stack":
        if direction == 1:
            return bool(df["__htf_bull_stack"].iat[i] >= 1) if "__htf_bull_stack" in df.columns else trend >= 1
        return bool(df["__htf_bear_stack"].iat[i] >= 1) if "__htf_bear_stack" in df.columns else trend <= -1

    if mode == "trend_adx":
        if direction == 1 and trend < 1:
            return False
        if direction == -1 and trend > -1:
            return False
        if "__htf_adx" in df.columns:
            adx_v = df["__htf_adx"].iat[i]
            if not np.isnan(adx_v) and adx_v < cfg.min_htf_adx:
                return False
        return True

    return trend >= 1 if direction == 1 else trend <= -1


def detect_wyckoff_signals(df: pd.DataFrame, cfg: WyckoffConfig | None = None) -> list[WyckoffSignal]:
    cfg = cfg or WyckoffConfig()
    n_bars = _consolidation_bars(cfg)
    if len(df) < n_bars + 5:
        return []

    highs = df["high"].values
    lows = df["low"].values
    opens = df["open"].values
    closes = df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values

    signals: list[WyckoffSignal] = []
    sl_buf = cfg.sl_buffer_pips * cfg.pip_size

    for i in range(n_bars, len(df) - cfg.entry_delay_bars):
        w_hi = highs[i - n_bars : i]
        w_lo = lows[i - n_bars : i]
        range_high = float(np.max(w_hi))
        range_low = float(np.min(w_lo))
        range_size = range_high - range_low
        if range_size <= 0:
            continue

        a = atr_vals[i]
        if np.isnan(a) or a <= 0:
            continue
        if range_size > cfg.max_range_atr_mult * a:
            continue
        if range_size / closes[i] > cfg.max_range_pct:
            continue
        if not _is_sideways(adx_vals, i, n_bars, cfg.max_adx):
            continue
        if _count_touches(w_hi, w_lo, range_high, range_low, range_size) < cfg.min_range_touches:
            continue
        if cfg.require_range_compression and not _range_compression(highs, lows, i, n_bars):
            continue

        body_bot = min(opens[i], closes[i])
        body_top = max(opens[i], closes[i])
        candle_rng = highs[i] - lows[i]
        if candle_rng <= 0:
            continue

        lower_wick = body_bot - lows[i]
        upper_wick = highs[i] - body_top
        sweep_down = range_low - lows[i]
        sweep_up = highs[i] - range_high

        reclaim_lo = range_low - cfg.close_reclaim_buffer * range_size
        reclaim_hi = range_high + cfg.close_reclaim_buffer * range_size

        spring_wick_ok = (
            lower_wick >= cfg.min_wick_range_ratio * range_size
            or lower_wick / candle_rng >= cfg.min_wick_candle_ratio
        )
        spring_sweep_ok = (
            lows[i] < range_low
            and sweep_down >= cfg.min_sweep_atr * a
            and sweep_down <= cfg.max_sweep_range_ratio * range_size
        )
        spring_close_ok = closes[i] >= reclaim_lo
        spring_shape_ok = not cfg.require_hammer_shape or lower_wick >= upper_wick

        if spring_wick_ok and spring_sweep_ok and spring_close_ok and spring_shape_ok and _htf_allows(df, i, 1, cfg):
            entry_bar = i + cfg.entry_delay_bars
            signals.append(WyckoffSignal(
                signal_bar=i,
                entry_bar=entry_bar,
                direction=1,
                sl_price=float(lows[i] - sl_buf),
                range_high=range_high,
                range_low=range_low,
                range_size=range_size,
                wick_ratio=float(lower_wick / range_size),
            ))
            continue

        up_wick_ok = (
            upper_wick >= cfg.min_wick_range_ratio * range_size
            or upper_wick / candle_rng >= cfg.min_wick_candle_ratio
        )
        up_sweep_ok = (
            highs[i] > range_high
            and sweep_up >= cfg.min_sweep_atr * a
            and sweep_up <= cfg.max_sweep_range_ratio * range_size
        )
        up_close_ok = closes[i] <= reclaim_hi
        up_shape_ok = not cfg.require_hammer_shape or upper_wick >= lower_wick

        if up_wick_ok and up_sweep_ok and up_close_ok and up_shape_ok and _htf_allows(df, i, -1, cfg):
            entry_bar = i + cfg.entry_delay_bars
            signals.append(WyckoffSignal(
                signal_bar=i,
                entry_bar=entry_bar,
                direction=-1,
                sl_price=float(highs[i] + sl_buf),
                range_high=range_high,
                range_low=range_low,
                range_size=range_size,
                wick_ratio=float(upper_wick / range_size),
            ))

    return _apply_session_cooldown(df, signals, cfg)


def _apply_session_cooldown(
    df: pd.DataFrame,
    signals: list[WyckoffSignal],
    cfg: WyckoffConfig,
) -> list[WyckoffSignal]:
    if not signals:
        return []

    hours = df.index.hour
    dates = df.index.date
    out: list[WyckoffSignal] = []
    last_entry = -cfg.cooldown_bars - 1
    trades_today: dict = {}

    for sig in sorted(signals, key=lambda s: s.entry_bar):
        i = sig.entry_bar
        if i >= len(df):
            continue
        if hours[i] < cfg.session_start or hours[i] >= cfg.session_end:
            continue
        day = dates[i]
        if trades_today.get(day, 0) >= cfg.max_trades_per_day:
            continue
        if i - last_entry <= cfg.cooldown_bars:
            continue
        out.append(sig)
        last_entry = i
        trades_today[day] = trades_today.get(day, 0) + 1

    return out


def wyckoff_gene(cfg: WyckoffConfig | None = None) -> dict[str, Any]:
    c = cfg or WyckoffConfig()
    return {"strategy_type": "wyckoff_failed_break", "wyckoff_config": c.to_dict()}
