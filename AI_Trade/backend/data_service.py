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


def _resolve_period(period: str) -> str:
    legacy = load_splits().get("legacy_map") or {}
    return legacy.get(period, period)


def _period_bounds(period: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    period = _resolve_period(period)
    cfg = load_splits()["periods"][period]
    start = pd.Timestamp(cfg["from"], tz="UTC")
    end = pd.Timestamp(cfg["to"], tz="UTC") + pd.Timedelta(hours=23, minutes=59)
    return start, end


def slice_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    start, end = _period_bounds(period)
    return df.loc[start:end]


def slice_periods(df: pd.DataFrame, periods: list[str]) -> pd.DataFrame:
    """Concatenate multiple period slices (e.g. multi-year backtest)."""
    if not periods:
        return df.iloc[0:0]
    if len(periods) == 1:
        return slice_period(df, periods[0])
    parts = [slice_period(df, p) for p in periods]
    out = pd.concat(parts)
    return out[~out.index.duplicated(keep="last")].sort_index()


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
    from .periods import period_for_timestamp as _pft

    return _pft(ts)


def month_bounds(month: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """month format YYYY-MM → inclusive UTC range for that calendar month."""
    start = pd.Timestamp(f"{month}-01", tz="UTC")
    if start.day != 1:
        raise ValueError(f"Invalid month: {month}")
    end = start + pd.offsets.MonthEnd(0) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    return start, end


def slice_month(df: pd.DataFrame, month: str) -> pd.DataFrame:
    start, end = month_bounds(month)
    return df.loc[start:end]


def months_for_period(period: str) -> list[str]:
    df = slice_period(load_candles(), period)
    if df.empty:
        return []
    cursor = pd.Timestamp(df.index[0].year, df.index[0].month, 1, tz="UTC")
    end_month = pd.Timestamp(df.index[-1].year, df.index[-1].month, 1, tz="UTC")
    months: list[str] = []
    while cursor <= end_month:
        months.append(cursor.strftime("%Y-%m"))
        if cursor.month == 12:
            cursor = pd.Timestamp(cursor.year + 1, 1, 1, tz="UTC")
        else:
            cursor = pd.Timestamp(cursor.year, cursor.month + 1, 1, tz="UTC")
    return months


def filter_records_by_month(
    records: list[dict],
    month: str,
    time_key: str,
) -> list[dict]:
    start, end = month_bounds(month)
    out: list[dict] = []
    for rec in records:
        ts = pd.Timestamp(rec[time_key])
        if ts.tz is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        if start <= ts <= end:
            out.append(rec)
    return out
