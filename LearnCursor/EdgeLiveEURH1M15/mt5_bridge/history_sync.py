"""Resumable MT5 history synchronization through ForgeBridge files (H1 + M15)."""
from __future__ import annotations

import os
import hashlib
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from config import get_active_tf
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  atomic_write_json,
  safe_replace,
  history_ack_path,
  history_chunk_path,
  history_request_path,
  history_status_path,
  read_json,
  utc_now_iso,
)
from runtime_profiles import get_tf_defaults

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BROKER_TIMEZONE = os.environ.get("EDGEMINER_BROKER_TIMEZONE", "Europe/Helsinki")
DEFAULT_CHUNK_SIZE = 750
_store_lock = threading.RLock()


def _tf(tf: str | None = None) -> str:
  return str(tf or get_active_tf()).upper()


def cache_path_for(tf: str | None = None) -> Path:
  return get_tf_defaults(_tf(tf)).cache_parquet


def cache_meta_for(tf: str | None = None) -> Path:
  return get_tf_defaults(_tf(tf)).cache_meta


# Back-compat module aliases (resolve for active TF at access time via functions;
# static defaults point at M15 for import-time Path comparisons).
MT5_CACHE_PATH = get_tf_defaults("M15").cache_parquet
MT5_META_PATH = get_tf_defaults("M15").cache_meta
DATA_START_BROKER = get_tf_defaults("M15").data_start_broker


def parse_broker_time(value) -> pd.Timestamp:
  """Convert an MT5 broker wall-clock timestamp to UTC-naive."""
  ts = pd.Timestamp(value)
  if ts.tzinfo is None:
    ts = ts.tz_localize(
      ZoneInfo(BROKER_TIMEZONE), ambiguous=True, nonexistent="shift_forward",
    )
  return ts.tz_convert("UTC").tz_localize(None)


def utc_to_broker_time(value) -> pd.Timestamp:
  """Convert an internal UTC-naive timestamp to MT5 broker wall-clock."""
  ts = pd.Timestamp(value)
  if ts.tzinfo is None:
    ts = ts.tz_localize("UTC")
  return ts.tz_convert(ZoneInfo(BROKER_TIMEZONE)).tz_localize(None)


def normalize_mt5_bars(bars: list[dict], *, tf: str | None = None) -> pd.DataFrame:
  d = get_tf_defaults(_tf(tf))
  rows: list[dict] = []
  index: list[pd.Timestamp] = []
  for bar in bars:
    try:
      index.append(parse_broker_time(bar.get("time") or bar.get("bar_time")))
      rows.append({
        "Open": float(bar["open"]),
        "High": float(bar["high"]),
        "Low": float(bar["low"]),
        "Close": float(bar["close"]),
        "Volume": float(bar.get("volume") or bar.get("tick_volume") or 0),
      })
    except (KeyError, TypeError, ValueError):
      continue
  if not rows:
    return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
  frame = pd.DataFrame(rows, index=pd.DatetimeIndex(index))
  frame = frame.sort_index()
  frame = frame[~frame.index.duplicated(keep="last")]
  valid = (
    (frame["High"] >= frame[["Open", "Close", "Low"]].max(axis=1))
    & (frame["Low"] <= frame[["Open", "Close", "High"]].min(axis=1))
  )
  frame = frame.loc[valid].dropna()
  return frame.loc[frame.index >= parse_broker_time(d.data_start_broker)]


def load_mt5_cache(tf: str | None = None) -> pd.DataFrame | None:
  d = get_tf_defaults(_tf(tf))
  path = d.cache_parquet
  if not path.exists():
    return None
  frame = pd.read_parquet(path)
  frame.index = pd.to_datetime(frame.index, utc=True).tz_convert(None)
  frame = frame.sort_index()[~frame.index.duplicated(keep="last")]
  return frame.loc[frame.index >= parse_broker_time(d.data_start_broker)]


def _write_cache(frame: pd.DataFrame, source: dict, *, tf: str | None = None) -> None:
  d = get_tf_defaults(_tf(tf))
  DATA_DIR.mkdir(parents=True, exist_ok=True)
  path = d.cache_parquet
  meta_path = d.cache_meta
  tmp = path.with_suffix(".parquet.tmp")
  frame.to_parquet(tmp)
  safe_replace(tmp, path)
  diffs = frame.index.to_series().diff().dropna()
  gap = pd.Timedelta(minutes=d.bar_minutes)
  gaps = int(((diffs > gap) & (diffs < pd.Timedelta(hours=48))).sum())
  fingerprint = hashlib.sha256(
    pd.util.hash_pandas_object(frame, index=True).values.tobytes(),
  ).hexdigest()
  previous = read_json(meta_path) or {}
  source = {**previous, **{k: v for k, v in source.items() if v is not None}}
  atomic_write_json(meta_path, {
    "source": "mt5_ea",
    "broker": source.get("server") or source.get("broker"),
    "account": source.get("account"),
    "pair": source.get("symbol") or source.get("pair") or "EURUSD",
    "timeframe": d.tf,
    "broker_timezone": BROKER_TIMEZONE,
    "bars": len(frame),
    "start": str(frame.index[0]) if len(frame) else None,
    "end": str(frame.index[-1]) if len(frame) else None,
    "gap_count": gaps,
    "fingerprint": fingerprint,
    "synced_at": utc_now_iso(),
  })
  try:
    from strategy_miner import notify_data_updated
    notify_data_updated(len(frame))
  except Exception:
    pass


