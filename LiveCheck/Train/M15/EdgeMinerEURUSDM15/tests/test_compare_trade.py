"""Tests for Compare Trade — paper fill + multi-model isolation + charts."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from gui.bridge_model_monitor import (
  build_multi_model_equity_figure,
  build_multi_model_monthly_figure,
)
from mt5_bridge.compare_runner import slice_replay_frame
from mt5_bridge.engine import _journal_open_and_day_count, _normalize
from mt5_bridge.history_sync import utc_to_broker_time
from mt5_bridge.paper_fill import PaperBook
from mt5_bridge.trade_journal import clear_trades, filter_trades, load_trades, save_trades


def _bar_time(ts: pd.Timestamp) -> str:
  return utc_to_broker_time(ts).strftime("%Y.%m.%d %H:%M")


def test_paper_fill_open_next_bar_and_tp(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_a")
  decision = {
    "action": "BUY",
    "signal_id": "sig_buy_1",
    "entry": 1.1000,
    "sl": 1.0990,
    "tp": 1.1020,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 96,
    "model_id": "tm_a",
  }
  # Decision queued → open at next bar open; manage on same bar skips (held=1)
  book.queue_decision(decision)
  assert book.pending is not None
  fills0 = book.on_bar(open_=1.1005, high=1.1008, low=1.1002, close=1.1006, bar_time="2026.01.02 08:00")
  assert len(fills0) == 1
  assert fills0[0]["event"] == "open"
  assert fills0[0]["price"] == pytest.approx(1.1005)
  assert book.open is True
  # Next bar: held becomes 2 → SL/TP active; high hits TP
  fills1 = book.on_bar(open_=1.1005, high=1.1030, low=1.1000, close=1.1025, bar_time="2026.01.02 08:15")
  assert len(fills1) == 1
  assert fills1[0]["event"] == "close"
  assert fills1[0]["reason"] == "tp"
  trades = load_trades(tmp_path)
  closed = [t for t in trades if t.get("status") == "CLOSED"]
  assert len(closed) == 1
  assert closed[0]["model_id"] == "tm_a"
  assert closed[0]["r"] is not None or closed[0]["profit"] is not None


def test_paper_fill_sl_sell(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_b")
  book.queue_decision({
    "action": "SELL",
    "signal_id": "sig_sell_1",
    "entry": 1.2000,
    "sl": 1.2010,
    "tp": 1.1980,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 10,
    "model_id": "tm_b",
  })
  book.on_bar(open_=1.2000, high=1.2002, low=1.1998, close=1.1999, bar_time="2026.02.01 10:00")
  book.on_bar(open_=1.1999, high=1.2001, low=1.1995, close=1.1998, bar_time="2026.02.01 10:15")  # skip
  fills = book.on_bar(open_=1.2002, high=1.2015, low=1.1990, close=1.2012, bar_time="2026.02.01 10:30")
  assert len(fills) == 1
  assert fills[0]["reason"] == "sl"


def test_journal_open_scoped_by_model_id(tmp_path: Path):
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "a1", "signal_id": "a1", "status": "OPEN", "mode": "auto",
      "model_id": "tm_a", "entry_time": "2026-01-05 09:00", "direction": "BUY",
    },
    {
      "id": "b1", "signal_id": "b1", "status": "CLOSED", "mode": "auto",
      "model_id": "tm_b", "entry_time": "2026-01-05 11:00", "direction": "SELL",
    },
  ], tmp_path)
  day = pd.Timestamp("2026-01-05").date()
  open_a, day_a = _journal_open_and_day_count(tmp_path, day, model_id="tm_a")
  open_b, day_b = _journal_open_and_day_count(tmp_path, day, model_id="tm_b")
  assert open_a is True
  assert day_a == 1
  assert open_b is False
  assert day_b == 1


def test_journal_day_count_includes_strategy_fills_tagged_user_sl_tp(tmp_path: Path):
  """user_sl_tp flips mode=manual; day slots must still count the strategy fill."""
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "s1", "signal_id": "f61781c53327a39f", "status": "CLOSED",
      "mode": "manual", "intervened": True,
      "interventions": ["user_sl_tp", "ea_trail"],
      "origin": "strategy", "model_id": "tm_a",
      "entry_time": "2026.08.20 07:30", "direction": "SELL",
    },
    {
      "id": "s2", "signal_id": "9c5362f87d48362e", "status": "CLOSED",
      "mode": "manual", "intervened": True,
      "interventions": ["user_sl_tp"],
      "origin": "strategy", "model_id": "tm_a",
      "entry_time": "2026.08.20 09:15", "direction": "SELL",
    },
    {
      "id": "m1", "signal_id": "manual_test_1", "status": "CLOSED",
      "mode": "manual", "origin": "manual_test", "model_id": "tm_a",
      "entry_time": "2026.08.20 12:00", "direction": "BUY",
    },
  ], tmp_path)
  day = pd.Timestamp("2026-08-20").date()
  has_open, day_n = _journal_open_and_day_count(tmp_path, day, model_id="tm_a")
  assert has_open is False
  assert day_n == 2


def test_filter_trades_requires_model_id(tmp_path: Path):
  save_trades([
    {"id": "1", "status": "CLOSED", "mode": "auto", "model_id": "tm_a", "entry_time": "2026-01-01"},
    {"id": "2", "status": "CLOSED", "mode": "auto", "model_id": "tm_b", "entry_time": "2026-01-01"},
  ], tmp_path)
  only_a = filter_trades(bridge_dir=tmp_path, model_id="tm_a")
  assert len(only_a) == 1
  assert only_a[0]["model_id"] == "tm_a"


def test_two_paper_books_do_not_block_each_other(tmp_path: Path):
  dir_a = tmp_path / "a"
  dir_b = tmp_path / "b"
  dir_a.mkdir()
  dir_b.mkdir()
  a = PaperBook(bridge_dir=dir_a, model_id="tm_a")
  b = PaperBook(bridge_dir=dir_b, model_id="tm_b")
  decision = {
    "action": "BUY",
    "entry": 1.10,
    "sl": 1.09,
    "tp": 1.12,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 5,
  }
  a.queue_decision({**decision, "signal_id": "a1", "model_id": "tm_a"})
  b.queue_decision({**decision, "signal_id": "b1", "model_id": "tm_b"})
  a.on_bar(open_=1.10, high=1.11, low=1.09, close=1.105, bar_time="2026.03.01 08:00")
  b.on_bar(open_=1.10, high=1.11, low=1.09, close=1.105, bar_time="2026.03.01 08:00")
  assert a.open and b.open
  assert len(load_trades(dir_a)) == 1
  assert len(load_trades(dir_b)) == 1
  assert load_trades(dir_a)[0]["model_id"] == "tm_a"
  assert load_trades(dir_b)[0]["model_id"] == "tm_b"


def test_slice_replay_frame_by_broker_date():
  idx = pd.to_datetime([
    "2026-01-01 10:00",
    "2026-01-02 10:00",
    "2026-01-03 10:00",
  ], utc=True).tz_convert(None)
  df = _normalize(pd.DataFrame({
    "Open": [1.0, 1.1, 1.2],
    "High": [1.01, 1.11, 1.21],
    "Low": [0.99, 1.09, 1.19],
    "Close": [1.005, 1.105, 1.205],
    "Volume": [1, 1, 1],
  }, index=idx))
  out = slice_replay_frame(df, "2026-01-02", "2026-01-02")
  assert len(out) == 1


def test_multi_model_equity_figure_has_two_series():
  eq_a = pd.DataFrame({
    "entry": pd.to_datetime(["2026-01-01", "2026-01-02"]),
    "equity_r": [1.0, 2.0],
    "drawdown_r": [0.0, 0.0],
  })
  eq_b = pd.DataFrame({
    "entry": pd.to_datetime(["2026-01-01", "2026-01-03"]),
    "equity_r": [0.5, 1.5],
    "drawdown_r": [0.0, 0.2],
  })
  fig = build_multi_model_equity_figure({"Model A": eq_a, "Model B": eq_b})
  assert fig is not None
  # equity + dd per model
  assert len(fig.data) >= 2


def test_multi_model_monthly_figure():
  mo_a = pd.DataFrame({
    "month": ["2026-01", "2026-02"],
    "total_r": [2.0, 1.0],
    "cum_r": [2.0, 3.0],
  })
  mo_b = pd.DataFrame({
    "month": ["2026-01", "2026-02"],
    "total_r": [1.0, 2.0],
    "cum_r": [1.0, 3.0],
  })
  fig = build_multi_model_monthly_figure({"A": mo_a, "B": mo_b})
  assert fig is not None
  assert len(fig.data) >= 2


def test_multi_model_price_figure_markers():
  from gui.bridge_model_monitor import build_multi_model_price_figure

  idx = pd.to_datetime([
    "2026-01-02 08:00",
    "2026-01-02 08:15",
    "2026-01-02 08:30",
    "2026-01-02 08:45",
  ])
  ohlc = pd.DataFrame({
    "Open": [1.10, 1.101, 1.102, 1.1015],
    "High": [1.101, 1.103, 1.104, 1.102],
    "Low": [1.099, 1.100, 1.101, 1.1005],
    "Close": [1.1005, 1.102, 1.1018, 1.1012],
    "Volume": [1, 1, 1, 1],
  }, index=idx)
  trades = {
    "Model A": [{
      "status": "CLOSED",
      "direction": "BUY",
      "entry_time": "2026.01.02 08:15",
      "entry_px": 1.101,
      "exit_time": "2026.01.02 08:45",
      "exit_px": 1.1015,
      "r": 0.5,
      "reason": "tp",
    }],
    "Model B": [{
      "status": "CLOSED",
      "direction": "SELL",
      "entry_time": "2026.01.02 08:00",
      "entry_px": 1.10,
      "exit_time": "2026.01.02 08:30",
      "exit_px": 1.1018,
      "r": -0.8,
      "reason": "sl",
    }],
  }
  fig = build_multi_model_price_figure(ohlc, trades, show_connectors=True)
  assert fig is not None
  # candlestick + entries + exits + connectors
  assert len(fig.data) >= 5
  types = {type(t).__name__ for t in fig.data}
  assert "Candlestick" in types
