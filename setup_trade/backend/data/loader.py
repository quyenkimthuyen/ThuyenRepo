from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from backend.core.config import CANDLES_PATH
from backend.core.periods import period_bounds


def load_candles(path: Path | None = None) -> pd.DataFrame:
    path = path or CANDLES_PATH
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run: python scripts/fetch_data.py")
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
        df = df.set_index("datetime")
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")
    else:
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0], utc=True)
        df = df.set_index(df.columns[0])
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df


def slice_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    start, end = period_bounds(period)
    return df.loc[start:end]


def candles_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ts, row in df.iterrows():
        rec: dict[str, Any] = {
            "time": int(ts.timestamp()),
            "open": round(float(row["open"]), 5),
            "high": round(float(row["high"]), 5),
            "low": round(float(row["low"]), 5),
            "close": round(float(row["close"]), 5),
            "volume": float(row.get("volume", 0)),
        }
        for col in ("ema50", "ema200", "rsi14", "rsi14_h4", "atr14"):
            if col in row and pd.notna(row[col]):
                rec[col] = round(float(row[col]), 2 if "rsi" in col else 5)
        rows.append(rec)
    return rows
