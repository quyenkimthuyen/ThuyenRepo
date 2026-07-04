"""Phân tích lệnh thua Inside Bar H1 + metadata tín hiệu."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr, rsi
from systemtrain.strategy.famous import FamousConfig, detect_inside_bar


@dataclass
class InsideBarSignalMeta:
    signal_bar: int
    mother_bar: int
    entry_bar: int
    direction: int
    tag: str
    sl_price: float
    inside_range_ratio: float
    mother_range_atr: float
    breakout_delay: int
    htf_trend: float
    htf_adx: float
    adx_1h: float
    rsi_entry: float
    hour: int


def detect_inside_signals_with_meta(
    df: pd.DataFrame,
    cfg: FamousConfig | None = None,
) -> list[InsideBarSignalMeta]:
    cfg = cfg or FamousConfig(name="inside_bar")
    base = detect_inside_bar(df, cfg)
    if not base:
        return []

    highs = df["high"].values
    lows = df["low"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values
    rsi_vals = rsi(df["close"], 14).values
    hours = df.index.hour

    has_htf = "__htf_trend" in df.columns
    htf_trend = df["__htf_trend"].values if has_htf else np.zeros(len(df))
    htf_adx = df["__htf_adx"].values if "__htf_adx" in df.columns else np.zeros(len(df))

    meta_list: list[InsideBarSignalMeta] = []
    for sig in base:
        inside = sig.signal_bar
        mother = inside - 1
        entry = sig.entry_bar
        mother_rng = highs[mother] - lows[mother]
        inside_rng = highs[inside] - lows[inside]
        breakout_bar = entry - cfg.entry_delay_bars

        meta_list.append(InsideBarSignalMeta(
            signal_bar=inside,
            mother_bar=mother,
            entry_bar=entry,
            direction=sig.direction,
            tag=sig.tag,
            sl_price=sig.sl_price,
            inside_range_ratio=float(inside_rng / mother_rng) if mother_rng > 0 else 0.0,
            mother_range_atr=float(mother_rng / atr_vals[mother]) if atr_vals[mother] > 0 else 0.0,
            breakout_delay=int(breakout_bar - inside),
            htf_trend=float(htf_trend[entry]) if has_htf else 0.0,
            htf_adx=float(htf_adx[entry]) if has_htf else np.nan,
            adx_1h=float(adx_vals[entry]),
            rsi_entry=float(rsi_vals[entry]),
            hour=int(hours[entry]),
        ))
    return meta_list


def classify_loss(meta: InsideBarSignalMeta, trade, df: pd.DataFrame) -> list[str]:
    """Gán nhãn nguyên nhân thua (có thể nhiều nhãn)."""
    reasons: list[str] = []
    entry_i = df.index.get_loc(trade.entry_time)
    bars_held = df.index.get_loc(trade.exit_time) - entry_i if trade.exit_time else 0

    if bars_held <= 3 and trade.result == "sl":
        reasons.append("quick_false_break")

    if meta.breakout_delay >= 4:
        reasons.append("late_breakout")

    if meta.inside_range_ratio > 0.55:
        reasons.append("wide_inside_bar")

    if meta.mother_range_atr < 0.45:
        reasons.append("small_mother_bar")

    if not np.isnan(meta.htf_adx) and meta.htf_adx < 26:
        reasons.append("weak_4h_adx")

    if meta.adx_1h >= 28:
        reasons.append("elevated_1h_adx")

    if meta.hour in (7, 8):
        reasons.append("early_session")

    if not reasons:
        reasons.append("other")
    return reasons


def h1_best_cfg() -> FamousConfig:
    return FamousConfig(
        name="inside_bar", rr=2.0, htf_mode="strict", use_htf_filter=True,
        min_htf_adx=24.0, session_start=9, session_end=16, max_adx_1h=30.0,
        max_inside_range_ratio=0.60, min_mother_range_atr=0.40,
        breakout_lookforward=6, max_breakout_bars=0,
    )
