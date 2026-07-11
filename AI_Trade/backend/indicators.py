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


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def add_h4_trend(df: pd.DataFrame) -> pd.Series:
    """Xu hướng lớn H4: EMA50 > EMA200 trên khung 4H, map về từng nến 1H."""
    if df.empty:
        return pd.Series(dtype=bool)

    work = df[["open", "high", "low", "close"]].copy()
    if work.index.tz is None:
        work.index = work.index.tz_localize("UTC")

    h4 = work.resample("4h", label="right", closed="right").agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
    ).dropna(subset=["close"])

    if len(h4) < 3:
        return pd.Series(False, index=df.index)

    h4["ema50"] = ema(h4["close"], 50)
    h4["ema200"] = ema(h4["close"], 200)
    h4_trend = (h4["ema50"] > h4["ema200"]).astype(bool)

    mapped = h4_trend.reindex(work.index, method="ffill")
    mapped = mapped.reindex(df.index, method="ffill")
    return mapped.fillna(False).astype(bool)


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema50"] = ema(out["close"], 50)
    out["ema200"] = ema(out["close"], 200)
    out["rsi14"] = rsi(out["close"], 14)
    out["atr14"] = atr(out, 14)
    out["trend_up"] = out["ema50"] > out["ema200"]
    out["close_above_ema50"] = out["close"] > out["ema50"]
    out["close_above_ema200"] = out["close"] > out["ema200"]
    out["h4_trend_up"] = add_h4_trend(out)
    return out
