"""Download and prepare GBP/USD H1 data (2022+ via Dukascopy)."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _safe_print(msg: str) -> None:
  """Print without crashing on Windows cp1252 consoles."""
  try:
    print(msg, flush=True)
  except UnicodeEncodeError:
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    print(msg.encode(enc, errors="replace").decode(enc, errors="replace"), flush=True)

DATA_DIR = Path(__file__).parent / "data"
CACHE_PATH = DATA_DIR / "gbpusd_h1.parquet"
META_PATH = DATA_DIR / "gbpusd_h1_meta.json"
DEFAULT_START = "2022-01-01"
CACHE_MAX_AGE_HOURS = 6
FETCH_ATTEMPTS = 4
FETCH_BACKOFF_SEC = 2.0


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
  rename = {"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
  out = df.rename(columns=rename)
  out = out[["Open", "High", "Low", "Close", "Volume"]].copy()
  out.index = pd.to_datetime(out.index, utc=True).tz_convert(None)
  out = out.sort_index()
  out = out[~out.index.duplicated(keep="first")]
  return out.dropna()


def _is_transient_network_error(exc: BaseException) -> bool:
  """True for connection drops / timeouts typical of Dukascopy."""
  names = (
    "ConnectionResetError", "ConnectionAbortedError", "ConnectionError",
    "TimeoutError", "ProtocolError", "ChunkedEncodingError",
  )
  cur: BaseException | None = exc
  seen = 0
  while cur is not None and seen < 6:
    if type(cur).__name__ in names:
      return True
    msg = str(cur).lower()
    if any(tok in msg for tok in (
      "connection aborted", "connection reset", "forcibly closed",
      "timed out", "temporarily unavailable", "broken pipe",
    )):
      return True
    cur = cur.__cause__ or cur.__context__
    seen += 1
  return False


def _fetch_dukascopy_h1(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
  import dukascopy_python as d
  from dukascopy_python import INTERVAL_HOUR_1, OFFER_SIDE_BID

  last_err: BaseException | None = None
  for attempt in range(1, FETCH_ATTEMPTS + 1):
    try:
      df = d.fetch(
        instrument="GBP/USD",
        interval=INTERVAL_HOUR_1,
        offer_side=OFFER_SIDE_BID,
        start=start.to_pydatetime().replace(tzinfo=None),
        end=end.to_pydatetime().replace(tzinfo=None),
        max_retries=5,
      )
      if df.empty:
        raise RuntimeError(
          f"Không tải được GBP/USD H1 từ Dukascopy ({start.date()} -> {end.date()})."
        )
      return _normalize_ohlcv(df)
    except Exception as e:
      last_err = e
      if attempt >= FETCH_ATTEMPTS or not _is_transient_network_error(e):
        break
      wait = FETCH_BACKOFF_SEC * (2 ** (attempt - 1))
      _safe_print(f"  Dukascopy lỗi mạng (lần {attempt}/{FETCH_ATTEMPTS}), chờ {wait:.0f}s...")
      time.sleep(wait)
  assert last_err is not None
  raise last_err


def _cache_stale(*, max_age_hours: float | None = None) -> bool:
  if not CACHE_PATH.exists() or not META_PATH.exists():
    return True
  try:
    with open(META_PATH, encoding="utf-8") as f:
      meta = json.load(f)
    fetched_at = pd.Timestamp(meta["fetched_at"])
    age_h = (pd.Timestamp.now() - fetched_at).total_seconds() / 3600
    limit = CACHE_MAX_AGE_HOURS if max_age_hours is None else max_age_hours
    return age_h > limit
  except Exception:
    return True


def _save_cache(df: pd.DataFrame):
  DATA_DIR.mkdir(parents=True, exist_ok=True)
  df.to_parquet(CACHE_PATH)
  with open(META_PATH, "w", encoding="utf-8") as f:
    json.dump({
      "source": "dukascopy",
      "pair": "GBP/USD",
      "timeframe": "H1",
      "bars": len(df),
      "start": str(df.index[0]),
      "end": str(df.index[-1]),
      "fetched_at": datetime.now(timezone.utc).isoformat(),
    }, f, indent=2)
  try:
    from strategy_miner import notify_data_updated
    notify_data_updated(len(df))
  except Exception:
    pass


def _load_cache() -> pd.DataFrame | None:
  if not CACHE_PATH.exists():
    return None
  return _normalize_ohlcv(pd.read_parquet(CACHE_PATH))


def download_gbpusd_h1(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
  *,
  allow_stale_on_error: bool = True,
  max_cache_age_hours: float | None = None,
) -> pd.DataFrame:
  """
  Tải GBP/USD H1 từ Dukascopy (hỗ trợ 2022+).
  Dữ liệu được cache tại data/gbpusd_h1.parquet.
  Khi mạng lỗi: dùng cache cũ nếu có (trừ khi allow_stale_on_error=False).
  """
  start = pd.Timestamp(start_date)
  end = pd.Timestamp(end_date) if end_date else pd.Timestamp.now().normalize() + pd.Timedelta(days=1)

  if use_cache and not force_refresh and not _cache_stale(max_age_hours=max_cache_age_hours):
    cached = _load_cache()
    if cached is not None and cached.index[0] <= start and cached.index[-1] >= end - pd.Timedelta(days=2):
      return cached[(cached.index >= start) & (cached.index < end)].copy()

  _safe_print(f"  Tải Dukascopy GBP/USD H1: {start.date()} -> {end.date()} ...")
  try:
    df = _fetch_dukascopy_h1(start, end)
  except Exception as e:
    cached = _load_cache() if allow_stale_on_error else None
    if cached is not None:
      _safe_print(f"  Dukascopy lỗi — dùng cache cũ ({len(cached)} bars): {e}")
      return cached[(cached.index >= start) & (cached.index < end)].copy()
    raise
  _save_cache(df)
  _safe_print(f"  Đã cache {len(df)} bars -> {CACHE_PATH}")
  return df


def load_gbpusd_h1(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
) -> pd.DataFrame:
  """Load GBP/USD H1, mặc định từ 2022-01-01."""
  df = download_gbpusd_h1(start_date, end_date, use_cache, force_refresh)
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
