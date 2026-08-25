"""EA positions.json ↔ App journal sync (open fields + import)."""
from __future__ import annotations

from pathlib import Path

from mt5_bridge.protocol import atomic_write_json, connection_path, positions_path
from mt5_bridge.trade_journal import (
  clear_trades,
  load_trades,
  reconcile_journal_from_ea_positions,
  save_trades,
  sync_open_positions_from_ea,
)


def test_sync_open_updates_sl_tp_from_mt5(tmp_path: Path):
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "t1", "signal_id": "s1", "status": "OPEN", "mode": "auto",
      "model_id": "tm_a", "magic": 20261021, "ticket": 1001,
      "direction": "BUY", "entry_px": 1.1000, "sl": 1.0990, "tp": 1.1020,
    },
  ], tmp_path)
  atomic_write_json(connection_path(tmp_path), {"positions": 1, "connected": True})
  atomic_write_json(positions_path(tmp_path), {
    "n": 1,
    "positions": [{
      "ticket": 1001,
      "magic": 20261021,
      "model_id": "tm_a",
      "type": "BUY",
      "price_open": 1.1000,
      "sl": 1.0985,
      "tp": 1.1030,
      "volume": 0.1,
    }],
  })
  out = sync_open_positions_from_ea(tmp_path)
  assert out["updated"] == 1
  row = load_trades(tmp_path)[0]
  assert float(row["sl"]) == 1.0985
  assert float(row["tp"]) == 1.1030


def test_reconcile_wrapper_imports_orphan(tmp_path: Path):
  clear_trades(tmp_path)
  (tmp_path / "models.json").write_text('{"models":[{"magic":20261022}]}', encoding="utf-8")
  atomic_write_json(connection_path(tmp_path), {"positions": 1, "connected": True})
  atomic_write_json(positions_path(tmp_path), {
    "n": 1,
    "positions": [{
      "ticket": 2002,
      "magic": 20261022,
      "model_id": "tm_b",
      "type": "SELL",
      "price_open": 1.2,
      "sl": 1.21,
      "tp": 1.18,
      "volume": 0.05,
    }],
  })
  out = reconcile_journal_from_ea_positions(tmp_path, require_fresh_heartbeat=False)
  assert out["imported"] == 1
  assert load_trades(tmp_path)[0]["ticket"] == 2002
