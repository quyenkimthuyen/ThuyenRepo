"""Position sync — ported from Trade (deals.json, awaiting_mt5_deal)."""
from __future__ import annotations

import json
from pathlib import Path

from mt5_bridge.position_sync import (
  _apply_close_from_fill,
  _matching_close_fill,
  is_history_paper_ticket,
  reconcile_bridge_positions,
)
from mt5_bridge.protocol import atomic_write_json, connection_path, deals_path, positions_path
from mt5_bridge.trade_journal import clear_trades, load_trades, save_trades


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
  atomic_write_json(positions_path(tmp_path), {"positions": [], "n": 0})
  atomic_write_json(deals_path(tmp_path), {"deals": []})
  save_trades([{
    "status": "OPEN",
    "ticket": 948277413,
    "magic": 20263004,
    "direction": "SELL",
    "entry_px": 1.3554,
    "sl": 1.35578,
    "sl_initial": 1.35578,
    "lots": 0.26,
    "signal_id": "abc",
  }], tmp_path)
  out = reconcile_bridge_positions(tmp_path, reason="ea_reconnect_reconcile")
  assert out["closed"] == 0
  assert out["awaiting"] == 1
  t = load_trades(tmp_path)[0]
  assert t["status"] == "OPEN"
  assert "awaiting_mt5_deal" in t.get("interventions", [])


def test_reconcile_closes_from_mt5_deal(tmp_path: Path):
  (tmp_path / "models.json").write_text(
    json.dumps({"models": [{"magic": 20263004}]}), encoding="utf-8",
  )
  atomic_write_json(positions_path(tmp_path), {"positions": [], "n": 0})
  atomic_write_json(deals_path(tmp_path), {
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
  })
  save_trades([{
    "status": "OPEN",
    "ticket": 948277413,
    "magic": 20263004,
    "direction": "SELL",
    "entry_px": 1.3554,
    "sl": 1.35578,
    "sl_initial": 1.35578,
    "lots": 0.26,
    "signal_id": "abc",
  }], tmp_path)
  out = reconcile_bridge_positions(tmp_path, reason="ea_reconnect_reconcile")
  assert out["closed"] == 1
  t = load_trades(tmp_path)[0]
  assert t["status"] == "CLOSED"
  assert t["result"] == "LOSS"
  assert t["profit"] == -9.88
  assert "mt5_deal" in t.get("interventions", [])


def test_history_paper_ticket_range():
  assert is_history_paper_ticket(700000)
  assert not is_history_paper_ticket(956252722)


def test_reconcile_clears_stale_awaiting_when_mt5_has_position(tmp_path: Path):
  (tmp_path / "models.json").write_text(
    json.dumps({"models": [{"magic": 20281044}]}), encoding="utf-8",
  )
  atomic_write_json(positions_path(tmp_path), {
    "positions": [{
      "ticket": 964538664,
      "magic": 20281044,
      "model_id": "tm_edge",
    }],
    "n": 1,
  })
  atomic_write_json(deals_path(tmp_path), {"deals": []})
  save_trades([{
    "status": "OPEN",
    "ticket": 964538664,
    "magic": 20281044,
    "direction": "SELL",
    "entry_px": 1.35973,
    "sl": 1.36042,
    "interventions": ["awaiting_mt5_deal"],
  }], tmp_path)
  out = reconcile_bridge_positions(tmp_path, reason="ea_reconnect_reconcile")
  assert out["closed"] == 0
  assert out["awaiting"] == 0
  t = load_trades(tmp_path)[0]
  assert t["status"] == "OPEN"
  assert "awaiting_mt5_deal" not in (t.get("interventions") or [])


def test_reconcile_leaves_history_paper_open(tmp_path: Path):
  (tmp_path / "models.json").write_text(
    json.dumps({"models": [{"magic": 20263010}]}), encoding="utf-8",
  )
  atomic_write_json(positions_path(tmp_path), {"positions": [], "n": 0})
  atomic_write_json(deals_path(tmp_path), {"deals": []})
  save_trades([{
    "status": "OPEN",
    "ticket": 700015,
    "magic": 20263010,
    "direction": "SELL",
    "entry_px": 1.36476,
    "sl": 1.36542,
    "sl_initial": 1.36542,
    "signal_id": "paper-sid",
  }], tmp_path)
  out = reconcile_bridge_positions(tmp_path, reason="ea_reconnect_reconcile")
  assert out["closed"] == 0
  assert load_trades(tmp_path)[0]["status"] == "OPEN"
