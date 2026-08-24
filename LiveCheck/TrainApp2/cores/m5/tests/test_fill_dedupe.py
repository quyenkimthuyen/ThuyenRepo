"""HistoryFeed / Live sticky fill.json must not duplicate journal rows."""
from __future__ import annotations

from pathlib import Path

from mt5_bridge.trade_journal import dedupe_trades, load_trades, process_fill


def test_repeated_close_does_not_duplicate(tmp_path: Path) -> None:
  open_fill = {
    "ok": True,
    "event": "open",
    "action": "SELL",
    "ticket": 700049,
    "signal_id": "sig_a",
    "price": 1.17985,
    "sl": 1.18046,
    "tp": 1.1761,
    "lots": 0.1,
    "bar_time": "2026.02.20 17:30",
  }
  close_fill = {
    "ok": True,
    "event": "close",
    "action": "SELL",
    "ticket": 700049,
    "signal_id": "sig_a",
    "price": 1.18046,
    "sl": 1.18046,
    "tp": 1.1761,
    "lots": 0.1,
    "profit": -1.0,
    "reason": "sl",
    "bar_time": "2026.02.23 01:00",
  }
  process_fill(open_fill, bridge_dir=tmp_path)
  for _ in range(40):
    process_fill(close_fill, bridge_dir=tmp_path)
  trades = load_trades(tmp_path)
  assert len(trades) == 1
  assert trades[0]["status"] == "CLOSED"
  assert trades[0]["r"] == -1.0


def test_live_sticky_close_across_restarts(tmp_path: Path) -> None:
  """Live service restart re-reads fill.json — must stay one CLOSED row."""
  close = {
    "ok": True,
    "event": "close",
    "action": "SELL",
    "ticket": 923367630,
    "signal_id": "manual_test_x",
    "price": 1.13712,
    "sl": 1.13892,
    "tp": 1.13292,
    "lots": 0.1,
    "profit": -0.48,
    "reason": "ea_close",
    "time": "2026.07.24 15:39:54",
    "manual": True,
  }
  for _ in range(6):
    process_fill(close, bridge_dir=tmp_path)
  assert len(load_trades(tmp_path)) == 1
  # Sticky open for same ticket after close must not create a second row
  process_fill(
    {
      "ok": True,
      "event": "open",
      "action": "SELL",
      "ticket": 923367630,
      "signal_id": "manual_test_x",
      "price": 1.1375,
      "sl": 1.13892,
      "tp": 1.13292,
      "lots": 0.1,
      "time": "2026.07.24 15:30:00",
    },
    bridge_dir=tmp_path,
  )
  assert len(load_trades(tmp_path)) == 1


def test_dedupe_collapses_same_ticket() -> None:
  rows = [
    {"id": "bt_close_1", "ticket": 1, "status": "CLOSED", "r": -1.0},
    {"id": "bt_close_1", "ticket": 1, "status": "CLOSED", "r": -1.0},
    {"id": "bt_close_1", "ticket": 1, "status": "CLOSED", "r": -1.0},
  ]
  out = dedupe_trades(rows)
  assert len(out) == 1


def test_noop_user_sl_tp_keeps_auto(tmp_path: Path) -> None:
  from mt5_bridge.trade_journal import trade_mode

  process_fill(
    {
      "ok": True,
      "event": "open",
      "action": "SELL",
      "ticket": 1,
      "signal_id": "sig_auto",
      "price": 1.16723,
      "sl": 1.16768,
      "tp": 1.16561,
      "lots": 0.14,
      "source": "strategy",
    },
    bridge_dir=tmp_path,
    model_id="m1",
  )
  process_fill(
    {
      "ok": True,
      "event": "modify",
      "action": "SELL",
      "ticket": 1,
      "signal_id": "sig_auto",
      "sl": 1.16768,
      "tp": 1.16561,
      "lots": 0.14,
      "detail": "user_sl_tp",
      "reason": "user_sl_tp",
      "manual": True,
      "source": "user_edit",
    },
    bridge_dir=tmp_path,
  )
  row = load_trades(tmp_path)[0]
  assert trade_mode(row) == "auto"
  assert row["origin"] == "strategy"


def test_real_user_sl_tp_marks_manual(tmp_path: Path) -> None:
  from mt5_bridge.trade_journal import trade_mode

  process_fill(
    {
      "ok": True,
      "event": "open",
      "action": "SELL",
      "ticket": 2,
      "signal_id": "sig_auto2",
      "price": 1.16723,
      "sl": 1.16768,
      "tp": 1.16561,
      "lots": 0.14,
      "source": "strategy",
    },
    bridge_dir=tmp_path,
    model_id="m1",
  )
  process_fill(
    {
      "ok": True,
      "event": "modify",
      "action": "SELL",
      "ticket": 2,
      "signal_id": "sig_auto2",
      "sl": 1.16790,
      "tp": 1.16561,
      "detail": "user_sl_tp",
      "manual": True,
      "source": "user_edit",
    },
    bridge_dir=tmp_path,
  )
  row = load_trades(tmp_path)[0]
  assert trade_mode(row) == "manual"
  assert "user_sl_tp" in row["interventions"]


def test_restore_false_manual_edits(tmp_path: Path) -> None:
  from mt5_bridge.trade_journal import restore_false_manual_edits, save_trades, trade_mode

  save_trades(
    [
      {
        "id": "bt_1",
        "signal_id": "abc",
        "status": "OPEN",
        "mode": "manual",
        "origin": "strategy",
        "intervened": True,
        "interventions": ["user_sl_tp"],
        "sl": 1.16772,
        "tp": 1.16588,
        "sl_initial": 1.16772,
        "tp_initial": 1.16588,
        "model_id": "m1",
      },
      {
        "id": "bt_2",
        "signal_id": "manual_test_x",
        "status": "CLOSED",
        "mode": "manual",
        "origin": "manual_test",
        "interventions": ["manual_test_open"],
        "sl": 1.1,
        "tp": 1.0,
        "sl_initial": 1.1,
        "tp_initial": 1.0,
      },
    ],
    tmp_path,
  )
  n = restore_false_manual_edits(tmp_path)
  assert n == 1
  trades = load_trades(tmp_path)
  by_id = {t["id"]: t for t in trades}
  assert trade_mode(by_id["bt_1"]) == "auto"
  assert trade_mode(by_id["bt_2"]) == "manual"
