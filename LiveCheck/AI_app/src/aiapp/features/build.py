from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
  delta = close.diff()
  up = delta.clip(lower=0.0)
  down = -delta.clip(upper=0.0)
  ma_up = up.ewm(alpha=1 / n, adjust=False).mean()
  ma_down = down.ewm(alpha=1 / n, adjust=False).mean()
  rs = ma_up / ma_down.replace(0.0, np.nan)
  return 100 - (100 / (1 + rs))


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
  prev_close = df["close"].shift(1)
  tr = pd.concat(
    [
      (df["high"] - df["low"]).abs(),
      (df["high"] - prev_close).abs(),
      (df["low"] - prev_close).abs(),
    ],
    axis=1,
  ).max(axis=1)
  return tr.rolling(n, min_periods=n).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
  out = df.copy()
  out["ret1"] = out["close"].pct_change()
  out["ema_fast"] = out["close"].ewm(span=20, adjust=False).mean()
  out["ema_slow"] = out["close"].ewm(span=80, adjust=False).mean()
  out["ema_slope"] = out["ema_fast"].pct_change(5)
  out["rsi"] = _rsi(out["close"], 14)
  out["atr"] = _atr(out, 14)
  out["atr_pct"] = out["atr"] / out["close"]
  roll = out["close"].rolling(48, min_periods=24)
  out["z"] = (out["close"] - roll.mean()) / roll.std(ddof=0).replace(0.0, np.nan)
  out["hour"] = out.index.hour
  out["london"] = out["hour"].between(7, 16).astype(int)
  # Daily ATR mapped onto intraday bars (for swing/donchian stops)
  daily_atr = out["atr"].resample("1D").mean().reindex(out.index, method="ffill")
  out["atr_daily"] = daily_atr
  return out