def merge_history_bars(
  bars: list[dict],
  source: dict | None = None,
  *,
  tf: str | None = None,
) -> pd.DataFrame:
  incoming = normalize_mt5_bars(bars, tf=tf)
  with _store_lock:
    current = load_mt5_cache(tf)
    if current is None or current.empty:
      merged = incoming
    elif incoming.empty:
      merged = current
    else:
      merged = pd.concat([current, incoming]).sort_index()
      merged = merged[~merged.index.duplicated(keep="last")]
    if not merged.empty:
      _write_cache(merged, source or {}, tf=tf)
    return merged


def _new_request(offset: int, bridge_dir: Path, chunk_size: int, *, tf: str | None = None) -> dict:
  d = get_tf_defaults(_tf(tf))
  # from_time format: YYYY.MM.DD HH:MM
  from_time = d.data_start_broker.replace("-", ".")[:16]
  request = {
    "request_id": uuid.uuid4().hex,
    "action": d.history_action,
    "symbol": "EURUSD",
    "period": d.history_period,
    "from_time": from_time,
    "offset": int(offset),
    "chunk_size": int(chunk_size),
    "requested_at": utc_now_iso(),
  }
  atomic_write_json(history_request_path(bridge_dir), request)
  return request


def start_history_sync(
  bridge_dir: Path | None = None,
  *,
  force: bool = False,
  chunk_size: int = DEFAULT_CHUNK_SIZE,
  tf: str | None = None,
) -> dict:
  bridge_dir = bridge_dir or BRIDGE_DIR
  status_file = history_status_path(bridge_dir)
  status = read_json(status_file) or {}
  if status.get("state") in ("requesting", "receiving", "completed") and not force:
    return status
  if force:
    for path in (
      history_request_path(bridge_dir),
      history_chunk_path(bridge_dir),
      history_ack_path(bridge_dir),
    ):
      path.unlink(missing_ok=True)
  request = _new_request(0, bridge_dir, chunk_size, tf=tf)
  status = {
    "state": "requesting",
    "offset": 0,
    "received_bars": 0,
    "request_id": request["request_id"],
    "started_at": utc_now_iso(),
    "updated_at": utc_now_iso(),
    "error": None,
    "tf": _tf(tf),
  }
  atomic_write_json(status_file, status)
  return status


def process_history_sync(
  bridge_dir: Path | None = None,
  *,
  chunk_size: int = DEFAULT_CHUNK_SIZE,
  tf: str | None = None,
) -> dict:
  """Consume at most one EA chunk and request the next one."""
  bridge_dir = bridge_dir or BRIDGE_DIR
  status_file = history_status_path(bridge_dir)
  status = read_json(status_file) or {}
  tf = status.get("tf") or tf
  request = read_json(history_request_path(bridge_dir))
  if not isinstance(request, dict):
    return start_history_sync(bridge_dir, chunk_size=chunk_size, tf=tf)

  chunk = read_json(history_chunk_path(bridge_dir))
  if not isinstance(chunk, dict) or chunk.get("request_id") != request.get("request_id"):
    status.update(state="requesting", updated_at=utc_now_iso())
    atomic_write_json(status_file, status)
    return status
  if status.get("processed_request_id") == chunk.get("request_id"):
    return status

  bars = chunk.get("bars") if isinstance(chunk.get("bars"), list) else []
  frame = merge_history_bars(bars, chunk, tf=tf)
  next_offset = int(chunk.get("next_offset") or request.get("offset") or 0)
  received = int(status.get("received_bars") or 0) + len(bars)
  atomic_write_json(history_ack_path(bridge_dir), {
    "request_id": request["request_id"],
    "accepted_bars": len(bars),
    "next_offset": next_offset,
    "acknowledged_at": utc_now_iso(),
  })
  status.update({
    "state": "completed" if chunk.get("done") else "receiving",
    "offset": next_offset,
    "received_bars": received,
    "stored_bars": len(frame),
    "available_bars": int(chunk.get("available_bars") or 0),
    "processed_request_id": chunk.get("request_id"),
    "broker": chunk.get("server"),
    "symbol": chunk.get("symbol"),
    "updated_at": utc_now_iso(),
    "completed_at": utc_now_iso() if chunk.get("done") else None,
    "error": None,
    "tf": _tf(tf),
  })
  if not chunk.get("done"):
    next_request = _new_request(next_offset, bridge_dir, chunk_size, tf=tf)
    status["request_id"] = next_request["request_id"]
  atomic_write_json(status_file, status)
  return status


def get_history_status(bridge_dir: Path | None = None, *, tf: str | None = None) -> dict:
  status = read_json(history_status_path(bridge_dir or BRIDGE_DIR)) or {"state": "idle"}
  meta = read_json(cache_meta_for(status.get("tf") or tf)) or {}
  return {**status, "data": meta}
