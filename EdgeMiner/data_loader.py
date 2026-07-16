"""Download and prepare EUR/USD H1 data (2022+ via Dukascopy)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
CACHE_PATH = DATA_DIR / "eurusd_h1.parquet"
META_PATH = DATA_DIR / "eurusd_h1_meta.json"
DEFAULT_START = "2022-01-01"
CACHE_MAX_AGE_HOURS = 6


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
  rename = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
  out = df.rename(columns=rename)
  out = out[["Open", "High", "Low", "Close", "Volume"]].copy()
  out.index = pd.to_datetime(out.index, utc=True).tz_convert(None)
  out = out.sort_index()
  out = out[~out.index.duplicated(keep="first")]
  return out.dropna()


def _fetch_dukascopy_h1(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
  import dukascopy_python as d
  from dukascopy_python import INTERVAL_HOUR_1, OFFER_SIDE_BID

  df = d.fetch(
    instrument="EUR/USD",
    interval=INTERVAL_HOUR_1,
    offer_side=OFFER_SIDE_BID,
    start=start.to_pydatetime().replace(tzinfo=None),
    end=end.to_pydatetime().replace(tzinfo=None),
    max_retries=5,
  )
  if df.empty:
    raise RuntimeError(
      f"Không tải được EUR/USD H1 từ Dukascopy ({start.date()} -> {end.date()})."
    )
  return _normalize_ohlcv(df)


def _cache_stale() -> bool:
  if not CACHE_PATH.exists() or not META_PATH.exists():
    return True
  try:
    with open(META_PATH, encoding="utf-8") as f:
      meta = json.load(f)
    fetched_at = pd.Timestamp(meta["fetched_at"])
    age_h = (pd.Timestamp.now() - fetched_at).total_seconds() / 3600
    return age_h > CACHE_MAX_AGE_HOURS
  except Exception:
    return True


def _save_cache(df: pd.DataFrame):
  DATA_DIR.mkdir(parents=True, exist_ok=True)
  df.to_parquet(CACHE_PATH)
  with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump({
      "source": "dukascopy",
      "pair": "EUR/USD",
      "timeframe": "H1",
      "bars": len(df),
      "start": str(df.index[0]),
      "end": str(df.index[-1]),
      "fetched_at": datetime.now(timezone.utc).isoformat(),
    }, f, indent=2)


def _load_cache() -> pd.DataFrame | None:
  if not CACHE_PATH.exists():
    return None
  return _normalize_ohlcv(pd.read_parquet(CACHE_PATH))


def download_eurusd_h1(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
) -> pd.DataFrame:
  """
  Tải EUR/USD H1 từ Dukascopy (hỗ trợ 2022+).
  Dữ liệu được cache tại data/eurusd_h1.parquet.
  """
  start = pd.Timestamp(start_date)
  end = pd.Timestamp(end_date) if end_date else pd.Timestamp.now().normalize() + pd.Timedelta(days=1)

  if use_cache and not force_refresh and not _cache_stale():
    cached = _load_cache()
    if cached is not None and cached.index[0] <= start and cached.index[-1] >= end - pd.Timedelta(days=2):
      return cached[(cached.index >= start) & (cached.index < end)].copy()

  print(f"  Tải Dukascopy EUR/USD H1: {start.date()} -> {end.date()} ...")
  try:
    df = _fetch_dukascopy_h1(start, end)
  except Exception as exc:
    if use_cache and not force_refresh:
      cached = _load_cache()
      if cached is not None and cached.index[0] <= start:
        fallback = cached[(cached.index >= start) & (cached.index < end)].copy()
        if not fallback.empty:
          print(f"  Dukascopy lỗi, dùng cache đến {fallback.index[-1].date()}: {exc}")
          return fallback

    raise RuntimeError(
      "Không tải được EUR/USD H1 từ Dukascopy và chưa có cache local phù hợp. "
      "Kiểm tra mạng/VPN/firewall rồi thử lại, hoặc chạy lại khi Dukascopy ổn định."
    ) from exc

  _save_cache(df)
  print(f"  Đã cache {len(df)} bars -> {CACHE_PATH}")
  return df


def load_eurusd_h1(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
) -> pd.DataFrame:
  """Load EUR/USD H1, mặc định từ 2022-01-01."""
  df = download_eurusd_h1(start_date, end_date, use_cache, force_refresh)
  start = pd.Timestamp(start_date)
  df = df[df.index >= start]
  if end_date:
    df = df[df.index < pd.Timestamp(end_date)]
  return df.dropna()


def get_train_window_indices(df: pd.DataFrame, as_of: pd.Timestamp, months: int = 3):
  """Return (start_idx, end_idx) for training window ending at as_of (exclusive)."""
  train_start = as_of - pd.DateOffset(months=months)
  mask = (df.index >= train_start) & (df.index < as_of)
  indices = df.index[mask]
  if len(indices) < 100:
    return None, None
  start_idx = df.index.get_loc(indices[0])
  end_idx = df.index.get_loc(indices[-1]) + 1
  return start_idx, end_idx


def get_week_indices(df: pd.DataFrame, week_start: pd.Timestamp, week_end: pd.Timestamp):
  """Return (start_idx, end_idx) for a trading week [week_start, week_end)."""
  mask = (df.index >= week_start) & (df.index < week_end)
  indices = df.index[mask]
  if len(indices) == 0:
    return None, None
  start_idx = df.index.get_loc(indices[0])
  end_idx = df.index.get_loc(indices[-1]) + 1
  return start_idx, end_idx
