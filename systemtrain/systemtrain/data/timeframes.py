"""Resample OHLCV to higher timeframes for 1H entry trading."""

from __future__ import annotations

import pandas as pd


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    ohlc = df.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    return ohlc


def to_entry_timeframe(df: pd.DataFrame, entry_tf: str = "1h") -> pd.DataFrame:
    """Convert stored 15m data to entry timeframe."""
    rules = {
        "15m": None, "15min": None,
        "30m": "30min", "30min": "30min",
        "1h": "1h", "1H": "1h",
        "4h": "4h", "4H": "4h",
    }
    rule = rules.get(entry_tf, entry_tf)
    if rule is None:
        return df.copy()
    return resample_ohlcv(df, rule)


# Entry TF -> HTF filter (≈4× higher)
ENTRY_HTF_MAP = {
    "15m": "1h",
    "30m": "2h",
    "1h": "4h",
    "4h": "1D",
}


def htf_for_entry(entry_tf: str) -> str:
    key = entry_tf.lower().replace("min", "m")
    if key == "1h":
        return "4h"
    if key == "4h":
        return "1D"
    return ENTRY_HTF_MAP.get(key, "4h")
