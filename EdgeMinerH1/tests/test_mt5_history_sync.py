from __future__ import annotations

import pandas as pd

from mt5_bridge import history_sync
from mt5_bridge.engine import _fmt_bar
from mt5_bridge.protocol import atomic_write_json, history_chunk_path, read_json


def _bar(time: str, close: float = 1.1) -> dict:
  return {
    "time": time,
    "open": close - 0.001,
    "high": close + 0.001,
    "low": close - 0.002,
    "close": close,
    "tick_volume": 100,
  }


def _temp_store(tmp_path, monkeypatch):
  monkeypatch.setattr(history_sync, "MT5_CACHE_PATH", tmp_path / "mt5.parquet")
  monkeypatch.setattr(history_sync, "MT5_META_PATH", tmp_path / "meta.json")


def test_broker_time_is_normalized_with_dst():
  winter = history_sync.parse_broker_time("2026.01.15 10:00")
  summer = history_sync.parse_broker_time("2026.07.15 10:00")
  assert winter == pd.Timestamp("2026-01-15 08:00:00")
  assert summer == pd.Timestamp("2026-07-15 07:00:00")
  assert _fmt_bar(summer) == "2026.07.15 10:00"


def test_merge_history_deduplicates_and_overwrites(tmp_path, monkeypatch):
  _temp_store(tmp_path, monkeypatch)
  history_sync.merge_history_bars([_bar("2026.07.15 10:00", 1.1)])
  frame = history_sync.merge_history_bars([_bar("2026.07.15 10:00", 1.2)])
  assert len(frame) == 1
  assert frame.iloc[0]["Close"] == 1.2
  assert read_json(history_sync.MT5_META_PATH)["source"] == "mt5_ea"


def test_chunk_protocol_resumes_until_done(tmp_path, monkeypatch):
  _temp_store(tmp_path, monkeypatch)
  bridge = tmp_path / "bridge"
  status = history_sync.start_history_sync(bridge, chunk_size=2)
  request = read_json(history_sync.history_request_path(bridge))
  atomic_write_json(history_chunk_path(bridge), {
    "request_id": request["request_id"],
    "symbol": "EURUSD",
    "server": "XMGlobal-MT5",
    "offset": 0,
    "next_offset": 2,
    "available_bars": 3,
    "done": False,
    "bars": [_bar("2026.07.15 10:00"), _bar("2026.07.15 11:00")],
  })
  status = history_sync.process_history_sync(bridge, chunk_size=2)
  assert status["state"] == "receiving"
  assert status["received_bars"] == 2

  request = read_json(history_sync.history_request_path(bridge))
  atomic_write_json(history_chunk_path(bridge), {
    "request_id": request["request_id"],
    "symbol": "EURUSD",
    "server": "XMGlobal-MT5",
    "offset": 2,
    "next_offset": 3,
    "available_bars": 3,
    "done": True,
    "bars": [_bar("2026.07.15 12:00")],
  })
  status = history_sync.process_history_sync(bridge, chunk_size=2)
  assert status["state"] == "completed"
  assert status["received_bars"] == 3
  assert len(history_sync.load_mt5_cache()) == 3
