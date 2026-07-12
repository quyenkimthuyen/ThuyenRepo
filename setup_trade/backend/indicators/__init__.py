from __future__ import annotations

import pandas as pd

from backend.indicators.atr import atr
from backend.indicators.ema import ema
from backend.indicators.rsi import rsi
from backend.indicators.rsi_h4 import add_h4_rsi_closed_only


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ema50"] = ema(out["close"], 50)
    out["ema200"] = ema(out["close"], 200)
    out["rsi14"] = rsi(out["close"], 14)
    out["rsi14_h4"] = add_h4_rsi_closed_only(out, 14)
    out["atr14"] = atr(out, 14)
    return out
