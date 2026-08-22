"""Live journal must enforce min_bars_between against already-filled entries."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from mt5_bridge.engine import journal_violates_min_bars_between
from mt5_bridge.history_sync import parse_broker_time, utc_to_broker_time
from mt5_bridge.trade_journal import clear_trades, save_trades


def _fm_from_broker(start: str, n: int = 24, minutes: int = 15):
  start_ts = parse_broker_time(start)
  idx = pd.date_range(start_ts, periods=n, freq=f"{minutes}min")
  return type("FM", (), {"index": idx})()


def _check(tmp_path: Path, bar_time: str, model_id: str, min_bars: int, fm=None) -> bool:
  bar_ts = parse_broker_time(bar_time)
  fm = fm or _fm_from_broker("2026-08-20 07:00")
  bar_idx = int(fm.index.get_loc(bar_ts))
  return journal_violates_min_bars_between(
    tmp_path,
    utc_to_broker_time(bar_ts).date(),
    model_id=model_id,
    fm=fm,
    bar_idx=bar_idx,
    bar_ts=bar_ts,
    min_bars=min_bars,
  )


def test_blocks_second_entry_7_bars_after_first(tmp_path: Path):
  """Today's EUR bug: 07:30 then 09:15 is 7 M15 bars, genome min_bars_between=12."""
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "t1",
      "signal_id": "auto_sig",
      "status": "CLOSED",
      "mode": "auto",
      "origin": "strategy",
      "model_id": "tm_a",
      "bar_time": "2026.08.20 07:30",
      "entry_time": "2026.08.20 07:30",
    },
  ], tmp_path)
  assert _check(tmp_path, "2026-08-20 09:15", "tm_a", 12) is True
  assert _check(tmp_path, "2026-08-20 10:30", "tm_a", 12) is False


def test_counts_manual_user_sl_tp_strategy_fill(tmp_path: Path):
  """user_sl_tp tags mode=manual but the open was still a strategy fill."""
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "t1",
      "signal_id": "abc123",
      "status": "CLOSED",
      "mode": "manual",
      "origin": "strategy",
      "interventions": ["user_sl_tp"],
      "model_id": "tm_b",
      "bar_time": "2026.08.20 07:30",
      "entry_time": "2026.08.20 07:30",
    },
  ], tmp_path)
  assert _check(tmp_path, "2026-08-20 09:15", "tm_b", 12) is True


def test_ignores_other_model_and_manual_test(tmp_path: Path):
  clear_trades(tmp_path)
  save_trades([
    {
      "id": "other",
      "signal_id": "x",
      "status": "CLOSED",
      "mode": "auto",
      "origin": "strategy",
      "model_id": "tm_other",
      "bar_time": "2026.08.20 07:30",
      "entry_time": "2026.08.20 07:30",
    },
    {
      "id": "test",
      "signal_id": "manual_test_1",
      "status": "CLOSED",
      "mode": "manual",
      "origin": "manual_test",
      "model_id": "tm_a",
      "bar_time": "2026.08.20 07:30",
      "entry_time": "2026.08.20 07:30",
    },
  ], tmp_path)
  assert _check(tmp_path, "2026-08-20 09:15", "tm_a", 12) is False
