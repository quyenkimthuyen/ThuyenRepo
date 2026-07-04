"""Phân tích lệnh thua RSI divergence + metadata tín hiệu."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from systemtrain.indicators.library import adx, atr, rsi
from systemtrain.strategy.rsi_divergence import RsiDivConfig, detect_rsi_divergence_signals


@dataclass
class RsiDivSignalMeta:
    signal_bar: int
    entry_bar: int
    direction: int
    div_type: str
    sl_price: float
    rsi1: float
    rsi2: float
    rsi_diff: float
    rsi_entry: float
    price_diff_atr: float
    swing_gap: int
    neckline_delay: int
    htf_trend: float
    htf_adx: float
    htf_rsi: float
    adx_1h: float
    atr_1h: float


def detect_rsi_signals_with_meta(
    df: pd.DataFrame,
    cfg: RsiDivConfig | None = None,
) -> list[RsiDivSignalMeta]:
    """Detect signals with analysis fields (mirrors detect logic)."""
    cfg = cfg or RsiDivConfig()
    base = detect_rsi_divergence_signals(df, cfg)
    if not base:
        return []

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    rsi_vals = rsi(df["close"], cfg.rsi_period).values
    atr_vals = atr(df["high"], df["low"], df["close"], 14).values
    adx_vals = adx(df["high"], df["low"], df["close"], 14).values

    has_htf = "__htf_trend" in df.columns
    htf_trend = df["__htf_trend"].values if has_htf else np.zeros(len(df))
    htf_adx = df["__htf_adx"].values if "__htf_adx" in df.columns else np.zeros(len(df))
    htf_rsi = df["__htf_rsi"].values if "__htf_rsi" in df.columns else np.zeros(len(df))

    # Re-scan to attach meta (match by entry_bar + direction)
    meta_list: list[RsiDivSignalMeta] = []
    entry_set = {(s.entry_bar, s.direction) for s in base}

    def _add(i1, i2, confirm, entry_bar, direction, div_type, sl_price, neckline_delay):
        if (entry_bar, direction) not in entry_set:
            return
        a = atr_vals[i2]
        if direction == 1:
            pd_atr = (lows[i1] - lows[i2]) / a if a > 0 else 0
            rdiff = rsi_vals[i2] - rsi_vals[i1]
        else:
            pd_atr = (highs[i2] - highs[i1]) / a if a > 0 else 0
            rdiff = rsi_vals[i1] - rsi_vals[i2]
        meta_list.append(RsiDivSignalMeta(
            signal_bar=confirm,
            entry_bar=entry_bar,
            direction=direction,
            div_type=div_type,
            sl_price=sl_price,
            rsi1=float(rsi_vals[i1]),
            rsi2=float(rsi_vals[i2]),
            rsi_diff=float(rdiff),
            rsi_entry=float(rsi_vals[entry_bar]) if entry_bar < len(rsi_vals) else np.nan,
            price_diff_atr=float(pd_atr),
            swing_gap=i2 - i1,
            neckline_delay=neckline_delay,
            htf_trend=float(htf_trend[entry_bar]) if has_htf else 0,
            htf_adx=float(htf_adx[entry_bar]) if has_htf else np.nan,
            htf_rsi=float(htf_rsi[entry_bar]) if has_htf else np.nan,
            adx_1h=float(adx_vals[entry_bar]),
            atr_1h=float(atr_vals[entry_bar]),
        ))

    swings_lo = _swing_indices(lows, cfg.swing_left, cfg.swing_right, "low")
    for j in range(1, len(swings_lo)):
        i2, i1 = swings_lo[j], swings_lo[j - 1]
        gap = i2 - i1
        if gap < cfg.min_swing_gap or gap > cfg.max_swing_gap:
            continue
        if np.isnan(rsi_vals[i1]) or np.isnan(rsi_vals[i2]):
            continue
        a = atr_vals[i2]
        if np.isnan(a) or a <= 0:
            continue
        if lows[i2] >= lows[i1] or rsi_vals[i2] <= rsi_vals[i1]:
            continue
        if rsi_vals[i2] > cfg.rsi_oversold:
            continue
        if (lows[i1] - lows[i2]) < cfg.min_price_diff_atr * a:
            continue
        if (rsi_vals[i2] - rsi_vals[i1]) < cfg.min_rsi_diff:
            continue
        confirm = i2 + cfg.swing_right
        entry_bar = confirm + cfg.entry_delay_bars
        delay = 0
        if cfg.require_neckline_break:
            neckline = float(np.max(highs[i1 : i2 + 1]))
            found = False
            for k in range(confirm + 1, min(confirm + 12, len(df))):
                if closes[k] > neckline:
                    entry_bar = k + cfg.entry_delay_bars
                    delay = k - confirm
                    found = True
                    break
            if not found:
                continue
        sl_buf = cfg.sl_buffer_pips * cfg.pip_size
        sl = float(min(lows[i1], lows[i2]) - sl_buf - cfg.sl_atr_mult * a)
        _add(i1, i2, confirm, entry_bar, 1, "bullish", sl, delay)

    swings_hi = _swing_indices(highs, cfg.swing_left, cfg.swing_right, "high")
    for j in range(1, len(swings_hi)):
        i2, i1 = swings_hi[j], swings_hi[j - 1]
        gap = i2 - i1
        if gap < cfg.min_swing_gap or gap > cfg.max_swing_gap:
            continue
        if np.isnan(rsi_vals[i1]) or np.isnan(rsi_vals[i2]):
            continue
        a = atr_vals[i2]
        if np.isnan(a) or a <= 0:
            continue
        if highs[i2] <= highs[i1] or rsi_vals[i2] >= rsi_vals[i1]:
            continue
        if rsi_vals[i2] < cfg.rsi_overbought:
            continue
        if (highs[i2] - highs[i1]) < cfg.min_price_diff_atr * a:
            continue
        if (rsi_vals[i1] - rsi_vals[i2]) < cfg.min_rsi_diff:
            continue
        confirm = i2 + cfg.swing_right
        entry_bar = confirm + cfg.entry_delay_bars
        delay = 0
        if cfg.require_neckline_break:
            neckline = float(np.min(lows[i1 : i2 + 1]))
            found = False
            for k in range(confirm + 1, min(confirm + 12, len(df))):
                if closes[k] < neckline:
                    entry_bar = k + cfg.entry_delay_bars
                    delay = k - confirm
                    found = True
                    break
            if not found:
                continue
        sl_buf = cfg.sl_buffer_pips * cfg.pip_size
        sl = float(max(highs[i1], highs[i2]) + sl_buf + cfg.sl_atr_mult * a)
        _add(i1, i2, confirm, entry_bar, -1, "bearish", sl, delay)

    return sorted(meta_list, key=lambda m: m.entry_bar)


def _swing_indices(arr: np.ndarray, left: int, right: int, kind: str) -> list[int]:
    out: list[int] = []
    for i in range(left, len(arr) - right):
        seg = arr[i - left : i + right + 1]
        if kind == "low" and arr[i] <= seg.min():
            out.append(i)
        elif kind == "high" and arr[i] >= seg.max():
            out.append(i)
    return out


def classify_loss(meta: RsiDivSignalMeta, trade, df: pd.DataFrame) -> list[str]:
    """Gán nhãn nguyên nhân thua (có thể nhiều nhãn)."""
    reasons: list[str] = []
    entry_i = df.index.get_loc(trade.entry_time)
    bars_held = df.index.get_loc(trade.exit_time) - entry_i if trade.exit_time else 0

    # 1. Ngược xu hướng 4H
    if meta.direction == 1 and meta.htf_trend < 0:
        reasons.append("counter_4h_trend")
    if meta.direction == -1 and meta.htf_trend > 0:
        reasons.append("counter_4h_trend")

    # 2. 4H trend mạnh (ADX cao) — mean-reversion khó
    if not np.isnan(meta.htf_adx) and meta.htf_adx >= 28:
        if (meta.direction == 1 and meta.htf_trend <= 0) or (meta.direction == -1 and meta.htf_trend >= 0):
            reasons.append("strong_4h_trend_against")

    # 3. Phân kỳ yếu
    if meta.rsi_diff < 4.0:
        reasons.append("weak_rsi_div")
    if meta.price_diff_atr < 0.12:
        reasons.append("weak_price_div")

    # 4. RSI entry không cực đoan (reversal chưa đủ sâu)
    if meta.direction == 1 and meta.rsi_entry > 42:
        reasons.append("rsi_not_oversold")
    if meta.direction == -1 and meta.rsi_entry < 58:
        reasons.append("rsi_not_overbought")

    # 5. 1H đang trend mạnh (ADX cao)
    if meta.adx_1h >= 30:
        reasons.append("strong_1h_trend")

    # 6. Neckline break trễ
    if meta.neckline_delay >= 6:
        reasons.append("late_neckline_break")

    # 7. SL nhanh (< 4 bar) — false breakout neckline
    if bars_held <= 3 and trade.result == "sl":
        reasons.append("quick_stop_false_break")

    # 8. Swing gap quá ngắn
    if meta.swing_gap < 14:
        reasons.append("short_swing_gap")

    if not reasons:
        reasons.append("other")
    return reasons
