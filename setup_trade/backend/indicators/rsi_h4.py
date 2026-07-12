"""RSI trên nến H4 thật — resample OHLC H1 → H4, map về H1 chỉ để hiển thị/tín hiệu."""

from __future__ import annotations

import pandas as pd

from .rsi import rsi


def h4_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    work = df[["open", "high", "low", "close"]].copy()
    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC")
    return work.resample("4h", label="right", closed="right").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
    ).dropna(subset=["close"])


def map_h4_to_h1(h4_series: pd.Series, df: pd.DataFrame) -> pd.Series:
    """Forward-fill H4 values onto H1 index — chỉ dùng sau khi H4 bar đã đóng."""
    work = df[["close"]].copy()
    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC")
    mapped = h4_series.reindex(work.index, method="ffill")
    return mapped.reindex(df.index, method="ffill")


def add_h4_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    h4 = h4_ohlc(df)
    if len(h4) < period + 1:
        return pd.Series(float("nan"), index=df.index)
    h4_rsi = rsi(h4["close"], period)
    return map_h4_to_h1(h4_rsi, df)


def add_h4_rsi_closed_only(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """RSI H4 chỉ cập nhật tại các mốc đóng nến H4 (không lookahead intrabar)."""
    if df.empty:
        return pd.Series(dtype=float)
    h4 = h4_ohlc(df)
    if len(h4) < period + 1:
        return pd.Series(float("nan"), index=df.index)
    h4_rsi = rsi(h4["close"], period)
    out = pd.Series(float("nan"), index=df.index)
    for h4_ts, val in h4_rsi.items():
        mask = df.index >= h4_ts
        if mask.any():
            out.loc[mask] = val
    return out.ffill()
