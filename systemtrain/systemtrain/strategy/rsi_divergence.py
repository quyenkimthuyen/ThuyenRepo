"""
RSI divergence on 1H — phân kỳ RSI EURUSD.

Bullish: giá lower low, RSI higher low (thường ở vùng oversold).
Bearish: giá higher high, RSI lower high (thường ở vùng overbought).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr, rsi
from systemtrain.strategy.wyckoff import _htf_allows


@dataclass
class RsiDivConfig:
    rsi_period: int = 14
    swing_left: int = 3
    swing_right: int = 3
    min_swing_gap: int = 10
    max_swing_gap: int = 90
    min_price_diff_atr: float = 0.08
    min_rsi_diff: float = 2.5
    rsi_oversold: float = 45.0
    rsi_overbought: float = 55.0
    rr: float = 2.0
    sl_atr_mult: float = 0.5
    sl_buffer_pips: float = 2.0
    entry_delay_bars: int = 1
    session_start: int = 7
    session_end: int = 18
    cooldown_bars: int = 8
    max_trades_per_day: int = 2
    use_htf_filter: bool = False
    htf_mode: str = "strict"
    min_htf_adx: float = 22.0
    require_4h_align: bool = False
    max_htf_adx_counter: float = 0.0
    max_adx_1h: float = 35.0
    max_neckline_delay: int = 99
    div_mode: str = "regular"
    require_neckline_break: bool = True
    pip_size: float = 0.0001

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> RsiDivConfig:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RsiDivSignal:
    signal_bar: int
    entry_bar: int
    direction: int
    sl_price: float
    div_type: str


def _swing_lows(lows: np.ndarray, left: int, right: int) -> list[int]:
    out: list[int] = []
    for i in range(left, len(lows) - right):
        seg = lows[i - left : i + right + 1]
        if lows[i] <= seg.min():
            out.append(i)
    return out


def _swing_highs(highs: np.ndarray, left: int, right: int) -> list[int]:
    out: list[int] = []
    for i in range(left, len(highs) - right):
        seg = highs[i - left : i + right + 1]
        if highs[i] >= seg.max():
            out.append(i)
    return out


def _htf_ok(df: pd.DataFrame, i: int, direction: int, cfg: RsiDivConfig) -> bool:
    if cfg.require_4h_align and "__htf_trend" in df.columns:
        trend = df["__htf_trend"].iat[i]
        if not np.isnan(trend):
            if direction == 1 and trend < 0:
                return False
            if direction == -1 and trend > 0:
                return False

    if cfg.max_htf_adx_counter > 0 and "__htf_trend" in df.columns and "__htf_adx" in df.columns:
        trend = df["__htf_trend"].iat[i]
        adx4 = df["__htf_adx"].iat[i]
        if not np.isnan(trend) and not np.isnan(adx4):
            counter = (direction == 1 and trend < 0) or (direction == -1 and trend > 0)
            if counter and adx4 >= cfg.max_htf_adx_counter:
                return False

    if not cfg.use_htf_filter:
        return True
    from systemtrain.strategy.wyckoff import WyckoffConfig

    w = WyckoffConfig(
        use_htf_filter=True,
        htf_mode=cfg.htf_mode,
        min_htf_adx=cfg.min_htf_adx,
    )
    return _htf_allows(df, i, direction, w)


def _adx_1h_ok_at(df: pd.DataFrame, adx_vals: np.ndarray, i: int, cfg: RsiDivConfig) -> bool:
    if cfg.max_adx_1h <= 0 or i >= len(adx_vals):
        return True
    v = adx_vals[i]
    return np.isnan(v) or v <= cfg.max_adx_1h


def _adx_1h_ok(df: pd.DataFrame, i: int, cfg: RsiDivConfig) -> bool:
    if cfg.max_adx_1h <= 0:
        return True
    if "__rsi_div_adx" not in df.columns:
        return True
    v = df["__rsi_div_adx"].iat[i]
    return np.isnan(v) or v <= cfg.max_adx_1h


def detect_rsi_divergence_signals(
    df: pd.DataFrame,
    cfg: RsiDivConfig | None = None,
) -> list[RsiDivSignal]:
    cfg = cfg or RsiDivConfig()
    n = len(df)
    need = cfg.swing_left + cfg.swing_right + cfg.max_swing_gap + cfg.rsi_period + 5
    if n < need:
        return []

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    rsi_vals = rsi(df["close"], cfg.rsi_period).values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values
    sl_buf = cfg.sl_buffer_pips * cfg.pip_size

    signals: list[RsiDivSignal] = []
    used: set[tuple[int, str]] = set()

    # Bullish divergence at swing lows
    swings_lo = _swing_lows(lows, cfg.swing_left, cfg.swing_right)
    for j in range(1, len(swings_lo)):
        i2 = swings_lo[j]
        i1 = swings_lo[j - 1]
        gap = i2 - i1
        if gap < cfg.min_swing_gap or gap > cfg.max_swing_gap:
            continue
        if np.isnan(rsi_vals[i1]) or np.isnan(rsi_vals[i2]):
            continue
        a = atr_vals[i2]
        if np.isnan(a) or a <= 0:
            continue

        if cfg.div_mode == "hidden":
            # Hidden bullish: price HL, RSI LL — tiếp diễn xu hướng tăng
            if lows[i2] <= lows[i1] or rsi_vals[i2] >= rsi_vals[i1]:
                continue
        else:
            if lows[i2] >= lows[i1] or rsi_vals[i2] <= rsi_vals[i1]:
                continue
            if rsi_vals[i2] > cfg.rsi_oversold:
                continue

        if (abs(lows[i1] - lows[i2])) < cfg.min_price_diff_atr * a:
            continue
        if abs(rsi_vals[i2] - rsi_vals[i1]) < cfg.min_rsi_diff:
            continue

        confirm = i2 + cfg.swing_right
        if confirm >= n - cfg.entry_delay_bars:
            continue
        if not _htf_ok(df, confirm, 1, cfg):
            continue

        entry_bar = confirm + cfg.entry_delay_bars
        neckline_delay = 0
        if cfg.require_neckline_break:
            neckline = float(np.max(highs[i1 : i2 + 1]))
            found = False
            for k in range(confirm + 1, min(confirm + 12, n)):
                if closes[k] > neckline:
                    entry_bar = k + cfg.entry_delay_bars
                    neckline_delay = k - confirm
                    found = True
                    break
            if not found:
                continue
            if neckline_delay > cfg.max_neckline_delay:
                continue
            if entry_bar >= n:
                continue
        if not _adx_1h_ok_at(df, adx_vals, entry_bar, cfg):
            continue
        if not _htf_ok(df, entry_bar, 1, cfg):
            continue

        key = (entry_bar, "bull")
        if key in used:
            continue
        used.add(key)
        sl_price = float(min(lows[i1], lows[i2]) - sl_buf - cfg.sl_atr_mult * a)
        signals.append(RsiDivSignal(confirm, entry_bar, 1, sl_price, "bullish"))

    # Bearish divergence at swing highs
    swings_hi = _swing_highs(highs, cfg.swing_left, cfg.swing_right)
    for j in range(1, len(swings_hi)):
        i2 = swings_hi[j]
        i1 = swings_hi[j - 1]
        gap = i2 - i1
        if gap < cfg.min_swing_gap or gap > cfg.max_swing_gap:
            continue
        if np.isnan(rsi_vals[i1]) or np.isnan(rsi_vals[i2]):
            continue
        a = atr_vals[i2]
        if np.isnan(a) or a <= 0:
            continue

        if cfg.div_mode == "hidden":
            if highs[i2] >= highs[i1] or rsi_vals[i2] <= rsi_vals[i1]:
                continue
        else:
            if highs[i2] <= highs[i1] or rsi_vals[i2] >= rsi_vals[i1]:
                continue
            if rsi_vals[i2] < cfg.rsi_overbought:
                continue

        if (abs(highs[i2] - highs[i1])) < cfg.min_price_diff_atr * a:
            continue
        if abs(rsi_vals[i1] - rsi_vals[i2]) < cfg.min_rsi_diff:
            continue

        confirm = i2 + cfg.swing_right
        if confirm >= n - cfg.entry_delay_bars:
            continue
        if not _htf_ok(df, confirm, -1, cfg):
            continue

        entry_bar = confirm + cfg.entry_delay_bars
        neckline_delay = 0
        if cfg.require_neckline_break:
            neckline = float(np.min(lows[i1 : i2 + 1]))
            found = False
            for k in range(confirm + 1, min(confirm + 12, n)):
                if closes[k] < neckline:
                    entry_bar = k + cfg.entry_delay_bars
                    neckline_delay = k - confirm
                    found = True
                    break
            if not found:
                continue
            if neckline_delay > cfg.max_neckline_delay:
                continue
            if entry_bar >= n:
                continue
        if not _adx_1h_ok_at(df, adx_vals, entry_bar, cfg):
            continue
        if not _htf_ok(df, entry_bar, -1, cfg):
            continue

        key = (entry_bar, "bear")
        if key in used:
            continue
        used.add(key)
        sl_price = float(max(highs[i1], highs[i2]) + sl_buf + cfg.sl_atr_mult * a)
        signals.append(RsiDivSignal(confirm, entry_bar, -1, sl_price, "bearish"))

    return _apply_session_cooldown(df, signals, cfg)


def _apply_session_cooldown(
    df: pd.DataFrame,
    signals: list[RsiDivSignal],
    cfg: RsiDivConfig,
) -> list[RsiDivSignal]:
    if not signals:
        return []

    hours = df.index.hour
    dates = df.index.date
    out: list[RsiDivSignal] = []
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
