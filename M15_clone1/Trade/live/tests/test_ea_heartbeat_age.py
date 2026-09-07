"""EA online must use connection.json mtime, not candle bar_time."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))

from deploy_ea import book_ea_status  # noqa: E402


def _write(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data), encoding="utf-8")


def test_stale_connection_is_offline_even_if_bar_time_looks_now(tmp_path):
  bdir = tmp_path / "bridge_live_eurusd_m15"
  conn = bdir / "connection.json"
  _write(conn, {"symbol": "EURUSD", "period": "M15", "connected": True})
  _write(bdir / "bar.json", {
    "symbol": "EURUSD",
    "period": "M15",
    "time": "2099.01.01 00:00",
    "bar_time": "2099.01.01 00:00",
  })
  stale = time.time() - 600
  os.utime(conn, (stale, stale))
  st = book_ea_status(
    {"symbol": "EURUSD", "timeframe": "M15", "bridge_dir": bdir},
    stale_after=45.0,
  )
  assert st["online"] is False
  assert st["age_sec"] is not None and st["age_sec"] > 45


def test_fresh_connection_is_online(tmp_path):
  bdir = tmp_path / "bridge_live_eurusd_m15"
  _write(bdir / "connection.json", {
    "symbol": "EURUSD", "period": "M15", "connected": True,
  })
  st = book_ea_status(
    {"symbol": "EURUSD", "timeframe": "M15", "bridge_dir": bdir},
    stale_after=45.0,
  )
  assert st["online"] is True
  assert st["age_sec"] is not None and st["age_sec"] < 45
