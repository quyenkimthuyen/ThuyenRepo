"""Rich feature space for setup discovery — learned from data, not textbooks."""

from __future__ import annotations

import numpy as np
import pandas as pd

from systemtrain.indicators.library import atr, bollinger_bands, ema, rsi


def add_learning_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]

    out["__feat_rsi7"] = rsi(close, 7)
    out["__feat_rsi14"] = rsi(close, 14)
    out["__feat_ema21_dist"] = (close - ema(close, 21)) / atr(high, low, close, 14).replace(0, np.nan)
    out["__feat_ema50_dist"] = (close - ema(close, 50)) / atr(high, low, close, 14).replace(0, np.nan)
    out["__feat_mom4"] = close.pct_change(4)
    out["__feat_mom16"] = close.pct_change(16)
    out["__feat_hour"] = out.index.hour.astype(float)
    out["__feat_dow"] = out.index.dayofweek.astype(float)

    bb_u, bb_m, bb_l = bollinger_bands(close, 20, 2.0)
    width = (bb_u - bb_l).replace(0, np.nan)
    out["__feat_bb_pos"] = (close - bb_l) / width

    atr14 = atr(high, low, close, 14)
    out["__feat_atr_ratio"] = atr14 / atr14.rolling(96, min_periods=20).mean()

    out["__feat_body"] = (close - out["open"]).abs() / atr14.replace(0, np.nan)
    out["__feat_upper_wick"] = (high - np.maximum(close, out["open"])) / atr14.replace(0, np.nan)
    out["__feat_lower_wick"] = (np.minimum(close, out["open"]) - low) / atr14.replace(0, np.nan)

    # Session context
    out["__feat_london"] = ((out["__feat_hour"] >= 7) & (out["__feat_hour"] < 12)).astype(float)
    out["__feat_ny"] = ((out["__feat_hour"] >= 12) & (out["__feat_hour"] < 17)).astype(float)

    # Creative composite signals (learned interactions)
    if "__htf_trend" in out.columns:
        out["__feat_aligned_mom"] = out["__feat_mom4"] * out["__htf_trend"]
        out["__feat_rsi_spread"] = out["__feat_rsi7"] - out["__htf_rsi"]
        out["__feat_trend_strength"] = out["__htf_adx"] * out["__htf_trend"].abs()
        out["__feat_pullback_long"] = (
            (out["__htf_trend"] >= 1)
            & (out["__feat_rsi14"] < 45)
            & (out["__feat_ema21_dist"] < 0)
        ).astype(float)
        out["__feat_pullback_short"] = (
            (out["__htf_trend"] <= -1)
            & (out["__feat_rsi14"] > 55)
            & (out["__feat_ema21_dist"] > 0)
        ).astype(float)
        # Regime-aware composites
        trend = (out["__htf_adx"] >= 22) & (out["__htf_trend"].abs() >= 1)
        rng = out["__htf_adx"] < 18
        out["__feat_regime_trend"] = trend.astype(float)
        out["__feat_regime_range"] = rng.astype(float)
        out["__feat_trend_long"] = (trend & (out["__htf_trend"] >= 1)).astype(float)
        out["__feat_trend_short"] = (trend & (out["__htf_trend"] <= -1)).astype(float)
        out["__feat_mr_long"] = (rng & (out["__feat_bb_pos"] < 0.28)).astype(float)
        out["__feat_mr_short"] = (rng & (out["__feat_bb_pos"] > 0.72)).astype(float)
        out["__feat_breakout_long"] = (
            trend & (out["__feat_mom4"] > 0) & (out["__feat_bb_pos"] > 0.85)
        ).astype(float)
        out["__feat_breakout_short"] = (
            trend & (out["__feat_mom4"] < 0) & (out["__feat_bb_pos"] < 0.15)
        ).astype(float)

    return out


FEATURE_COLUMNS = [
    "__feat_rsi7",
    "__feat_rsi14",
    "__feat_ema21_dist",
    "__feat_ema50_dist",
    "__feat_mom4",
    "__feat_mom16",
    "__feat_hour",
    "__feat_dow",
    "__feat_bb_pos",
    "__feat_atr_ratio",
    "__feat_body",
    "__feat_upper_wick",
    "__feat_lower_wick",
    "__feat_london",
    "__feat_ny",
    "__feat_aligned_mom",
    "__feat_rsi_spread",
    "__feat_trend_strength",
    "__feat_pullback_long",
    "__feat_pullback_short",
    "__feat_regime_trend",
    "__feat_regime_range",
    "__feat_trend_long",
    "__feat_trend_short",
    "__feat_mr_long",
    "__feat_mr_short",
    "__feat_breakout_long",
    "__feat_breakout_short",
    "__htf_trend",
    "__htf_ema21_dist",
    "__htf_rsi",
    "__htf_adx",
    "__htf_macd_hist",
    "__htf_momentum",
    "__htf_bull_stack",
    "__htf_bear_stack",
]

HTF_LONG_FILTERS = [
    ("__htf_trend", "gte", 1.0),
]

HTF_SHORT_FILTERS = [
    ("__htf_trend", "lte", -1.0),
]

# Lọc 4H chặt theo stack (EMA21/50 + close) — dùng cho Wyckoff & so sánh learned
HTF_STACK_LONG_FILTERS = [
    ("__htf_bull_stack", "gte", 1.0),
]

HTF_STACK_SHORT_FILTERS = [
    ("__htf_bear_stack", "gte", 1.0),
]
