"""EMA & RSI indicators — RSI(14) on H4 mapped to H1 candles."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _h4_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    work = df[["open", "high", "low", "close"]].copy()
    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC")
    return work.resample("4h", label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna(subset=["close"])


def _map_h4_to_1h(h4_series: pd.Series, df: pd.DataFrame) -> pd.Series:
    work = df[["close"]].copy()
    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC")
    mapped = h4_series.reindex(work.index, method="ffill")
    return mapped.reindex(df.index, method="ffill")


def add_h4_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    h4 = _h4_ohlc(df)
    if len(h4) < period + 1:
        return pd.Series(float("nan"), index=df.index)
    return _map_h4_to_1h(rsi(h4["close"], period), df)


def add_h4_trend(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    h4 = _h4_ohlc(df)
    if len(h4) < 3:
        return pd.Series(False, index=df.index)
    h4["ema50"] = ema(h4["close"], 50)
    h4["ema200"] = ema(h4["close"], 200)
    return _map_h4_to_1h((h4["ema50"] > h4["ema200"]).astype(bool), df).fillna(False)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema50"] = ema(out["close"], 50)
    out["ema200"] = ema(out["close"], 200)
    out["rsi14_h4"] = add_h4_rsi(out, 14)
    out["h4_trend_up"] = add_h4_trend(out)
    out["trend_up"] = out["ema50"] > out["ema200"]
    prev_close = out["close"].shift(1)
    tr = pd.concat(
        [
            out["high"] - out["low"],
            (out["high"] - prev_close).abs(),
            (out["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    out["atr14"] = tr.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    return out
