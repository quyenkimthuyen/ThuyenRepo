from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_ohlc(path: Path | str) -> pd.DataFrame:
  path = Path(path)
  if not path.exists():
    raise FileNotFoundError(path)
  df = pd.read_parquet(path)
  # Normalize columns
  cols = {c.lower(): c for c in df.columns}
  rename = {}
  for need in ("open", "high", "low", "close"):
    if need in cols:
      rename[cols[need]] = need
    elif need.capitalize() in df.columns:
      rename[need.capitalize()] = need
  df = df.rename(columns=rename)
  if not {"open", "high", "low", "close"}.issubset(df.columns):
    raise ValueError(f"OHLC columns missing in {path}: {list(df.columns)}")
  if not isinstance(df.index, pd.DatetimeIndex):
    for cand in ("time", "datetime", "timestamp", "date"):
      if cand in df.columns or cand in cols:
        key = cand if cand in df.columns else cols[cand]
        df[key] = pd.to_datetime(df[key], utc=False)
        df = df.set_index(key)
        break
  if not isinstance(df.index, pd.DatetimeIndex):
    df.index = pd.to_datetime(df.index)
  df = df.sort_index()
  df = df[~df.index.duplicated(keep="last")]
  return df[["open", "high", "low", "close"]].astype(float)


def slice_range(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
  s = pd.Timestamp(start)
  e = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
  return df.loc[(df.index >= s) & (df.index <= e)].copy()
