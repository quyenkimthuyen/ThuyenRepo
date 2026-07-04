"""Triple-barrier labels: did price hit TP (2R) before SL (1R) within horizon?"""

from __future__ import annotations

import numpy as np
import pandas as pd

from systemtrain.indicators.library import atr


def compute_trade_labels(
    df: pd.DataFrame,
    atr_period: int = 14,
    atr_mult: float = 1.3,
    rr: float = 2.0,
    max_bars: int = 48,
) -> tuple[pd.Series, pd.Series]:
    """
    For each bar, label whether a long/short with fixed SL/TP would win.
    Entry at bar close; look forward only (for mining on train set).
    """
    n = len(df)
    atr_vals = atr(df["high"], df["low"], df["close"], atr_period).values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values

    long_labels = np.full(n, np.nan)
    short_labels = np.full(n, np.nan)

    for i in range(n - max_bars - 1):
        a = atr_vals[i]
        if np.isnan(a) or a <= 0:
            continue
        entry = closes[i]
        sl_dist = a * atr_mult
        tp_dist = sl_dist * rr

        long_sl = entry - sl_dist
        long_tp = entry + tp_dist
        short_sl = entry + sl_dist
        short_tp = entry - tp_dist

        long_outcome = np.nan
        short_outcome = np.nan

        for j in range(i + 1, min(i + 1 + max_bars, n)):
            if np.isnan(long_outcome):
                sl_hit = lows[j] <= long_sl
                tp_hit = highs[j] >= long_tp
                if sl_hit and tp_hit:
                    long_outcome = 0.0
                elif sl_hit:
                    long_outcome = 0.0
                elif tp_hit:
                    long_outcome = 1.0
            if np.isnan(short_outcome):
                sl_hit = highs[j] >= short_sl
                tp_hit = lows[j] <= short_tp
                if sl_hit and tp_hit:
                    short_outcome = 0.0
                elif sl_hit:
                    short_outcome = 0.0
                elif tp_hit:
                    short_outcome = 1.0
            if not np.isnan(long_outcome) and not np.isnan(short_outcome):
                break

        long_labels[i] = long_outcome
        short_labels[i] = short_outcome

    return (
        pd.Series(long_labels, index=df.index),
        pd.Series(short_labels, index=df.index),
    )
