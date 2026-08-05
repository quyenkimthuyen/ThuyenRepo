"""Canonical EUR/USD M15 loader backed exclusively by ForgeBridge/MT5."""
from __future__ import annotations

import pandas as pd

from mt5_bridge.history_sync import (
  DATA_DIR,
  MT5_CACHE_PATH,
  MT5_META_PATH,
  load_mt5_cache,
  start_history_sync,
)
from mt5_bridge.protocol import read_json

CACHE_PATH = MT5_CACHE_PATH
META_PATH = MT5_META_PATH
DEFAULT_START = "2025-01-01"


def require_canonical_mt5_data() -> dict:
  """Fail closed unless the active cache has complete MT5 provenance."""
  meta = read_json(META_PATH)
  if (
    not isinstance(meta, dict)
    or meta.get("source") != "mt5_ea"
    or meta.get("timeframe") != "M15"
  ):
    raise RuntimeError("Dữ liệu chưa được xác nhận từ ForgeBridge/XM MT5.")
  missing = [key for key in ("broker", "fingerprint", "bars", "start", "end") if not meta.get(key)]
  if missing:
    raise RuntimeError(f"Metadata MT5 thiếu: {', '.join(missing)}")
  return meta


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
  rename = {
    "open": "Open", "high": "High", "low": "Low",
    "close": "Close", "volume": "Volume",
  }
  out = df.rename(columns={c: rename.get(str(c).lower(), c) for c in df.columns})
  if "Volume" not in out.columns:
    out["Volume"] = 0.0
  out = out[["Open", "High", "Low", "Close", "Volume"]].copy()
  out.index = pd.to_datetime(out.index, utc=True).tz_convert(None)
  out = out.sort_index()
  out = out[~out.index.duplicated(keep="last")]
  return out.dropna()


def _slice_cache(cached: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
  return cached[(cached.index >= start) & (cached.index < end)].copy()


def download_eurusd_m15(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
  *,
  allow_stale_on_error: bool = True,
  max_cache_age_hours: float | None = None,
) -> pd.DataFrame:
  """Request an MT5 sync and return currently available broker history."""
  del use_cache, allow_stale_on_error, max_cache_age_hours
  if force_refresh:
    start_history_sync(force=True)
  cached = load_mt5_cache()
  if cached is None or cached.empty:
    start_history_sync()
    raise RuntimeError(
      "Chưa có lịch sử M15 từ MT5. Hãy giữ ForgeBridge EA và MT5 Bridge service "
      "đang chạy để hoàn tất đồng bộ history."
    )
  require_canonical_mt5_data()
  start = pd.Timestamp(start_date)
  end = (
    pd.Timestamp(end_date)
    if end_date else pd.Timestamp.now().normalize() + pd.Timedelta(days=1)
  )
  return _slice_cache(_normalize_ohlcv(cached), start, end)


def load_eurusd_m15(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
) -> pd.DataFrame:
  """Load canonical MT5 EUR/USD M15 data."""
  return download_eurusd_m15(
    start_date, end_date, use_cache, force_refresh,
  ).dropna()


def get_train_window_indices(df: pd.DataFrame, as_of: pd.Timestamp, weeks: int = 3):
  """Return (start_idx, end_idx) for training window ending at as_of (exclusive)."""
  train_start = as_of - pd.Timedelta(weeks=weeks)
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
