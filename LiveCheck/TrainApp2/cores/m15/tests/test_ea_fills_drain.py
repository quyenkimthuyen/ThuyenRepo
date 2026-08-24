"""Atomic ea_fills drain must not drop fills appended during read."""
from __future__ import annotations

import json
from pathlib import Path

from mt5_bridge.trade_journal import (
  close_ghost_journal_opens,
  drain_ea_fills_queue,
  load_trades,
  reconcile_ghost_opens_if_ea_flat,
  save_trades,
)


def test_drain_rename_keeps_all_lines(tmp_path: Path):
  q = tmp_path / "ea_fills.jsonl"
  rows = [
    {"event": "close", "ticket": 1, "signal_id": "a"},
    {"event": "close", "ticket": 2, "signal_id": "b"},
    {"event": "close", "ticket": 3, "signal_id": "c"},
  ]
  q.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
  got = drain_ea_fills_queue(tmp_path)
  assert [g["ticket"] for g in got] == [1, 2, 3]
  assert not q.exists() or q.stat().st_size == 0


def test_close_ghost_opens_unblocks_journal(tmp_path: Path):
  save_trades(
    [
      {
        "id": "bt_1",
        "signal_id": "s1",
        "status": "OPEN",
        "direction": "SELL",
        "entry_px": 1.3,
        "model_id": "m1",
      },
      {
        "id": "bt_2",
        "signal_id": "s2",
        "status": "CLOSED",
        "direction": "BUY",
        "entry_px": 1.2,
        "exit_px": 1.21,
        "r": 1.0,
        "result": "WIN",
        "model_id": "m1",
      },
    ],
    tmp_path,
  )
  n = close_ghost_journal_opens(tmp_path, reason="sim_end_reconcile")
  assert n == 1
  trades = load_trades(tmp_path)
  opens = [t for t in trades if t.get("status") == "OPEN"]
  closed_ghost = next(t for t in trades if t.get("signal_id") == "s1")
  assert opens == []
  assert closed_ghost["status"] == "CLOSED"
  assert closed_ghost["reason"] == "sim_end_reconcile"
  assert "journal_desync" in closed_ghost.get("interventions", [])


def _open_row() -> dict:
  return {
    "id": "bt_1",
    "signal_id": "s1",
    "status": "OPEN",
    "direction": "SELL",
    "entry_px": 1.3,
    "model_id": "m1",
  }


def test_reconcile_ghost_opens_when_ea_flat(tmp_path: Path):
  from mt5_bridge.protocol import atomic_write_json, connection_path

  save_trades([_open_row()], tmp_path)
  atomic_write_json(connection_path(tmp_path), {"positions": 0, "connected": True})
  n = reconcile_ghost_opens_if_ea_flat(tmp_path)
  assert n == 1
  assert load_trades(tmp_path)[0]["status"] == "CLOSED"


def test_reconcile_skips_when_mt5_has_positions(tmp_path: Path):
  from mt5_bridge.protocol import atomic_write_json, connection_path

  save_trades([_open_row()], tmp_path)
  atomic_write_json(connection_path(tmp_path), {"positions": 2, "connected": True})
  assert reconcile_ghost_opens_if_ea_flat(tmp_path) == 0
  assert load_trades(tmp_path)[0]["status"] == "OPEN"


def test_reconcile_skips_stale_heartbeat_unless_user_confirms(tmp_path: Path):
  import os
  import time

  from mt5_bridge.protocol import atomic_write_json, connection_path

  save_trades([_open_row()], tmp_path)
  path = connection_path(tmp_path)
  atomic_write_json(path, {"positions": 0, "connected": True})
  old = time.time() - 60
  os.utime(path, (old, old))
  assert reconcile_ghost_opens_if_ea_flat(tmp_path, require_fresh_heartbeat=True) == 0
  assert load_trades(tmp_path)[0]["status"] == "OPEN"
  assert reconcile_ghost_opens_if_ea_flat(tmp_path, require_fresh_heartbeat=False) == 1
  assert load_trades(tmp_path)[0]["status"] == "CLOSED"
