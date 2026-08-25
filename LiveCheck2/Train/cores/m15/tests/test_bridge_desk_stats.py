"""Tests for shared Live desk stats helpers."""
from __future__ import annotations

from datetime import date, datetime, timezone

from gui.bridge_desk_stats import (
  count_open,
  fmt_px,
  open_trade,
  period_stats,
  unrealized_r,
)


def test_fmt_px():
  assert fmt_px(1.08512) == "1.08512"
  assert fmt_px(None) == "—"


def test_open_trade_returns_last_open():
  trades = [
    {"status": "CLOSED", "entry_px": 1.0},
    {"status": "OPEN", "entry_px": 1.1, "direction": "BUY"},
    {"status": "OPEN", "entry_px": 1.2, "direction": "SELL"},
  ]
  ot = open_trade(trades)
  assert ot is not None
  assert ot["entry_px"] == 1.2


def test_unrealized_r_buy():
  trade = {"direction": "BUY", "entry_px": 1.10000, "sl": 1.09000}
  conn = {"bid": 1.10500, "ask": 1.10520}
  ur = unrealized_r(trade, conn)
  assert ur is not None
  assert ur == 0.5  # (1.105-1.10)/0.01


def test_period_stats_auto_only():
  today = date(2026, 8, 6)  # Thursday
  trades = [
    {
      "status": "CLOSED",
      "mode": "auto",
      "entry_time": "2026-08-06T10:00:00+05:30",
      "exit_time": "2026-08-06T11:00:00+05:30",
      "r": 1.5,
      "direction": "BUY",
    },
    {
      "status": "CLOSED",
      "mode": "manual",
      "entry_time": "2026-08-06T12:00:00+05:30",
      "exit_time": "2026-08-06T13:00:00+05:30",
      "r": 9.0,
      "direction": "BUY",
    },
    {
      "status": "CLOSED",
      "mode": "auto",
      "entry_time": "2026-08-04T10:00:00+05:30",
      "exit_time": "2026-08-04T11:00:00+05:30",
      "r": 0.5,
      "direction": "SELL",
    },
  ]
  today_s, week_s = period_stats(trades, today=today)
  assert today_s["n_trades"] == 1
  assert abs(float(today_s["total_r"]) - 1.5) < 1e-6
  assert week_s["n_trades"] == 2  # Mon=Aug3 week includes Aug4 + Aug6
  assert abs(float(week_s["total_r"]) - 2.0) < 1e-6


def test_count_open_auto():
  trades = [
    {"status": "OPEN", "mode": "auto"},
    {"status": "OPEN", "mode": "manual"},
    {"status": "CLOSED", "mode": "auto"},
  ]
  assert count_open(trades, mode="auto") == 1
  assert count_open(trades, mode=None) == 2


def test_desync_hold_without_mt5():
  from gui.bridge_desk_stats import journal_mt5_position_desync

  d = journal_mt5_position_desync(
    journal_open_n=0,
    ea_positions=0,
    ea_online=True,
    decision_reason="position_open",
  )
  assert d is not None
  assert d["kind"] == "hold_without_mt5"
  assert d.get("fixable") is True


def test_desync_counts_manual_opens_against_mt5():
  from gui.bridge_desk_stats import journal_mt5_position_desync

  matched = journal_mt5_position_desync(
    journal_open_n=2,
    ea_positions=2,
    ea_online=True,
    decision_reason="signal",
  )
  assert matched is None
  ghost = journal_mt5_position_desync(
    journal_open_n=2,
    ea_positions=0,
    ea_online=True,
    decision_reason="signal",
  )
  assert ghost is not None
  assert ghost["kind"] == "journal_ghost_open"
