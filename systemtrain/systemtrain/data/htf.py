"""Higher timeframe features — 4H filter for 1H entry, no lookahead."""

from __future__ import annotations

import numpy as np
import pandas as pd

from systemtrain.data.timeframes import resample_ohlcv
from systemtrain.indicators.library import adx, atr, ema, macd, rsi


def add_htf_features(df: pd.DataFrame, htf_rule: str = "4h") -> pd.DataFrame:
    """
    Attach completed HTF bar features to entry-timeframe bars.
    Default: 4H filter on 1H entry bars.
  Uses shift(1) — only last closed HTF candle.
    """
    out = df.copy()
    htf = resample_ohlcv(df, htf_rule)

    h_close = htf["close"]
    h_ema21 = ema(h_close, 21)
    h_ema50 = ema(h_close, 50)
    h_rsi = rsi(h_close, 14)
    h_atr = atr(htf["high"], htf["low"], h_close, 14)
    _, _, h_macd_hist = macd(h_close)
    h_adx = adx(htf["high"], htf["low"], h_close, 14)

    h1_feat = pd.DataFrame(
        {
            "__htf_trend": np.where(h_close > h_ema50, 1, np.where(h_close < h_ema50, -1, 0)),
            "__htf_ema21_dist": (h_close - h_ema21) / h_atr.replace(0, np.nan),
            "__htf_rsi": h_rsi,
            "__htf_adx": h_adx,
            "__htf_macd_hist": h_macd_hist,
            "__htf_momentum": h_close.pct_change(4),
            "__htf_bull_stack": ((h_ema21 > h_ema50) & (h_close > h_ema21)).astype(float),
            "__htf_bear_stack": ((h_ema21 < h_ema50) & (h_close < h_ema21)).astype(float),
            "__htf_4h_trend": np.where(h_close > h_ema50, 1, np.where(h_close < h_ema50, -1, 0)),
        },
        index=htf.index,
    )

    h1_feat = h1_feat.shift(1)
    aligned = h1_feat.reindex(out.index, method="ffill")
    for col in h1_feat.columns:
        out[col] = aligned[col]
    return out
