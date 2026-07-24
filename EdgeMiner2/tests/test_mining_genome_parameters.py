from __future__ import annotations

from dataclasses import FrozenInstanceError

import numpy as np
import pandas as pd
import pytest

from evolution import (
  M15_ATR_MULTIPLIERS,
  M15_MAX_HOLD_BARS,
  M15_MIN_BARS_BETWEEN,
  M15_RR_RATIOS,
  M15_SESSION_RANGES,
  crossover,
  mutate_genome,
)
from knowledge_base import KnowledgeBase
from strategy_miner import (
  LABEL_CACHE,
  MinedStrategy,
  MiningSearchSpace,
  Rule,
  _label_outcomes,
  clear_label_cache,
  generate_signals_mined,
)


class _LabelMatrix:
  def __init__(self):
    self.n = 12
    self.open = np.ones(self.n)
    self.high = np.ones(self.n)
    self.low = np.ones(self.n)
    self.atr = np.full(self.n, 0.1)
    self.high[5] = 1.11


def test_label_cache_separates_hold_horizons():
  fm = _LabelMatrix()
  clear_label_cache()

  short_long, _ = _label_outcomes(fm, 0, fm.n, rr=1.0, atr_mult=1.0, max_hold_bars=2)
  long_long, _ = _label_outcomes(fm, 0, fm.n, rr=1.0, atr_mult=1.0, max_hold_bars=5)

  assert not np.array_equal(short_long, long_long)
  assert len(LABEL_CACHE) == 2


class _SessionMatrix:
  def __init__(self, broker_hours=None):
    self.index = pd.date_range("2026-07-20", periods=5, freq="15min")
    self.n = len(self.index)
    self.warmup = 0
    self.hours = np.zeros(self.n, dtype=int)
    if broker_hours is not None:
      self.broker_hours = np.asarray(broker_hours)
    self._feature = np.ones(self.n)

  def get(self, _name):
    return self._feature


def _session_strategy():
  return MinedStrategy(
    long_rules=[Rule("always", "long", "eq1", 0.5, weight=2.0)],
    score_threshold=1.0,
    min_rules_match=1,
    max_trades_per_day=10,
    min_bars_between=1,
    session_start_hour=7,
    session_end_hour=20,
  )


def test_signal_session_boundaries_use_broker_hours_inclusively():
  fm = _SessionMatrix([6, 7, 20, 21, 12])
  signals = generate_signals_mined(fm, _session_strategy())
  assert np.flatnonzero(signals).tolist() == [1, 2]


def test_signal_session_filter_falls_back_to_matrix_hours():
  fm = _SessionMatrix()
  fm.hours = np.asarray([6, 7, 20, 21, 12])
  signals = generate_signals_mined(fm, _session_strategy())
  assert np.flatnonzero(signals).tolist() == [1, 2]


def test_genome_roundtrip_preserves_execution_genes(tmp_path):
  kb = KnowledgeBase(tmp_path / "knowledge.json")
  original = MinedStrategy(
    long_rules=[Rule("x", "long", "gt", 1.0)],
    short_rules=[Rule("y", "short", "lt", -1.0)],
    max_hold_bars=96,
    min_bars_between=12,
    session_filter=False,
    session_start_hour=8,
    session_end_hour=17,
  )

  genome = kb.genome_to_dict(original, fitness=12.5)
  restored = kb.dict_to_strategy(genome)

  assert restored.max_hold_bars == 96
  assert restored.min_bars_between == 12
  assert restored.session_filter is False
  assert (restored.session_start_hour, restored.session_end_hour) == (8, 17)


def _legacy_genome():
  return {
    "name": "legacy",
    "long_rules": [],
    "short_rules": [],
    "score_threshold": 1.0,
    "ml_prob_min": 0.4,
    "rr_ratio": 2.5,
    "atr_mult_sl": 0.9,
    "min_rules_match": 1,
    "exit_mode": "full",
  }


def test_mutation_uses_m15_ranges_and_backfills_legacy_genes():
  backfilled = mutate_genome(_legacy_genome(), rate=0.0)
  assert backfilled["max_hold_bars"] == 36
  assert backfilled["min_bars_between"] == 4
  assert backfilled["session_filter"] is True
  assert (backfilled["session_start_hour"], backfilled["session_end_hour"]) == (7, 20)

  m15_space = MiningSearchSpace(
    rr_ratios=M15_RR_RATIOS,
    atr_multipliers=M15_ATR_MULTIPLIERS,
    max_hold_bars=M15_MAX_HOLD_BARS,
    min_bars_between=M15_MIN_BARS_BETWEEN,
    session_ranges=M15_SESSION_RANGES,
    session_filters=(True, False),
  )
  mutated = mutate_genome(_legacy_genome(), rate=1.0, search_space=m15_space)
  assert mutated["rr_ratio"] in M15_RR_RATIOS
  assert mutated["atr_mult_sl"] in M15_ATR_MULTIPLIERS
  assert mutated["max_hold_bars"] in M15_MAX_HOLD_BARS
  assert mutated["min_bars_between"] in M15_MIN_BARS_BETWEEN
  assert (mutated["session_start_hour"], mutated["session_end_hour"]) in M15_SESSION_RANGES


def test_crossover_backfills_legacy_execution_genes():
  child = crossover(_legacy_genome(), _legacy_genome())
  assert child["max_hold_bars"] == 36
  assert child["min_bars_between"] == 4
  assert child["session_filter"] is True
  assert (child["session_start_hour"], child["session_end_hour"]) == (7, 20)


def test_search_space_defaults_are_immutable_and_backward_compatible():
  space = MiningSearchSpace()
  # Researched M15 defaults (combo_spacing_12__hold_96)
  assert space.max_hold_bars == (96,)
  assert space.min_bars_between == (12,)
  assert space.session_ranges == ((7, 20),)
  with pytest.raises(FrozenInstanceError):
    space.max_hold_bars = (36,)
