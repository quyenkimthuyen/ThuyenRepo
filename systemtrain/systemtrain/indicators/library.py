from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, min_periods=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_mult: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = sma(close, period)
    std = close.rolling(window=period, min_periods=period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    lowest = low.rolling(window=k_period, min_periods=k_period).min()
    highest = high.rolling(window=k_period, min_periods=k_period).max()
    denom = (highest - lowest).replace(0, np.nan)
    k = 100 * (close - lowest) / denom
    d = k.rolling(window=d_period, min_periods=d_period).mean()
    return k, d


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period)


def rolling_high(high: pd.Series, period: int) -> pd.Series:
    return high.rolling(window=period, min_periods=period).max().shift(1)


def rolling_low(low: pd.Series, period: int) -> pd.Series:
    return low.rolling(window=period, min_periods=period).min().shift(1)


INDICATOR_SOURCES = {
    "close": lambda df, **_: df["close"],
    "open": lambda df, **_: df["open"],
    "high": lambda df, **_: df["high"],
    "low": lambda df, **_: df["low"],
    "volume": lambda df, **_: df.get("volume", pd.Series(0, index=df.index)),
    "rsi": lambda df, period=14, **_: rsi(df["close"], period),
    "ema": lambda df, period=20, **_: ema(df["close"], period),
    "sma": lambda df, period=20, **_: sma(df["close"], period),
    "atr": lambda df, period=14, **_: atr(df["high"], df["low"], df["close"], period),
    "macd": lambda df, fast=12, slow=26, signal=9, **_: macd(df["close"], fast, slow, signal)[0],
    "macd_signal": lambda df, fast=12, slow=26, signal=9, **_: macd(df["close"], fast, slow, signal)[1],
    "macd_hist": lambda df, fast=12, slow=26, signal=9, **_: macd(df["close"], fast, slow, signal)[2],
    "bb_upper": lambda df, period=20, std_mult=2.0, **_: bollinger_bands(df["close"], period, std_mult)[0],
    "bb_mid": lambda df, period=20, std_mult=2.0, **_: bollinger_bands(df["close"], period, std_mult)[1],
    "bb_lower": lambda df, period=20, std_mult=2.0, **_: bollinger_bands(df["close"], period, std_mult)[2],
    "stoch_k": lambda df, k_period=14, d_period=3, **_: stochastic(df["high"], df["low"], df["close"], k_period, d_period)[0],
    "stoch_d": lambda df, k_period=14, d_period=3, **_: stochastic(df["high"], df["low"], df["close"], k_period, d_period)[1],
    "adx": lambda df, period=14, **_: adx(df["high"], df["low"], df["close"], period),
    "rolling_high": lambda df, period=16, **_: rolling_high(df["high"], period),
    "rolling_low": lambda df, period=16, **_: rolling_low(df["low"], period),
    "hour": lambda df, **_: pd.Series(df.index.hour, index=df.index),
}


def compute_indicator(df: pd.DataFrame, name: str, params: dict | None = None) -> pd.Series:
    params = params or {}
    if name not in INDICATOR_SOURCES:
        raise ValueError(f"Unknown indicator: {name}")
    return INDICATOR_SOURCES[name](df, **params)


def precompute_indicators(df: pd.DataFrame, specs: list[tuple[str, dict]]) -> pd.DataFrame:
    """Precompute a set of indicators and attach as columns."""
    out = df.copy()
    for i, (name, params) in enumerate(specs):
        key = f"{name}_{i}"
        out[key] = compute_indicator(df, name, params)
    return out
