"""Live SL must keep ATR room after the broker hits the opposite quote."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from execution import PIP, atr_stop_distance, spread_price
from mt5_bridge.paper_fill import PaperBook
from paper_monitor import _project_signal_levels
from strategy_miner import MinedStrategy, backtest_mined
from mt5_bridge.trade_journal import load_trades


def test_atr_stop_distance_adds_one_spread():
  atr = 0.000333
  sl_d = atr_stop_distance(atr, 0.9, spread_pips=1.9)
  assert sl_d == pytest.approx(0.9 * atr + 1.9 * PIP)
  assert spread_price(1.9) == pytest.approx(0.00019)


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


def test_project_levels_as_of_closed_bar_ignores_next_open():
  fm = _LevelsFm()
  fm.open = fm.open.copy()
  fm.open[1] = 1.18000
  strat = MinedStrategy(atr_mult_sl=0.9, rr_ratio=3.0)
  live_like = _project_signal_levels(
    fm, strat, 0, -1, spread_pips=1.9, slippage_pips=0.3, as_of_closed_bar=True,
  )
  leaked = _project_signal_levels(
    fm, strat, 0, -1, spread_pips=1.9, slippage_pips=0.3, as_of_closed_bar=False,
  )
  clip = _LevelsFm()
  clip.n = 1
  clip.open = clip.open[:1]
  clip.high = clip.high[:1]
  clip.low = clip.low[:1]
  clip.close = clip.close[:1]
  clip.atr = clip.atr[:1]
  clip.hours = clip.hours[:1]
  clip.index = clip.index[:1]
  want = _project_signal_levels(
    clip, strat, 0, -1, spread_pips=1.9, slippage_pips=0.3, as_of_closed_bar=True,
  )
  assert live_like["entry_px"] == want["entry_px"]
  assert live_like["entry_px"] != leaked["entry_px"]


def test_project_levels_sl_includes_spread():
  fm = _LevelsFm()
  strat = MinedStrategy(atr_mult_sl=0.9, rr_ratio=3.0)
  proj = _project_signal_levels(fm, strat, 0, -1, spread_pips=1.9, slippage_pips=0.3)
  assert proj is not None
  sl_d = abs(proj["entry_px"] - proj["sl"])
  atr_only = 0.9 * float(fm.atr[0])
  assert sl_d == pytest.approx(atr_only + 1.9 * PIP, abs=1.5e-5)
  assert sl_d > atr_only + 1.5 * PIP


def test_project_levels_eur_sell_survives_11_15_wick():
  """Replay 26/8 11:15: bid high 1.16760 must not reach spread-buffered SL."""
  fm = _LevelsFm()
  strat = MinedStrategy(atr_mult_sl=0.9, rr_ratio=3.0)
  proj = _project_signal_levels(fm, strat, 0, -1, spread_pips=1.9, slippage_pips=0.3)
  fill = 1.16738
  planned_risk = abs(proj["entry_px"] - proj["sl"])
  live_sl = fill + planned_risk
  bid_high = 1.16760
  ask_high = bid_high + 1.9 * PIP
  assert ask_high < live_sl


def test_paper_fill_sell_sl_on_entry_bar(tmp_path: Path, monkeypatch):
  book = PaperBook(
    bridge_dir=tmp_path, model_id="tm_sl", spread_pips=1.9, slippage_pips=0.3,
  )
  book.queue_decision({
    "action": "SELL",
    "signal_id": "sig_entry_sl",
    "entry": 1.16738,
    "sl": 1.16768,
    "tp": 1.16648,
    "rr": 3.0,
    "exit_mode": "full",
    "max_hold_bars": 96,
    "model_id": "tm_sl",
  })
  fills = book.on_bar(
    open_=1.16738, high=1.16760, low=1.16734, close=1.16759,
    bar_time="2026.08.26 11:15",
  )
  assert len(fills) == 2
  assert fills[0]["event"] == "open"
  assert fills[1]["event"] == "close"
  assert fills[1]["reason"] == "sl"
  closed = [t for t in load_trades(tmp_path) if t.get("status") == "CLOSED"]
  assert len(closed) == 1


class _BtFm:
  def __init__(self):
    n = 6
    self.index = pd.date_range("2026-08-26 11:00", periods=n, freq="15min")
    self.n = n
    self.warmup = 0
    self.open = np.full(n, 1.10)
    self.high = np.full(n, 1.10012)
    self.low = np.full(n, 1.09990)
    self.close = np.full(n, 1.10)
    self.high[1] = 1.10012
    self.low[3] = 1.09800
    self.atr = np.full(n, 0.000333)
    self.hours = self.index.hour.to_numpy()


def test_backtest_buffered_sl_does_not_die_on_spread_wick():
  fm = _BtFm()
  signals = np.zeros(fm.n, dtype=np.int8)
  signals[0] = -1
  strat = MinedStrategy(
    atr_mult_sl=0.9, rr_ratio=3.0, max_hold_bars=96, max_trades_per_day=2,
    session_filter=False, min_bars_between=1, exit_mode="full", anti_chase=False,
  )
  trades = backtest_mined(
    fm, strat, signals, 0, fm.n, spread_pips=1.9, slippage_pips=0.3,
  )
  assert len(trades) == 1
  assert trades[0].exit_reason == "tp"
