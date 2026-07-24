"""Tests for PA confluence features and retargeted fitness."""
from __future__ import annotations

import numpy as np
import pandas as pd

from feature_engine import FeatureMatrix
from strategy_miner import MiningSearchSpace, score_strategy_metrics


def _frame(periods: int = 500, start: str = "2026-01-01") -> pd.DataFrame:
  index = pd.date_range(start, periods=periods, freq="15min")
  close = 1.1 + np.sin(np.arange(periods) / 20) * 0.003
  high = close + 0.0004
  low = close - 0.0004
  # Inject a clear bullish rejection pin
  low[250] = close[250] - 0.002
  high[250] = close[250] + 0.0001
  open_ = close.copy()
  open_[250] = close[250] - 0.00005
  return pd.DataFrame({
    "Open": open_,
    "High": high,
    "Low": low,
    "Close": close,
  }, index=index)


def test_new_pa_features_exist_and_are_finite():
  fm = FeatureMatrix(_frame())
  for name in (
    "rejection_bull", "rejection_bear",
    "displacement_bull", "displacement_bear",
    "structure_break_up", "structure_break_dn",
    "session_vwap_dist", "swing_strength",
    "confluence_long", "confluence_short",
  ):
    v = fm.get(name)
    assert len(v) == fm.n
    assert np.isfinite(v[fm.warmup:]).all()


def test_fitness_prefers_higher_total_r_at_similar_wr():
  weeks = 4.0
  base = {
    "n_trades": 32,
    "win_rate": 0.47,
    "avg_rr": 2.3,
    "profit_factor": 2.0,
    "max_drawdown_r": 10.0,
    "max_loss_streak": 5,
  }
  low_r = score_strategy_metrics({**base, "total_r": 40.0}, weeks)
  high_r = score_strategy_metrics({**base, "total_r": 90.0}, weeks)
  assert high_r > low_r


def test_fitness_rewards_lower_drawdown_via_risk_adjusted_term():
  weeks = 4.0
  base = {
    "n_trades": 32,
    "win_rate": 0.47,
    "avg_rr": 2.3,
    "total_r": 80.0,
    "profit_factor": 2.0,
    "max_loss_streak": 5,
  }
  high_dd = score_strategy_metrics({**base, "max_drawdown_r": 20.0}, weeks)
  low_dd = score_strategy_metrics({**base, "max_drawdown_r": 8.0}, weeks)
  assert low_dd > high_dd


def test_researched_search_space_defaults():
  space = MiningSearchSpace()
  assert space.max_hold_bars == (96,)
  assert space.min_bars_between == (12,)
