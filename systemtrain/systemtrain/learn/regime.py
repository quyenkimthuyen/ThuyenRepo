"""Market regime helpers — trend vs range for setup mining."""

from __future__ import annotations

import numpy as np
import pandas as pd

TREND_ADX = 22.0
RANGE_ADX = 18.0


def regime_trend_mask(df: pd.DataFrame) -> np.ndarray:
    """Bars in trending regime (4H ADX elevated + directional bias)."""
    if "__htf_adx" not in df.columns or "__htf_trend" not in df.columns:
        return np.ones(len(df), dtype=bool)
    return (
        (df["__htf_adx"].fillna(0) >= TREND_ADX)
        & (df["__htf_trend"].abs() >= 1)
    ).values


def regime_range_mask(df: pd.DataFrame) -> np.ndarray:
    """Bars in ranging / low-trend regime."""
    if "__htf_adx" not in df.columns:
        return np.zeros(len(df), dtype=bool)
    return (df["__htf_adx"].fillna(99) < RANGE_ADX).values


def regime_label(df: pd.DataFrame) -> pd.Series:
    """Per-bar regime: 1=trend, -1=range, 0=mixed."""
    trend = regime_trend_mask(df)
    rng = regime_range_mask(df)
    out = np.zeros(len(df), dtype=int)
    out[trend] = 1
    out[rng & ~trend] = -1
    return pd.Series(out, index=df.index, name="regime")
