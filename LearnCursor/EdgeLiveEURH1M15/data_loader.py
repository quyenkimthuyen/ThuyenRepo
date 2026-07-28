"""Canonical EUR/USD loader backed exclusively by ForgeBridge/MT5 (H1 + M15)."""
from __future__ import annotations

import pandas as pd

from config import get_active_tf
from mt5_bridge.history_sync import (
  DATA_DIR,
  cache_meta_for,
  cache_path_for,
  load_mt5_cache,
  start_history_sync,
)
from mt5_bridge.protocol import read_json
from runtime_profiles import get_tf_defaults

# Back-compat aliases (active-TF aware via functions; static default = M15)
CACHE_PATH = cache_path_for("M15")
META_PATH = cache_meta_for("M15")
DEFAULT_START = get_tf_defaults("M15").start_date


def require_canonical_mt5_data(tf: str | None = None) -> dict:
  """Fail closed unless the active cache has complete MT5 provenance."""
  t = str(tf or get_active_tf()).upper()
  meta = read_json(cache_meta_for(t))
  if (
    not isinstance(meta, dict)
    or meta.get("source") != "mt5_ea"
    or meta.get("timeframe") != t
  ):
    raise RuntimeError(f"Dữ liệu {t} chưa được xác nhận từ ForgeBridge/XM MT5.")
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


def download_eurusd(
  start_date: str | None = None,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
  *,
  tf: str | None = None,
  allow_stale_on_error: bool = True,
  max_cache_age_hours: float | None = None,
) -> pd.DataFrame:
  """Request an MT5 sync and return currently available broker history."""
  del use_cache, allow_stale_on_error, max_cache_age_hours
  t = str(tf or get_active_tf()).upper()
  d = get_tf_defaults(t)
  start_date = start_date or d.start_date
  if force_refresh:
    start_history_sync(force=True, tf=t)
  cached = load_mt5_cache(t)
  if cached is None or cached.empty:
    start_history_sync(tf=t)
    raise RuntimeError(
      f"Chưa có lịch sử {t} từ MT5. Hãy giữ ForgeBridge EA và MT5 Bridge service "
      "đang chạy để hoàn tất đồng bộ history."
    )
  require_canonical_mt5_data(t)
  start = pd.Timestamp(start_date)
  end = (
    pd.Timestamp(end_date)
    if end_date else pd.Timestamp.now().normalize() + pd.Timedelta(days=1)
  )
  return _slice_cache(_normalize_ohlcv(cached), start, end)


def download_eurusd_m15(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
  *,
  allow_stale_on_error: bool = True,
  max_cache_age_hours: float | None = None,
) -> pd.DataFrame:
  return download_eurusd(
    start_date, end_date, use_cache, force_refresh,
    tf="M15",
    allow_stale_on_error=allow_stale_on_error,
    max_cache_age_hours=max_cache_age_hours,
  )


def download_eurusd_h1(
  start_date: str | None = None,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
) -> pd.DataFrame:
  return download_eurusd(start_date, end_date, use_cache, force_refresh, tf="H1")


def load_eurusd(
  start_date: str | None = None,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
  *,
  tf: str | None = None,
) -> pd.DataFrame:
  return download_eurusd(
    start_date, end_date, use_cache, force_refresh, tf=tf,
  ).dropna()


def load_eurusd_m15(
  start_date: str = DEFAULT_START,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
) -> pd.DataFrame:
  """Load canonical MT5 EUR/USD M15 data."""
  return load_eurusd(start_date, end_date, use_cache, force_refresh, tf="M15")


def load_eurusd_h1(
  start_date: str | None = None,
  end_date: str | None = None,
  use_cache: bool = True,
  force_refresh: bool = False,
) -> pd.DataFrame:
  return load_eurusd(start_date, end_date, use_cache, force_refresh, tf="H1")


def get_train_window_indices(
  df: pd.DataFrame,
  as_of: pd.Timestamp,
  length: int = 3,
  *,
  train_unit: str | None = None,
  tf: str | None = None,
  weeks: int | None = None,
  months: int | None = None,
):
  """Return (start_idx, end_idx) for training window ending at as_of (exclusive).

  Back-compat: ``weeks=`` / ``months=`` kwargs still work.
  """
  if weeks is not None:
    train_unit, length = "weeks", int(weeks)
  elif months is not None:
    train_unit, length = "months", int(months)
  elif train_unit is None:
    d = get_tf_defaults(str(tf or get_active_tf()).upper())
    train_unit, length = d.train_unit, int(length or d.train_length)

  if train_unit == "months":
    train_start = as_of - pd.DateOffset(months=int(length))
  else:
    train_start = as_of - pd.Timedelta(weeks=int(length))

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
