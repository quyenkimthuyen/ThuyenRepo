"""Phân tích lệnh thua EMA 50/200 pullback + metadata tín hiệu."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr, ema, rsi
from systemtrain.strategy.ema_trend import EmaTrendConfig, detect_ema_trend, ema_50200_best_cfg


@dataclass
class EmaTrendSignalMeta:
    signal_bar: int
    entry_bar: int
    direction: int
    tag: str
    sl_price: float
    dist_fast_atr: float
    ema_spread_atr: float
    htf_trend: float
    htf_adx: float
    adx_1h: float
    rsi_entry: float
    hour: int


def detect_ema_signals_with_meta(
    df: pd.DataFrame,
    cfg: EmaTrendConfig | None = None,
) -> list[EmaTrendSignalMeta]:
    cfg = cfg or ema_50200_best_cfg()
    base = detect_ema_trend(df, cfg)
    if not base:
        return []

    closes = df["close"]
    ema_fast = ema(closes, cfg.ema_fast).values
    ema_slow = ema(closes, cfg.ema_slow).values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values
    rsi_vals = rsi(closes, 14).values
    hours = df.index.hour

    has_htf = "__htf_trend" in df.columns
    htf_trend = df["__htf_trend"].values if has_htf else np.zeros(len(df))
    htf_adx = df["__htf_adx"].values if "__htf_adx" in df.columns else np.zeros(len(df))

    meta_list: list[EmaTrendSignalMeta] = []
    for sig in base:
        bar = sig.signal_bar
        entry = sig.entry_bar
        a = atr_vals[bar]
        spread = abs(ema_fast[bar] - ema_slow[bar])
        dist = abs(closes.iloc[bar] - ema_fast[bar])

        meta_list.append(EmaTrendSignalMeta(
            signal_bar=bar,
            entry_bar=entry,
            direction=sig.direction,
            tag=sig.tag,
            sl_price=sig.sl_price,
            dist_fast_atr=float(dist / a) if a > 0 else 0.0,
            ema_spread_atr=float(spread / a) if a > 0 else 0.0,
            htf_trend=float(htf_trend[entry]) if has_htf else 0.0,
            htf_adx=float(htf_adx[entry]) if has_htf else np.nan,
            adx_1h=float(adx_vals[entry]),
            rsi_entry=float(rsi_vals[entry]),
            hour=int(hours[entry]),
        ))
    return meta_list


def classify_loss(meta: EmaTrendSignalMeta, trade, df: pd.DataFrame) -> list[str]:
    """Gán nhãn nguyên nhân thua (có thể nhiều nhãn)."""
    reasons: list[str] = []
    entry_i = df.index.get_loc(trade.entry_time)
    bars_held = df.index.get_loc(trade.exit_time) - entry_i if trade.exit_time else 0

    if bars_held <= 3 and trade.result == "sl":
        reasons.append("quick_sl")

    if meta.ema_spread_atr >= 1.0:
        reasons.append("extended_trend")
    elif meta.ema_spread_atr >= 0.5:
        reasons.append("wide_ema_spread")

    if meta.dist_fast_atr > 0.42:
        reasons.append("loose_pullback")

    if not np.isnan(meta.htf_adx) and meta.htf_adx < 30:
        reasons.append("weak_4h_adx")

    if meta.adx_1h >= 26:
        reasons.append("elevated_1h_adx")

    if meta.hour in (7, 8, 16):
        reasons.append("session_edge")

    if not reasons:
        reasons.append("other")
    return reasons


def ema_50200_base_cfg() -> EmaTrendConfig:
    """Config trước tối ưu (để so sánh trong báo cáo)."""
    return EmaTrendConfig(
        ema_fast=50,
        ema_slow=200,
        mode="pullback",
        pullback_atr=0.45,
        htf_mode="strict",
        min_htf_adx=28.0,
        max_adx_1h=28.0,
        session_start=9,
        session_end=16,
    )
