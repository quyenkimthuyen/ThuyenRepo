from __future__ import annotations

import numpy as np
import pandas as pd

from config import BARS_PER_WEEK, DEFAULT_TF, MAX_TRADES_PER_DAY, TRAIN_WEEKS
from data_loader import get_train_window_indices
from strategy_miner import MinedStrategy, Rule, backtest_mined, generate_signals_mined


def test_m15_constants_and_three_week_window():
  assert DEFAULT_TF == "M15"
  assert TRAIN_WEEKS == 3
  assert BARS_PER_WEEK == 672
  index = pd.date_range("2026-01-01", periods=3000, freq="15min")
  frame = pd.DataFrame({"Close": np.arange(len(index))}, index=index)
  start, end = get_train_window_indices(frame, index[-1], weeks=3)
  assert end - start == BARS_PER_WEEK * 3


class _SignalMatrix:
  def __init__(self):
    first = pd.date_range("2026-07-15 07:00", periods=8, freq="15min")
    second = pd.date_range("2026-07-16 07:00", periods=8, freq="15min")
    self.index = first.append(second)
    self.n = len(self.index)
    self.warmup = 0
    self.hours = self.index.hour.to_numpy()
    self._feature = np.ones(self.n)

  def get(self, _name):
    return self._feature


def test_signal_cap_is_two_per_broker_day():
  fm = _SignalMatrix()
  strategy = MinedStrategy(
    long_rules=[Rule("always", "long", "eq1", 0.5, weight=2.0)],
    min_rules_match=1,
    score_threshold=1.0,
    min_bars_between=1,
    max_trades_per_day=MAX_TRADES_PER_DAY,
    session_filter=False,
  )
  signals = generate_signals_mined(fm, strategy)
  selected = fm.index[np.flatnonzero(signals)]
  assert len(selected) == 4
  assert selected.to_series().groupby(selected.date).size().max() == 2


def test_entry_cap_blocks_third_order_on_broker_day():
  fm = _SignalMatrix()
  fm.open = np.full(fm.n, 1.1)
  fm.high = np.full(fm.n, 1.1001)
  fm.low = np.full(fm.n, 1.0999)
  fm.close = np.full(fm.n, 1.1)
  fm.atr = np.full(fm.n, 0.001)
  signals = np.zeros(fm.n, dtype=np.int8)
  signals[[0, 3, 6]] = 1
  strategy = MinedStrategy(
    max_trades_per_day=2,
    max_hold_bars=1,
    atr_mult_sl=10,
    rr_ratio=10,
  )
  trades = backtest_mined(fm, strategy, signals, 0, 8)
  assert len(trades) == 2
