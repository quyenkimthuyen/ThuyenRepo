"""Reconcile must close from MT5 OUT deals, not invent SL/BE."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from position_sync import (  # noqa: E402
  _apply_close_from_fill,
  _matching_close_fill,
  reconcile_bridge_positions,
)


def test_match_close_by_ticket_not_foreign_signal(tmp_path: Path):
  (tmp_path / "fill.json").write_text(
    json.dumps({
      "event": "close",
      "ticket": 111,
      "signal_id": "sid-of-other",
      "price": 1.35614,
      "profit": -9.84,
      "reason": "sl",
    }),
    encoding="utf-8",
  )
  got = _matching_close_fill(tmp_path, ticket=222, signal_id="sid-of-other")
  assert got is None
  got_ok = _matching_close_fill(tmp_path, ticket=111, signal_id="anything")
  assert got_ok is not None
  assert got_ok["ticket"] == 111


def test_apply_close_aligns_r_when_profit_is_loss():
  trade = {
    "direction": "SELL",
    "entry_px": 1.35644,
    "sl_initial": 1.35687,
    "sl": 1.35687,
    "lots": 0.22,
  }
  fill = {
    "event": "close",
    "price": 1.35614,
    "profit": -9.84,
    "reason": "sl",
    "sl": 1.35687,
    "action": "SELL",
  }
  _apply_close_from_fill(trade, fill, now="2026-08-17T14:00:00+07:00")
  assert trade["result"] == "LOSS"
  assert float(trade["r"]) < 0


def test_reconcile_without_deal_leaves_open(tmp_path: Path):
  (tmp_path / "models.json").write_text(
    json.dumps({"models": [{"magic": 20263004}]}), encoding="utf-8",
  )
  (tmp_path / "positions.json").write_text(
    json.dumps({"positions": []}), encoding="utf-8",
  )
  (tmp_path / "deals.json").write_text(json.dumps({"deals": []}), encoding="utf-8")
  (tmp_path / "trades.json").write_text(
    json.dumps({
      "trades": [{
        "status": "OPEN",
        "ticket": 948277413,
        "magic": 20263004,
        "direction": "SELL",
        "entry_px": 1.3554,
        "sl": 1.35578,
        "sl_initial": 1.35578,
        "lots": 0.26,
        "signal_id": "abc",
      }],
    }),
    encoding="utf-8",
  )
  out = reconcile_bridge_positions(tmp_path, reason="ea_reconnect_reconcile")
  assert out["closed"] == 0
  assert out["awaiting"] == 1
  trades = json.loads((tmp_path / "trades.json").read_text(encoding="utf-8"))["trades"]
  t = trades[0]
  assert t["status"] == "OPEN"
  assert "awaiting_mt5_deal" in t.get("interventions", [])


def test_reconcile_closes_from_mt5_deal(tmp_path: Path):
  (tmp_path / "models.json").write_text(
    json.dumps({"models": [{"magic": 20263004}]}), encoding="utf-8",
  )
  (tmp_path / "positions.json").write_text(
    json.dumps({"positions": []}), encoding="utf-8",
  )
  (tmp_path / "deals.json").write_text(
    json.dumps({
      "deals": [{
        "deal": 99,
        "position_id": 948277413,
        "ticket": 948277413,
        "magic": 20263004,
        "type": "SELL",
        "volume": 0.26,
        "price": 1.35578,
        "profit": -9.88,
        "reason": "sl",
        "time": "2026.08.17 08:49:03",
      }],
    }),
    encoding="utf-8",
  )
  (tmp_path / "trades.json").write_text(
    json.dumps({
      "trades": [{
        "status": "OPEN",
        "ticket": 948277413,
        "magic": 20263004,
        "direction": "SELL",
        "entry_px": 1.3554,
        "sl": 1.35578,
        "sl_initial": 1.35578,
        "lots": 0.26,
        "signal_id": "abc",
      }],
    }),
    encoding="utf-8",
  )
  out = reconcile_bridge_positions(tmp_path, reason="ea_reconnect_reconcile")
  assert out["closed"] == 1
  trades = json.loads((tmp_path / "trades.json").read_text(encoding="utf-8"))["trades"]
  t = trades[0]
  assert t["status"] == "CLOSED"
  assert t["result"] == "LOSS"
  assert t["profit"] == -9.88
  assert t["exit_px"] == 1.35578
  assert "mt5_deal" in t.get("interventions", [])
  assert "sl_assumed" not in t.get("interventions", [])


def test_reconcile_repairs_closed_be_from_deal(tmp_path: Path):
  (tmp_path / "models.json").write_text(
    json.dumps({"models": [{"magic": 20263004}]}), encoding="utf-8",
  )
  (tmp_path / "positions.json").write_text(
    json.dumps({"positions": []}), encoding="utf-8",
  )
  (tmp_path / "deals.json").write_text(
    json.dumps({
      "deals": [{
        "position_id": 948277413,
        "ticket": 948277413,
        "price": 1.35578,
        "profit": -9.91,
        "reason": "sl",
        "volume": 0.26,
        "type": "SELL",
      }],
    }),
    encoding="utf-8",
  )
  (tmp_path / "trades.json").write_text(
    json.dumps({
      "trades": [{
        "status": "CLOSED",
        "ticket": 948277413,
        "magic": 20263004,
        "direction": "SELL",
        "entry_px": 1.3554,
        "exit_px": 1.3554,
        "sl": 1.35578,
        "sl_initial": 1.35578,
        "lots": 0.26,
        "r": 0.0,
        "result": "BE",
        "profit": None,
        "reason": "ea_reconnect_reconcile",
        "interventions": ["journal_desync"],
      }],
    }),
    encoding="utf-8",
  )
  out = reconcile_bridge_positions(tmp_path)
  assert out["repaired"] == 1
  t = json.loads((tmp_path / "trades.json").read_text(encoding="utf-8"))["trades"][0]
  assert t["result"] == "LOSS"
  assert t["profit"] == -9.91
  assert t["exit_px"] == 1.35578


def test_reconcile_repairs_when_deal_profit_differs(tmp_path: Path):
  (tmp_path / "models.json").write_text(
    json.dumps({"models": [{"magic": 20263007}]}), encoding="utf-8",
  )
  (tmp_path / "positions.json").write_text(json.dumps({"positions": []}), encoding="utf-8")
  (tmp_path / "deals.json").write_text(
    json.dumps({
      "deals": [{
        "position_id": 948475011,
        "ticket": 948475011,
        "price": 1.35598,
        "profit": -10.32,
        "reason": "sl",
        "volume": 0.24,
        "type": "SELL",
      }],
    }),
    encoding="utf-8",
  )
  (tmp_path / "trades.json").write_text(
    json.dumps({
      "trades": [{
        "status": "CLOSED",
        "ticket": 948475011,
        "magic": 20263007,
        "direction": "SELL",
        "entry_px": 1.35555,
        "exit_px": 1.35578,
        "sl": 1.35596,
        "sl_initial": 1.35596,
        "lots": 0.24,
        "r": -0.561,
        "result": "LOSS",
        "profit": -9.88,
        "reason": "sl",
      }],
    }),
    encoding="utf-8",
  )
  out = reconcile_bridge_positions(tmp_path)
  assert out["repaired"] == 1
  t = json.loads((tmp_path / "trades.json").read_text(encoding="utf-8"))["trades"][0]
  assert t["profit"] == -10.32
  assert t["exit_px"] == 1.35598
  assert t["result"] == "LOSS"
