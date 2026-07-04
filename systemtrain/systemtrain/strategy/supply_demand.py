"""
Supply / Demand zones — base + impulse, retest vùng cung/cầu.

Demand: base (nén) → impulse bullish → retest zone + rejection → long
Supply: base → impulse bearish → retest zone + rejection → short
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr
from systemtrain.strategy.famous import _htf, _session_filter, _sl_buf, FamousConfig
from systemtrain.strategy.signal import TradeSignal


@dataclass
class SupplyDemandConfig:
    rr: float = 2.0
    base_bars: int = 5
    max_base_range_atr: float = 0.85
    min_impulse_atr: float = 1.0
    impulse_bars: int = 4
    max_retest_bars: int = 48
    min_zone_width_atr: float = 0.12
    max_zone_width_atr: float = 0.9
    require_rejection: bool = True
    min_wick_body_ratio: float = 2.0
    session_start: int = 9
    session_end: int = 16
    cooldown_bars: int = 8
    max_trades_per_day: int = 2
    entry_delay_bars: int = 1
    sl_atr_mult: float = 0.5
    sl_buffer_pips: float = 2.0
    pip_size: float = 0.0001
    use_htf_filter: bool = True
    htf_mode: str = "strict"
    min_htf_adx: float = 22.0
    max_adx_1h: float = 35.0

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def to_famous(self) -> FamousConfig:
        """Adapter for shared session/htf helpers."""
        return FamousConfig(
            name="supply_demand",
            rr=self.rr,
            session_start=self.session_start,
            session_end=self.session_end,
            cooldown_bars=self.cooldown_bars,
            max_trades_per_day=self.max_trades_per_day,
            entry_delay_bars=self.entry_delay_bars,
            sl_atr_mult=self.sl_atr_mult,
            sl_buffer_pips=self.sl_buffer_pips,
            pip_size=self.pip_size,
            use_htf_filter=self.use_htf_filter,
            htf_mode=self.htf_mode,
            min_htf_adx=self.min_htf_adx,
            max_adx_1h=self.max_adx_1h,
            min_wick_body_ratio=self.min_wick_body_ratio,
        )


@dataclass
class _Zone:
    kind: str
    hi: float
    lo: float
    expire: int


def _rejection_candle(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    i: int,
    direction: int,
    min_wick_ratio: float,
) -> bool:
    rng = highs[i] - lows[i]
    if rng <= 0:
        return False
    body = abs(closes[i] - opens[i])
    if body / rng > 0.45:
        return False
    lower_wick = min(opens[i], closes[i]) - lows[i]
    upper_wick = highs[i] - max(opens[i], closes[i])
    min_body = max(body, rng * 0.05)
    if direction == 1:
        return lower_wick >= min_wick_ratio * min_body and closes[i] >= opens[i]
    return upper_wick >= min_wick_ratio * min_body and closes[i] <= opens[i]


def _htf_sd(df: pd.DataFrame, i: int, direction: int, cfg: SupplyDemandConfig) -> bool:
    if not cfg.use_htf_filter:
        return True
    f = cfg.to_famous()
    return _htf(df, i, direction, f)


def detect_supply_demand(df: pd.DataFrame, cfg: SupplyDemandConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or SupplyDemandConfig()
    n = len(df)
    min_bars = cfg.base_bars + cfg.impulse_bars + 10
    if n < min_bars + cfg.max_retest_bars:
        return []

    highs = df["high"].values
    lows = df["low"].values
    opens = df["open"].values
    closes = df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values if cfg.max_adx_1h > 0 else None

    zones: list[_Zone] = []
    signals: list[TradeSignal] = []
    used_zone: set[tuple[str, int]] = set()

    for i in range(min_bars, n - cfg.entry_delay_bars):
        zones = [z for z in zones if i <= z.expire]

        impulse_end = i
        impulse_start = i - cfg.impulse_bars
        base_end = impulse_start - 1
        base_start = base_end - cfg.base_bars + 1
        if base_start < 0:
            continue

        a_end = atr_vals[impulse_end]
        if np.isnan(a_end) or a_end <= 0:
            continue

        a_base = atr_vals[base_end]
        if np.isnan(a_base) or a_base <= 0:
            continue

        base_hi = float(np.max(highs[base_start : base_end + 1]))
        base_lo = float(np.min(lows[base_start : base_end + 1]))
        base_rng = base_hi - base_lo
        if base_rng < cfg.min_zone_width_atr * a_base or base_rng > cfg.max_base_range_atr * a_base:
            pass
        else:
            bull_move = closes[impulse_end] - closes[impulse_start]
            bear_move = closes[impulse_start] - closes[impulse_end]
            if bull_move >= cfg.min_impulse_atr * a_end:
                zones.append(_Zone("demand", base_hi, base_lo, i + cfg.max_retest_bars))
            elif bear_move >= cfg.min_impulse_atr * a_end:
                zones.append(_Zone("supply", base_hi, base_lo, i + cfg.max_retest_bars))

        entry_bar = i + cfg.entry_delay_bars
        if adx_vals is not None:
            adx_e = adx_vals[entry_bar] if entry_bar < len(adx_vals) else np.nan
            if not np.isnan(adx_e) and adx_e > cfg.max_adx_1h:
                continue

        a = atr_vals[i]
        if np.isnan(a) or a <= 0:
            continue

        for z in zones:
            zkey = (z.kind, int(z.lo * 1e5))
            if zkey in used_zone:
                continue
            touched = lows[i] <= z.hi and highs[i] >= z.lo
            if not touched:
                continue

            if z.kind == "demand":
                if closes[i] < z.lo:
                    continue
                if cfg.require_rejection and not _rejection_candle(
                    opens, highs, lows, closes, i, 1, cfg.min_wick_body_ratio
                ):
                    continue
                if not _htf_sd(df, i, 1, cfg):
                    continue
                sl = float(z.lo - _sl_buf(cfg.to_famous()) - cfg.sl_atr_mult * a)
                signals.append(TradeSignal(i, entry_bar, 1, sl, "sd_demand"))
                used_zone.add(zkey)
                break

            if closes[i] > z.hi:
                continue
            if cfg.require_rejection and not _rejection_candle(
                opens, highs, lows, closes, i, -1, cfg.min_wick_body_ratio
            ):
                continue
            if not _htf_sd(df, i, -1, cfg):
                continue
            sl = float(z.hi + _sl_buf(cfg.to_famous()) + cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i, entry_bar, -1, sl, "sd_supply"))
            used_zone.add(zkey)
            break

    return _session_filter(df, signals, cfg.to_famous())
