"""
EMA trend following — EMA fast/slow pullback, cross, stack.

Presets: EMA 20/100 (noisy) | EMA 50/200 (smoother, tốt hơn trên 1H).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr, ema
from systemtrain.strategy.famous import _htf, _session_filter, _sl_buf, FamousConfig
from systemtrain.strategy.signal import TradeSignal


@dataclass
class EmaTrendConfig:
    ema_fast: int = 20
    ema_slow: int = 100
    mode: str = "pullback"
    pullback_atr: float = 0.5
    require_bounce: bool = True
    cross_lookback: int = 3
    rr: float = 2.0
    session_start: int = 9
    session_end: int = 16
    cooldown_bars: int = 8
    max_trades_per_day: int = 2
    entry_delay_bars: int = 1
    sl_atr_mult: float = 0.6
    sl_buffer_pips: float = 2.0
    sl_ema_slow: bool = True
    pip_size: float = 0.0001
    use_htf_filter: bool = True
    htf_mode: str = "strict"
    min_htf_adx: float = 22.0
    max_adx_1h: float = 35.0
    min_ema_spread_atr: float = 0.0
    max_ema_spread_atr: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    def to_famous(self) -> FamousConfig:
        return FamousConfig(
            name="ema_trend",
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
        )


def ema_50200_best_cfg() -> EmaTrendConfig:
    """EMA 50/200 pullback elite — filter spread EMA + pullback chặt hơn."""
    return EmaTrendConfig(
        ema_fast=50,
        ema_slow=200,
        mode="pullback",
        pullback_atr=0.38,
        htf_mode="strict",
        min_htf_adx=30.0,
        max_adx_1h=26.0,
        max_ema_spread_atr=2.2,
        session_start=9,
        session_end=16,
    )


def ema_20100_cfg() -> EmaTrendConfig:
    return EmaTrendConfig(
        ema_fast=20,
        ema_slow=100,
        mode="pullback",
        htf_mode="strict",
        min_htf_adx=22.0,
        max_adx_1h=30.0,
        session_start=9,
        session_end=16,
    )


def detect_ema_trend(df: pd.DataFrame, cfg: EmaTrendConfig | None = None) -> list[TradeSignal]:
    cfg = cfg or EmaTrendConfig()
    n = len(df)
    if n < cfg.ema_slow + 20:
        return []

    closes = df["close"]
    ema_fast = ema(closes, cfg.ema_fast).values
    ema_slow = ema(closes, cfg.ema_slow).values
    highs = df["high"].values
    lows = df["low"].values
    opens = df["open"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values if cfg.max_adx_1h > 0 else None
    signals: list[TradeSignal] = []
    fcfg = cfg.to_famous()

    for i in range(cfg.ema_slow + 5, n - cfg.entry_delay_bars):
        if np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]):
            continue
        a = atr_vals[i]
        if np.isnan(a) or a <= 0:
            continue
        entry_bar = i + cfg.entry_delay_bars
        if adx_vals is not None:
            adx_e = adx_vals[entry_bar] if entry_bar < len(adx_vals) else np.nan
            if not np.isnan(adx_e) and adx_e > cfg.max_adx_1h:
                continue

        bull_stack = ema_fast[i] > ema_slow[i] and closes.iloc[i] > ema_fast[i]
        bear_stack = ema_fast[i] < ema_slow[i] and closes.iloc[i] < ema_fast[i]
        dist_fast = abs(closes.iloc[i] - ema_fast[i])
        ema_spread = abs(ema_fast[i] - ema_slow[i])
        spread_atr = ema_spread / a
        if cfg.min_ema_spread_atr > 0 and spread_atr < cfg.min_ema_spread_atr:
            continue
        if cfg.max_ema_spread_atr > 0 and spread_atr > cfg.max_ema_spread_atr:
            continue

        long_sig = short_sig = False
        tag = ""

        if cfg.mode == "cross":
            lb = cfg.cross_lookback
            if i < lb + 1:
                continue
            cross_up = ema_fast[i] > ema_slow[i] and ema_fast[i - lb] <= ema_slow[i - lb]
            cross_dn = ema_fast[i] < ema_slow[i] and ema_fast[i - lb] >= ema_slow[i - lb]
            long_sig, short_sig = cross_up, cross_dn
            tag = "ema_cross"

        elif cfg.mode == "pullback":
            touch_long = lows[i] <= ema_fast[i] + cfg.pullback_atr * a and bull_stack
            touch_short = highs[i] >= ema_fast[i] - cfg.pullback_atr * a and bear_stack
            if touch_long and dist_fast <= cfg.pullback_atr * a:
                long_sig = True
                tag = "ema_pull_long"
            if touch_short and dist_fast <= cfg.pullback_atr * a:
                short_sig = True
                tag = "ema_pull_short"

        elif cfg.mode == "stack":
            if bull_stack and closes.iloc[i] > opens[i]:
                long_sig = True
                tag = "ema_stack_long"
            elif bear_stack and closes.iloc[i] < opens[i]:
                short_sig = True
                tag = "ema_stack_short"

        if cfg.require_bounce:
            if long_sig and closes.iloc[i] <= opens[i]:
                long_sig = False
            if short_sig and closes.iloc[i] >= opens[i]:
                short_sig = False

        if long_sig and _htf(df, i, 1, fcfg):
            if cfg.sl_ema_slow:
                sl = float(min(lows[i], ema_slow[i]) - _sl_buf(fcfg) - cfg.sl_atr_mult * a)
            else:
                sl = float(lows[i] - _sl_buf(fcfg) - cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i, entry_bar, 1, sl, tag))
        elif short_sig and _htf(df, i, -1, fcfg):
            if cfg.sl_ema_slow:
                sl = float(max(highs[i], ema_slow[i]) + _sl_buf(fcfg) + cfg.sl_atr_mult * a)
            else:
                sl = float(highs[i] + _sl_buf(fcfg) + cfg.sl_atr_mult * a)
            signals.append(TradeSignal(i, entry_bar, -1, sl, tag))

    return _session_filter(df, signals, fcfg)
