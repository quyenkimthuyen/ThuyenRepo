"""
Chiến lược forex nổi tiếng — MACD div, London breakout, Pin bar, Inside bar, EMA pullback, Bollinger MR.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr, bollinger_bands, ema, macd, rsi
from systemtrain.strategy.signal import TradeSignal
from systemtrain.strategy.wyckoff import _htf_allows, WyckoffConfig


@dataclass
class FamousConfig:
    name: str = "base"
    rr: float = 2.0
    session_start: int = 7
    session_end: int = 17
    cooldown_bars: int = 6
    max_trades_per_day: int = 2
    entry_delay_bars: int = 1
    sl_atr_mult: float = 0.6
    sl_buffer_pips: float = 2.0
    pip_size: float = 0.0001
    use_htf_filter: bool = True
    htf_mode: str = "soft"
    min_htf_adx: float = 0.0
    # london breakout
    asian_start: int = 0
    asian_end: int = 7
    london_end: int = 12
    min_asian_range_atr: float = 0.4
    max_asian_range_atr: float = 2.5
    # pin bar
    min_wick_body_ratio: float = 2.0
    max_body_range_ratio: float = 0.35
    min_wick_range_ratio: float = 0.0
    min_range_atr: float = 0.0
    require_at_swing: bool = False
    swing_lookback: int = 20
    max_adx_1h: float = 0.0
    # ema pullback
    ema_period: int = 20
    pullback_atr: float = 0.5
    # bollinger
    bb_period: int = 20
    bb_std: float = 2.0
    max_adx: float = 28.0
    rsi_oversold: float = 38.0
    rsi_overbought: float = 62.0
    # macd div
    swing_left: int = 3
    swing_right: int = 3
    min_swing_gap: int = 10
    max_swing_gap: int = 90
    min_macd_diff: float = 0.00005
    # donchian
    donchian_period: int = 20
    # inside bar
    max_inside_range_ratio: float = 0.65
    min_mother_range_atr: float = 0.35
    breakout_lookforward: int = 4
    max_breakout_bars: int = 0
    require_close_break: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def _session_filter(df: pd.DataFrame, signals: list[TradeSignal], cfg: FamousConfig) -> list[TradeSignal]:
    if not signals:
        return []
    hours = df.index.hour
    dates = df.index.date
    out: list[TradeSignal] = []
    last = -cfg.cooldown_bars - 1
    per_day: dict = {}
    for sig in sorted(signals, key=lambda s: s.entry_bar):
        i = sig.entry_bar
        if i >= len(df):
            continue
        if hours[i] < cfg.session_start or hours[i] >= cfg.session_end:
            continue
        d = dates[i]
        if per_day.get(d, 0) >= cfg.max_trades_per_day:
            continue
        if i - last <= cfg.cooldown_bars:
            continue
        out.append(sig)
        last = i
        per_day[d] = per_day.get(d, 0) + 1
    return out


def _htf(df: pd.DataFrame, i: int, direction: int, cfg: FamousConfig) -> bool:
    if not cfg.use_htf_filter:
        return True
    w = WyckoffConfig(
        use_htf_filter=True,
        htf_mode=cfg.htf_mode,
        min_htf_adx=cfg.min_htf_adx if cfg.min_htf_adx > 0 else 22.0,
    )
    if not _htf_allows(df, i, direction, w):
        return False
    if cfg.min_htf_adx > 0 and cfg.htf_mode in ("strict", "soft", "stack"):
        if "__htf_adx" in df.columns:
            adx_v = df["__htf_adx"].iat[i]
            if np.isnan(adx_v) or adx_v < cfg.min_htf_adx:
                return False
    return True


def _sl_buf(cfg: FamousConfig) -> float:
    return cfg.sl_buffer_pips * cfg.pip_size


# ── 1. London Breakout (Asian range) ─────────────────────────────────────

def detect_london_breakout(df: pd.DataFrame, cfg: FamousConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or FamousConfig(name="london_breakout")
    if len(df) < 200:
        return []

    highs, lows, closes = df["high"].values, df["low"].values, df["close"].values
    hours = df.index.hour
    dates = df.index.date
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    signals: list[TradeSignal] = []

    unique_days = sorted(set(dates))
    for day in unique_days:
        day_mask = dates == day
        day_idx = np.where(day_mask)[0]
        if len(day_idx) < 10:
            continue
        asian = day_idx[(hours[day_idx] >= cfg.asian_start) & (hours[day_idx] < cfg.asian_end)]
        if len(asian) < 3:
            continue
        range_hi = float(np.max(highs[asian]))
        range_lo = float(np.min(lows[asian]))
        rng = range_hi - range_lo
        a = atr_vals[asian[-1]]
        if np.isnan(a) or a <= 0:
            continue
        if rng < cfg.min_asian_range_atr * a or rng > cfg.max_asian_range_atr * a:
            continue

        london = day_idx[(hours[day_idx] >= cfg.asian_end) & (hours[day_idx] < cfg.london_end)]
        for i in london:
            if i + cfg.entry_delay_bars >= len(df):
                break
            entry_bar = i + cfg.entry_delay_bars
            if closes[i] > range_hi and _htf(df, i, 1, cfg):
                sl = range_lo - _sl_buf(cfg) - cfg.sl_atr_mult * a
                signals.append(TradeSignal(i, entry_bar, 1, sl, "london_long"))
                break
            if closes[i] < range_lo and _htf(df, i, -1, cfg):
                sl = range_hi + _sl_buf(cfg) + cfg.sl_atr_mult * a
                signals.append(TradeSignal(i, entry_bar, -1, sl, "london_short"))
                break

    return _session_filter(df, signals, cfg)


# ── 2. Pin Bar (Price Action) ────────────────────────────────────────────

def _pin_at_swing(highs: np.ndarray, lows: np.ndarray, i: int, direction: int, lookback: int) -> bool:
    start = max(0, i - lookback)
    if direction == 1:
        return lows[i] <= np.min(lows[start : i + 1]) + 1e-9
    return highs[i] >= np.max(highs[start : i + 1]) - 1e-9


def detect_pin_bar(df: pd.DataFrame, cfg: FamousConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or FamousConfig(name="pin_bar")
    n = len(df)
    if n < 100:
        return []

    highs, lows, opens, closes = df["high"].values, df["low"].values, df["open"].values, df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values if cfg.max_adx_1h > 0 else None
    signals: list[TradeSignal] = []

    for i in range(20, n - cfg.entry_delay_bars):
        rng = highs[i] - lows[i]
        if rng <= 0:
            continue
        body = abs(closes[i] - opens[i])
        if body / rng > cfg.max_body_range_ratio:
            continue
        lower_wick = min(opens[i], closes[i]) - lows[i]
        upper_wick = highs[i] - max(opens[i], closes[i])
        a = atr_vals[i]
        if np.isnan(a) or a <= 0:
            continue
        if cfg.min_range_atr > 0 and rng / a < cfg.min_range_atr:
            continue

        entry_bar = i + cfg.entry_delay_bars
        if adx_vals is not None:
            adx_entry = adx_vals[entry_bar] if entry_bar < len(adx_vals) else np.nan
            if not np.isnan(adx_entry) and adx_entry > cfg.max_adx_1h:
                continue

        min_body = max(body, rng * 0.05)
        if lower_wick >= cfg.min_wick_body_ratio * min_body:
            wick_rng = lower_wick / rng
            if cfg.min_wick_range_ratio > 0 and wick_rng < cfg.min_wick_range_ratio:
                continue
            if cfg.require_at_swing and not _pin_at_swing(highs, lows, i, 1, cfg.swing_lookback):
                continue
            if _htf(df, i, 1, cfg):
                sl = float(lows[i] - _sl_buf(cfg) - cfg.sl_atr_mult * a)
                signals.append(TradeSignal(i, entry_bar, 1, sl, "pin_bull"))
                continue
        if upper_wick >= cfg.min_wick_body_ratio * min_body:
            wick_rng = upper_wick / rng
            if cfg.min_wick_range_ratio > 0 and wick_rng < cfg.min_wick_range_ratio:
                continue
            if cfg.require_at_swing and not _pin_at_swing(highs, lows, i, -1, cfg.swing_lookback):
                continue
            if _htf(df, i, -1, cfg):
                sl = float(highs[i] + _sl_buf(cfg) + cfg.sl_atr_mult * a)
                signals.append(TradeSignal(i, entry_bar, -1, sl, "pin_bear"))

    return _session_filter(df, signals, cfg)


# ── 3. EMA Pullback (trend + pullback) ───────────────────────────────────

def detect_ema_pullback(df: pd.DataFrame, cfg: FamousConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or FamousConfig(name="ema_pullback")
    if len(df) < cfg.ema_period + 50:
        return []

    closes = df["close"]
    ema_vals = ema(closes, cfg.ema_period).values
    highs, lows, opens = df["high"].values, df["low"].values, df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    signals: list[TradeSignal] = []

    for i in range(cfg.ema_period + 5, len(df) - cfg.entry_delay_bars):
        a = atr_vals[i]
        if np.isnan(a) or a <= 0 or np.isnan(ema_vals[i]):
            continue
        dist = abs(closes.iloc[i] - ema_vals[i])
        if dist > cfg.pullback_atr * a:
            continue
        entry_bar = i + cfg.entry_delay_bars

        if closes.iloc[i] > ema_vals[i] and closes.iloc[i] > opens[i] and _htf(df, i, 1, cfg):
            if cfg.use_htf_filter and "__htf_trend" in df.columns and df["__htf_trend"].iat[i] < 1:
                continue
            sl = float(lows[i] - _sl_buf(cfg) - cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i, entry_bar, 1, sl, "ema_pull_long"))
        elif closes.iloc[i] < ema_vals[i] and closes.iloc[i] < opens[i] and _htf(df, i, -1, cfg):
            if cfg.use_htf_filter and "__htf_trend" in df.columns and df["__htf_trend"].iat[i] > -1:
                continue
            sl = float(highs[i] + _sl_buf(cfg) + cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i, entry_bar, -1, sl, "ema_pull_short"))

    return _session_filter(df, signals, cfg)


# ── 4. Bollinger Mean Reversion ──────────────────────────────────────────

def detect_bollinger_mr(df: pd.DataFrame, cfg: FamousConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or FamousConfig(name="bollinger_mr")
    if len(df) < cfg.bb_period + 30:
        return []

    upper, mid, lower = bollinger_bands(df["close"], cfg.bb_period, cfg.bb_std)
    rsi_vals = rsi(df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values
    highs, lows = df["high"].values, df["low"].values
    closes = df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    signals: list[TradeSignal] = []

    for i in range(cfg.bb_period + 5, len(df) - cfg.entry_delay_bars):
        if not np.isnan(adx_vals[i]) and adx_vals[i] > cfg.max_adx:
            continue
        a = atr_vals[i]
        if np.isnan(a) or a <= 0:
            continue
        entry_bar = i + cfg.entry_delay_bars
        lo, up = lower.iloc[i], upper.iloc[i]
        if closes[i] < lo and rsi_vals[i] < cfg.rsi_oversold and _htf(df, i, 1, cfg):
            sl = float(lows[i] - _sl_buf(cfg) - cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i, entry_bar, 1, sl, "bb_long"))
        elif closes[i] > up and rsi_vals[i] > cfg.rsi_overbought and _htf(df, i, -1, cfg):
            sl = float(highs[i] + _sl_buf(cfg) + cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i, entry_bar, -1, sl, "bb_short"))

    return _session_filter(df, signals, cfg)


# ── 5. MACD Divergence ───────────────────────────────────────────────────

def _swings(arr: np.ndarray, left: int, right: int, kind: str) -> list[int]:
    out = []
    for i in range(left, len(arr) - right):
        seg = arr[i - left : i + right + 1]
        if kind == "low" and arr[i] <= seg.min():
            out.append(i)
        elif kind == "high" and arr[i] >= seg.max():
            out.append(i)
    return out


def detect_macd_divergence(df: pd.DataFrame, cfg: FamousConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or FamousConfig(name="macd_divergence")
    n = len(df)
    if n < 150:
        return []

    _, _, hist = macd(df["close"])
    macd_vals = hist.values
    highs, lows = df["high"].values, df["low"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    signals: list[TradeSignal] = []

    for swings, direction, tag in (
        (_swings(lows, cfg.swing_left, cfg.swing_right, "low"), 1, "macd_bull"),
        (_swings(highs, cfg.swing_left, cfg.swing_right, "high"), -1, "macd_bear"),
    ):
        for j in range(1, len(swings)):
            i1, i2 = swings[j - 1], swings[j]
            gap = i2 - i1
            if gap < cfg.min_swing_gap or gap > cfg.max_swing_gap:
                continue
            a = atr_vals[i2]
            if np.isnan(a) or a <= 0:
                continue
            entry_bar = i2 + cfg.swing_right + cfg.entry_delay_bars
            if entry_bar >= n:
                continue

            if direction == 1:
                if lows[i2] >= lows[i1] or macd_vals[i2] <= macd_vals[i1]:
                    continue
                if macd_vals[i2] - macd_vals[i1] < cfg.min_macd_diff:
                    continue
                if not _htf(df, i2, 1, cfg):
                    continue
                sl = float(min(lows[i1], lows[i2]) - _sl_buf(cfg) - cfg.sl_atr_mult * a)
            else:
                if highs[i2] <= highs[i1] or macd_vals[i2] >= macd_vals[i1]:
                    continue
                if macd_vals[i1] - macd_vals[i2] < cfg.min_macd_diff:
                    continue
                if not _htf(df, i2, -1, cfg):
                    continue
                sl = float(max(highs[i1], highs[i2]) + _sl_buf(cfg) + cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i2, entry_bar, direction, sl, tag))

    return _session_filter(df, signals, cfg)


# ── 6. Donchian Breakout (Turtle) ──────────────────────────────────────────

def detect_donchian_breakout(df: pd.DataFrame, cfg: FamousConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or FamousConfig(name="donchian")
    p = cfg.donchian_period
    if len(df) < p + 30:
        return []

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    signals: list[TradeSignal] = []

    for i in range(p + 2, len(df) - cfg.entry_delay_bars):
        prev_hi = float(np.max(highs[i - p : i]))
        prev_lo = float(np.min(lows[i - p : i]))
        a = atr_vals[i]
        if np.isnan(a) or a <= 0:
            continue
        entry_bar = i + cfg.entry_delay_bars

        if closes[i] > prev_hi and _htf(df, i, 1, cfg):
            if cfg.use_htf_filter and "__htf_trend" in df.columns and df["__htf_trend"].iat[i] < 1:
                continue
            sl = float(prev_lo - _sl_buf(cfg))
            signals.append(TradeSignal(i, entry_bar, 1, sl, "donchian_long"))
        elif closes[i] < prev_lo and _htf(df, i, -1, cfg):
            if cfg.use_htf_filter and "__htf_trend" in df.columns and df["__htf_trend"].iat[i] > -1:
                continue
            sl = float(prev_hi + _sl_buf(cfg))
            signals.append(TradeSignal(i, entry_bar, -1, sl, "donchian_short"))

    return _session_filter(df, signals, cfg)


# ── 7. Inside Bar (mother-bar breakout) ───────────────────────────────────

def detect_inside_bar(df: pd.DataFrame, cfg: FamousConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or FamousConfig(name="inside_bar")
    n = len(df)
    if n < 50:
        return []

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values if cfg.max_adx_1h > 0 else None
    signals: list[TradeSignal] = []
    used_mother: set[int] = set()

    for i in range(1, n - cfg.entry_delay_bars):
        mother_hi = highs[i - 1]
        mother_lo = lows[i - 1]
        if highs[i] >= mother_hi or lows[i] <= mother_lo:
            continue

        mother_rng = mother_hi - mother_lo
        inside_rng = highs[i] - lows[i]
        if mother_rng <= 0:
            continue
        if inside_rng / mother_rng > cfg.max_inside_range_ratio:
            continue

        a_mother = atr_vals[i - 1]
        if np.isnan(a_mother) or a_mother <= 0:
            continue
        if cfg.min_mother_range_atr > 0 and mother_rng / a_mother < cfg.min_mother_range_atr:
            continue

        if i - 1 in used_mother:
            continue

        for j in range(i + 1, min(i + 1 + cfg.breakout_lookforward, n - cfg.entry_delay_bars)):
            if cfg.max_breakout_bars > 0 and (j - i) > cfg.max_breakout_bars:
                continue
            entry_bar = j + cfg.entry_delay_bars
            a = atr_vals[j]
            if np.isnan(a) or a <= 0:
                continue
            if adx_vals is not None:
                adx_entry = adx_vals[entry_bar] if entry_bar < len(adx_vals) else np.nan
                if not np.isnan(adx_entry) and adx_entry > cfg.max_adx_1h:
                    continue

            long_break = closes[j] > mother_hi if cfg.require_close_break else highs[j] > mother_hi
            short_break = closes[j] < mother_lo if cfg.require_close_break else lows[j] < mother_lo

            if long_break and _htf(df, j, 1, cfg):
                sl = float(mother_lo - _sl_buf(cfg) - cfg.sl_atr_mult * a)
                signals.append(TradeSignal(i, entry_bar, 1, sl, "ib_long"))
                used_mother.add(i - 1)
                break
            if short_break and _htf(df, j, -1, cfg):
                sl = float(mother_hi + _sl_buf(cfg) + cfg.sl_atr_mult * a)
                signals.append(TradeSignal(i, entry_bar, -1, sl, "ib_short"))
                used_mother.add(i - 1)
                break

    return _session_filter(df, signals, cfg)


FAMOUS_STRATEGIES = {
    "london_breakout": (detect_london_breakout, FamousConfig(name="london_breakout")),
    "pin_bar": (detect_pin_bar, FamousConfig(
        name="pin_bar", min_wick_body_ratio=4.0, max_body_range_ratio=0.25,
        htf_mode="strict", use_htf_filter=True, min_htf_adx=24.0,
        session_start=9, session_end=16,
        require_at_swing=True, swing_lookback=12, min_wick_range_ratio=0.58,
        max_adx_1h=30.0,
    )),
    "ema_pullback": (detect_ema_pullback, FamousConfig(name="ema_pullback")),
    "bollinger_mr": (detect_bollinger_mr, FamousConfig(name="bollinger_mr")),
    "macd_divergence": (detect_macd_divergence, FamousConfig(name="macd_divergence")),
    "donchian_breakout": (detect_donchian_breakout, FamousConfig(name="donchian_breakout", htf_mode="strict")),
    "inside_bar": (detect_inside_bar, FamousConfig(
        name="inside_bar", htf_mode="strict", use_htf_filter=True, min_htf_adx=24.0,
        session_start=9, session_end=16, max_adx_1h=30.0,
        max_inside_range_ratio=0.60, min_mother_range_atr=0.40,
        breakout_lookforward=6, max_breakout_bars=0,
    )),
}
