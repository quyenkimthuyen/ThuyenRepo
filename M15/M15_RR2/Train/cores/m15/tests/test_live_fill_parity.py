"""Lab (KB/grid/OOS) fill geometry must match live/replay Bid/Ask + confirm-stop."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from execution import (
  confirm_bar_result,
  confirm_fill_price,
  effective_rr,
  rebase_fill_levels,
)
from mt5_bridge.paper_fill import PaperBook
from paper_monitor import _project_signal_levels
from strategy_miner import MinedStrategy, apply_oos_exit_overlay, backtest_mined


class _LevelsFm:
  def __init__(self):
    self.index = pd.date_range("2026-08-26 11:00", periods=3, freq="15min")
    self.n = 3
    self.open = np.array([1.16699, 1.16738, 1.16758])
    self.high = np.array([1.16743, 1.16760, 1.16759])
    self.low = np.array([1.16691, 1.16734, 1.16706])
    self.close = np.array([1.16739, 1.16759, 1.16726])
    self.atr = np.full(3, 0.000333)
    self.hours = self.index.hour.to_numpy()
    self.warmup = 0


def test_clipped_tp_decision_rr_is_geometry_not_genome():
  fm = _LevelsFm()
  strat = MinedStrategy(atr_mult_sl=0.9, rr_ratio=3.0, tp_ignores_spread_buffer=True)
  proj = _project_signal_levels(fm, strat, 0, -1, spread_pips=1.9, slippage_pips=0.0)
  assert proj is not None
  geom = effective_rr(proj["entry_px"], proj["sl"], proj["tp"], fallback=3.0)
  assert geom == pytest.approx(float(proj["rr"]), abs=1e-3)
  assert geom < 2.8
  sl, tp, risk = rebase_fill_levels(
    direction=-1,
    fill_entry=proj["entry_px"] + 0.00004,
    planned_entry=proj["entry_px"],
    planned_sl=proj["sl"],
    planned_tp=proj["tp"],
    rr=3.0,
  )
  assert abs((proj["entry_px"] + 0.00004 - tp) / risk - geom) < 1e-9


def test_oos_exit_overlay_is_what_live_and_grid_backtest_use():
  mined = MinedStrategy(exit_mode="full", trail_activate_r=1.0, trail_distance_r=0.5)
  space = type("S", (), {
    "oos_exit_mode": "hybrid",
    "oos_trail_activate_r": 2.4,
    "oos_trail_distance_r": 0.6,
  })()
  live = apply_oos_exit_overlay(mined, space)
  assert live.exit_mode == "hybrid"
  assert live.trail_activate_r == pytest.approx(2.4)
  assert mined.exit_mode == "full"


def test_confirm_same_bar_cancel_beats_fill():
  hit = confirm_bar_result(
    direction=1, ref_price=1.10, sl_d=0.001, confirm_r=0.20, cancel_r=0.50,
    bid_high=1.10025, bid_low=1.09940, spread_px=0.0,
  )
  assert hit == "cancel"


def test_paper_confirm_fill_matches_miner(tmp_path: Path):
  n = 8
  spr_pips = 1.0
  spr_px = spr_pips * 0.0001
  sl_d = 0.001 + spr_px  # ATR×1 + 1 spread, same as miner
  ask_open = 1.10 + spr_px
  want = confirm_fill_price(1, ask_open, sl_d, 0.20)

  index = pd.date_range("2026-08-26 11:00", periods=n, freq="15min")
  fm = type("Fm", (), {})()
  fm.index = index
  fm.n = n
  fm.warmup = 0
  fm.open = np.full(n, 1.10)
  fm.high = np.full(n, 1.10005)
  fm.low = np.full(n, 1.09995)
  fm.close = np.full(n, 1.10)
  fm.atr = np.full(n, 0.001)
  fm.hours = index.hour.to_numpy()
  fm.spread_points = np.zeros(n)
  fm.high[1] = want + 0.00005
  fm.high[4] = 1.10400

  signals = np.zeros(n, dtype=np.int8)
  signals[0] = 1
  strat = MinedStrategy(
    atr_mult_sl=1.0, rr_ratio=2.0, max_hold_bars=96, max_trades_per_day=2,
    session_filter=False, min_bars_between=1, exit_mode="full", anti_chase=False,
    confirm_r=0.20, confirm_wait_bars=4, confirm_cancel_r=0.50,
  )
  trades = backtest_mined(fm, strat, signals, 0, n, spread_pips=spr_pips, slippage_pips=0.0)
  assert len(trades) == 1
  assert trades[0].entry_price == pytest.approx(want)

  planned = ask_open
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_confirm")
  book.queue_decision({
    "action": "BUY",
    "signal_id": "s-c",
    "entry": planned,
    "sl": planned - sl_d,
    "tp": planned + sl_d * 2.0,
    "rr": 3.0,
    "exit_mode": "full",
    "max_hold_bars": 10,
    "spread_pips": spr_pips,
    "confirm_r": 0.20,
    "confirm_wait_bars": 4,
    "confirm_cancel_r": 0.50,
  })
  fills = book.on_bar(
    open_=1.10, high=float(fm.high[1]), low=1.09995, close=1.10,
    bar_time="t1", spread_points=0,
  )
  assert len(fills) == 1
  assert fills[0]["price"] == pytest.approx(want)
  assert fills[0]["price"] == pytest.approx(trades[0].entry_price)
  geom = effective_rr(planned, planned - sl_d, planned + sl_d * 2.0)
  assert geom == pytest.approx(2.0)
  assert book.sl == pytest.approx(want - sl_d)
  assert book.tp == pytest.approx(want + sl_d * geom)


def test_paper_confirm_cancel_clears_pending_without_crash(tmp_path: Path):
  book = PaperBook(bridge_dir=tmp_path, model_id="tm_cancel")
  book.queue_decision({
    "action": "BUY",
    "signal_id": "s-x",
    "entry": 1.10010,
    "sl": 1.09900,
    "tp": 1.10220,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 10,
    "spread_pips": 1.0,
    "confirm_r": 0.20,
    "confirm_wait_bars": 4,
    "confirm_cancel_r": 0.50,
  })
  fills = book.on_bar(
    open_=1.10, high=1.10005, low=1.09800, close=1.09950,
    bar_time="t1", spread_points=0,
  )
  assert fills == []
  assert book.pending is None
  assert book.open is False
