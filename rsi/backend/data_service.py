"""Load EURUSD H1 candles and prepare chart payloads."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .divergence import find_rsi_divergences
from .indicators import add_indicators

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "EURUSD_H1.json"

_df_cache: pd.DataFrame | None = None


def load_candles() -> pd.DataFrame:
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    with DATA_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)

    rows = raw["candles"]
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("time").sort_index()
    df = df[["open", "high", "low", "close", "volume"]]
    _df_cache = add_indicators(df)
    return _df_cache


def filter_range(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    out = df
    if start:
        ts = pd.Timestamp(start, tz="UTC")
        out = out[out.index >= ts]
    if end:
        ts = pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23, minutes=59)
        out = out[out.index <= ts]
    return out


def _to_chart_time(ts: pd.Timestamp) -> int:
    return int(ts.timestamp())


def build_chart_payload(df: pd.DataFrame) -> dict:
    candles = []
    ema50 = []
    ema200 = []
    ema800 = []
    rsi_h4 = []

    rsi_ffill = df["rsi14_h4"].ffill()

    for ts, row in df.iterrows():
        t = _to_chart_time(ts)
        candles.append({
            "time": t,
            "open": round(float(row["open"]), 5),
            "high": round(float(row["high"]), 5),
            "low": round(float(row["low"]), 5),
            "close": round(float(row["close"]), 5),
        })
        if pd.notna(row["ema50"]):
            ema50.append({"time": t, "value": round(float(row["ema50"]), 5)})
        if pd.notna(row["ema200"]):
            ema200.append({"time": t, "value": round(float(row["ema200"]), 5)})
        if pd.notna(row["ema800"]):
            ema800.append({"time": t, "value": round(float(row["ema800"]), 5)})
        if pd.notna(rsi_ffill.loc[ts]):
            rsi_h4.append({"time": t, "value": round(float(rsi_ffill.loc[ts]), 2)})

    first = df.index[0].isoformat() if len(df) else None
    last = df.index[-1].isoformat() if len(df) else None

    return {
        "symbol": "EURUSD",
        "timeframe": "H1",
        "rsi_timeframe": "H4",
        "count": len(df),
        "range": {"start": first, "end": last},
        "candles": candles,
        "divergences": find_rsi_divergences(df),
        "indicators": {
            "ema50": ema50,
            "ema200": ema200,
            "ema800": ema800,
            "rsi14_h4": rsi_h4,
        },
    }


def data_info() -> dict:
    if not DATA_PATH.exists():
        return {"exists": False, "path": str(DATA_PATH)}
    df = load_candles()
    return {
        "exists": True,
        "path": str(DATA_PATH),
        "count": len(df),
        "start": df.index[0].isoformat(),
        "end": df.index[-1].isoformat(),
    }
