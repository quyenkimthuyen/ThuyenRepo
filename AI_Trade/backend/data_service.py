from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import CANDLES_PATH, SPLITS_PATH


def load_splits() -> dict[str, Any]:
    return json.loads(SPLITS_PATH.read_text(encoding="utf-8"))


def load_candles(path: Path | None = None) -> pd.DataFrame:
    path = path or CANDLES_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run: python scripts/fetch_data.py"
        )
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
    splits = load_splits()["periods"][period]
    start = pd.Timestamp(splits["from"], tz="UTC")
    end = pd.Timestamp(splits["to"], tz="UTC") + pd.Timedelta(hours=23, minutes=59)
    return df.loc[start:end]


def candles_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for ts, row in df.iterrows():
        rows.append(
            {
                "time": int(ts.timestamp()),
                "open": round(float(row["open"]), 5),
                "high": round(float(row["high"]), 5),
                "low": round(float(row["low"]), 5),
                "close": round(float(row["close"]), 5),
                "volume": float(row.get("volume", 0)),
            }
        )
    return rows


def period_for_timestamp(ts: pd.Timestamp) -> str | None:
    splits = load_splits()["periods"]
    for name, cfg in splits.items():
        start = pd.Timestamp(cfg["from"], tz="UTC")
        end = pd.Timestamp(cfg["to"], tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        if start <= ts <= end:
            return name
    return None
