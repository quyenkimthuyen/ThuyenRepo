"""Resumable MT5 M15 history synchronization through ForgeBridge files."""
from __future__ import annotations

import os
import hashlib
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from mt5_bridge.protocol import (
  BRIDGE_DIR,
  atomic_write_json,
  history_ack_path,
  history_chunk_path,
  history_request_path,
  history_status_path,
  read_json,
  utc_now_iso,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MT5_CACHE_PATH = DATA_DIR / "mt5_eurusd_m15.parquet"
MT5_META_PATH = DATA_DIR / "mt5_eurusd_m15_meta.json"
BROKER_TIMEZONE = os.environ.get("EDGEMINER_BROKER_TIMEZONE", "Europe/Helsinki")
DATA_START_BROKER = "2025-01-01 00:00"
DEFAULT_CHUNK_SIZE = 750
_store_lock = threading.RLock()


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


def normalize_mt5_bars(bars: list[dict]) -> pd.DataFrame:
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
  return frame.loc[frame.index >= parse_broker_time(DATA_START_BROKER)]


def load_mt5_cache() -> pd.DataFrame | None:
  if not MT5_CACHE_PATH.exists():
    return None
  frame = pd.read_parquet(MT5_CACHE_PATH)
  frame.index = pd.to_datetime(frame.index, utc=True).tz_convert(None)
  frame = frame.sort_index()[~frame.index.duplicated(keep="last")]
  return frame.loc[frame.index >= parse_broker_time(DATA_START_BROKER)]


def _write_cache(frame: pd.DataFrame, source: dict) -> None:
  DATA_DIR.mkdir(parents=True, exist_ok=True)
  tmp = MT5_CACHE_PATH.with_suffix(".parquet.tmp")
  frame.to_parquet(tmp)
  tmp.replace(MT5_CACHE_PATH)
  diffs = frame.index.to_series().diff().dropna()
  gaps = int(((diffs > pd.Timedelta(minutes=15)) & (diffs < pd.Timedelta(hours=48))).sum())
  fingerprint = hashlib.sha256(
    pd.util.hash_pandas_object(frame, index=True).values.tobytes(),
  ).hexdigest()
  previous = read_json(MT5_META_PATH) or {}
  source = {**previous, **{k: v for k, v in source.items() if v is not None}}
  atomic_write_json(MT5_META_PATH, {
    "source": "mt5_ea",
    "broker": source.get("server") or source.get("broker"),
    "account": source.get("account"),
    "pair": source.get("symbol") or source.get("pair") or "EURUSD",
    "timeframe": "M15",
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


def merge_history_bars(bars: list[dict], source: dict | None = None) -> pd.DataFrame:
  incoming = normalize_mt5_bars(bars)
  with _store_lock:
    current = load_mt5_cache()
    if current is None or current.empty:
      merged = incoming
    elif incoming.empty:
      merged = current
    else:
      merged = pd.concat([current, incoming]).sort_index()
      merged = merged[~merged.index.duplicated(keep="last")]
    if not merged.empty:
      _write_cache(merged, source or {})
    return merged


def _new_request(offset: int, bridge_dir: Path, chunk_size: int) -> dict:
  request = {
    "request_id": uuid.uuid4().hex,
    "action": "export_m15_history",
    "symbol": "EURUSD",
    "period": "M15",
    "from_time": "2025.01.01 00:00",
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
  request = _new_request(0, bridge_dir, chunk_size)
  status = {
    "state": "requesting",
    "offset": 0,
    "received_bars": 0,
    "request_id": request["request_id"],
    "started_at": utc_now_iso(),
    "updated_at": utc_now_iso(),
    "error": None,
  }
  atomic_write_json(status_file, status)
  return status


def process_history_sync(
  bridge_dir: Path | None = None,
  *,
  chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> dict:
  """Consume at most one EA chunk and request the next one."""
  bridge_dir = bridge_dir or BRIDGE_DIR
  status_file = history_status_path(bridge_dir)
  status = read_json(status_file) or {}
  request = read_json(history_request_path(bridge_dir))
  if not isinstance(request, dict):
    return start_history_sync(bridge_dir, chunk_size=chunk_size)

  chunk = read_json(history_chunk_path(bridge_dir))
  if not isinstance(chunk, dict) or chunk.get("request_id") != request.get("request_id"):
    status.update(state="requesting", updated_at=utc_now_iso())
    atomic_write_json(status_file, status)
    return status
  if status.get("processed_request_id") == chunk.get("request_id"):
    return status

  bars = chunk.get("bars") if isinstance(chunk.get("bars"), list) else []
  frame = merge_history_bars(bars, chunk)
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
  })
  if not chunk.get("done"):
    next_request = _new_request(next_offset, bridge_dir, chunk_size)
    status["request_id"] = next_request["request_id"]
  atomic_write_json(status_file, status)
  return status


def get_history_status(bridge_dir: Path | None = None) -> dict:
  status = read_json(history_status_path(bridge_dir or BRIDGE_DIR)) or {"state": "idle"}
  meta = read_json(MT5_META_PATH) or {}
  return {**status, "data": meta}
