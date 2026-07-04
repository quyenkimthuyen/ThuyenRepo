"""Phân tích lệnh thua Pin Bar + metadata tín hiệu."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr, rsi
from systemtrain.strategy.famous import FamousConfig, detect_pin_bar


@dataclass
class PinBarSignalMeta:
    signal_bar: int
    entry_bar: int
    direction: int
    tag: str
    sl_price: float
    wick_body_ratio: float
    wick_range_ratio: float
    body_range_ratio: float
    range_atr: float
    at_swing: bool
    htf_trend: float
    htf_adx: float
    adx_1h: float
    rsi_entry: float
    hour: int


def detect_pin_signals_with_meta(
    df: pd.DataFrame,
    cfg: FamousConfig | None = None,
) -> list[PinBarSignalMeta]:
    cfg = cfg or FamousConfig(name="pin_bar")
    base = detect_pin_bar(df, cfg)
    if not base:
        return []

    highs = df["high"].values
    lows = df["low"].values
    opens = df["open"].values
    closes = df["close"].values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values
    rsi_vals = rsi(df["close"], 14).values
    hours = df.index.hour

    has_htf = "__htf_trend" in df.columns
    htf_trend = df["__htf_trend"].values if has_htf else np.zeros(len(df))
    htf_adx = df["__htf_adx"].values if "__htf_adx" in df.columns else np.zeros(len(df))

    meta_list: list[PinBarSignalMeta] = []
    for sig in base:
        i = sig.signal_bar
        entry = sig.entry_bar
        rng = highs[i] - lows[i]
        body = abs(closes[i] - opens[i])
        lower_wick = min(opens[i], closes[i]) - lows[i]
        upper_wick = highs[i] - max(opens[i], closes[i])
        wick = lower_wick if sig.direction == 1 else upper_wick
        min_body = max(body, rng * 0.05) if rng > 0 else 0.0
        start = max(0, i - cfg.swing_lookback)
        if sig.direction == 1:
            at_sw = lows[i] <= np.min(lows[start : i + 1]) + 1e-9
        else:
            at_sw = highs[i] >= np.max(highs[start : i + 1]) - 1e-9

        meta_list.append(PinBarSignalMeta(
            signal_bar=i,
            entry_bar=entry,
            direction=sig.direction,
            tag=sig.tag,
            sl_price=sig.sl_price,
            wick_body_ratio=float(wick / min_body) if min_body > 0 else 0.0,
            wick_range_ratio=float(wick / rng) if rng > 0 else 0.0,
            body_range_ratio=float(body / rng) if rng > 0 else 0.0,
            range_atr=float(rng / atr_vals[i]) if atr_vals[i] > 0 else 0.0,
            at_swing=at_sw,
            htf_trend=float(htf_trend[entry]) if has_htf else 0.0,
            htf_adx=float(htf_adx[entry]) if has_htf else np.nan,
            adx_1h=float(adx_vals[entry]),
            rsi_entry=float(rsi_vals[entry]),
            hour=int(hours[entry]),
        ))
    return meta_list


def classify_loss(meta: PinBarSignalMeta, trade, df: pd.DataFrame) -> list[str]:
    """Gán nhãn nguyên nhân thua (có thể nhiều nhãn)."""
    reasons: list[str] = []
    entry_i = df.index.get_loc(trade.entry_time)
    bars_held = df.index.get_loc(trade.exit_time) - entry_i if trade.exit_time else 0

    if bars_held <= 3 and trade.result == "sl":
        reasons.append("quick_stop_rejection")

    if meta.hour in (7, 8):
        reasons.append("early_london_chop")

    if meta.wick_range_ratio < 0.60:
        reasons.append("weak_pin_shape")

    if not meta.at_swing:
        reasons.append("not_at_swing")

    if meta.body_range_ratio > 0.22:
        reasons.append("large_body_pin")

    if meta.range_atr < 0.75:
        reasons.append("small_candle_range")

    if meta.adx_1h >= 35:
        reasons.append("strong_1h_trend")

    if meta.direction == 1 and meta.rsi_entry > 55:
        reasons.append("rsi_not_oversold")
    if meta.direction == -1 and meta.rsi_entry < 45:
        reasons.append("rsi_not_overbought")

    if not reasons:
        reasons.append("other")
    return reasons
