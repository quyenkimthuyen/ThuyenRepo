"""Tests for PA confluence features and retargeted fitness."""
from __future__ import annotations

import numpy as np
import pandas as pd

from feature_engine import FeatureMatrix
from strategy_miner import MiningSearchSpace, score_strategy_metrics, MinedStrategy


def _frame(periods: int = 500, start: str = "2026-01-01") -> pd.DataFrame:
  index = pd.date_range(start, periods=periods, freq="5min")
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
  assert space.max_hold_bars == (192,)
  assert space.min_bars_between == (16,)
  assert space.selection_mode == "legacy"


def test_expectancy_frontier_prefers_joint_wr_rr():
  weeks = 4.0
  high_wr_low_rr = {
    "n_trades": 32, "win_rate": 0.55, "avg_rr": 1.6, "total_r": 50.0,
    "profit_factor": 1.8, "max_drawdown_r": 10.0, "max_loss_streak": 5,
  }
  balanced = {
    "n_trades": 32, "win_rate": 0.49, "avg_rr": 2.5, "total_r": 55.0,
    "profit_factor": 2.1, "max_drawdown_r": 10.0, "max_loss_streak": 5,
  }
  legacy_high = score_strategy_metrics(high_wr_low_rr, weeks, selection_mode="legacy")
  frontier_high = score_strategy_metrics(high_wr_low_rr, weeks, selection_mode="expectancy_frontier")
  frontier_bal = score_strategy_metrics(balanced, weeks, selection_mode="expectancy_frontier")
  # Frontier should lift the balanced high-RR book relative to WR-only book.
  assert frontier_bal - frontier_high > legacy_high - score_strategy_metrics(
    balanced, weeks, selection_mode="legacy",
  ) or frontier_bal > frontier_high


def test_mining_presets_are_opt_in_and_baseline_matches_default():
  from mining_presets import get_preset, list_presets
  from strategy_miner import mining_search_space_from_dict

  assert "baseline" in list_presets()
  assert "wr_rr_frontier" in list_presets()
  assert "edge_surgery" in list_presets()
  baseline = mining_search_space_from_dict(get_preset("baseline"))
  default = MiningSearchSpace()
  assert baseline.rr_ratios == default.rr_ratios
  assert baseline.min_bars_between == default.min_bars_between
  assert baseline.selection_mode == "legacy"
  assert baseline.edge_surgery is False
  frontier = mining_search_space_from_dict(get_preset("wr_rr_frontier"))
  assert frontier.selection_mode == "expectancy_frontier"
  assert frontier.min_bars_between == (24,)
  assert frontier.session_ranges == ((8, 17),)
  surgery = mining_search_space_from_dict(get_preset("edge_surgery"))
  assert surgery.edge_surgery is True
  assert surgery.min_bars_between == default.min_bars_between


def test_edge_surgery_blocks_toxic_hour_and_weak_side():
  from strategy import Trade
  from strategy_miner import calibrate_edge_surgery
  import strategy_miner as sm

  class _FM:
    n = 5
    index = pd.date_range("2026-01-05 08:00", periods=5, freq="5min")
    warmup = 0

  trades = [
    Trade(pd.Timestamp("2026-01-05 08:00"), pd.Timestamp("2026-01-05 09:00"),
          1, 1.1, 1.0, 1.0, 1.2, -10, -1.0, "sl"),
    Trade(pd.Timestamp("2026-01-05 08:15"), pd.Timestamp("2026-01-05 09:00"),
          1, 1.1, 1.0, 1.0, 1.2, -10, -1.0, "sl"),
    Trade(pd.Timestamp("2026-01-05 08:30"), pd.Timestamp("2026-01-05 09:00"),
          1, 1.1, 1.0, 1.0, 1.2, -10, -1.0, "sl"),
    Trade(pd.Timestamp("2026-01-05 10:00"), pd.Timestamp("2026-01-05 11:00"),
          -1, 1.1, 1.0, 1.2, 1.0, 20, 2.5, "tp"),
    Trade(pd.Timestamp("2026-01-05 10:15"), pd.Timestamp("2026-01-05 11:00"),
          -1, 1.1, 1.0, 1.2, 1.0, 20, 2.5, "tp"),
    Trade(pd.Timestamp("2026-01-05 10:30"), pd.Timestamp("2026-01-05 11:00"),
          -1, 1.1, 1.0, 1.2, 1.0, 20, 2.5, "tp"),
  ]
  original_gen = sm.generate_signals_mined
  original_bt = sm.backtest_mined
  sm.generate_signals_mined = lambda *a, **k: None
  sm.backtest_mined = lambda *a, **k: trades
  try:
    strat = MinedStrategy(name="t")
    out = calibrate_edge_surgery(_FM(), strat, 0, 5, min_hour_trades=3, max_hour_wr=0.38)
  finally:
    sm.generate_signals_mined = original_gen
    sm.backtest_mined = original_bt
  assert 8 in out.blocked_hours
  assert out.allow_long is False
  assert out.allow_short is True


def test_elite_frontier_rewards_wr60_rr3():
  weeks = 4.0
  base = {
    "n_trades": 16, "total_r": 40.0, "profit_factor": 2.5,
    "max_drawdown_r": 6.0, "max_loss_streak": 3,
  }
  mid = score_strategy_metrics(
    {**base, "win_rate": 0.50, "avg_rr": 2.5}, weeks,
    target_tpw=3.0, selection_mode="elite_frontier",
  )
  elite = score_strategy_metrics(
    {**base, "win_rate": 0.62, "avg_rr": 3.1}, weeks,
    target_tpw=3.0, selection_mode="elite_frontier",
  )
  assert elite > mid


def test_m5_frequency_band_prefers_dense_target():
  """Legacy fitness must reward ~24 tpw, not leftover M15 7–10 caps."""
  weeks = 4.0
  base = {
    "win_rate": 0.48, "avg_rr": 2.3, "profit_factor": 2.0,
    "max_drawdown_r": 10.0, "max_loss_streak": 5, "total_r": 60.0,
  }
  sparse = score_strategy_metrics(
    {**base, "n_trades": 32}, weeks, target_tpw=24.0,  # 8 tpw
  )
  dense = score_strategy_metrics(
    {**base, "n_trades": 96}, weeks, target_tpw=24.0,  # 24 tpw
  )
  assert dense > sparse


def test_elite_presets_opt_in():
  from mining_presets import RECOMMENDED_PRESET, get_preset, preset_label
  from strategy_miner import mining_search_space_from_dict

  space = mining_search_space_from_dict(get_preset("elite_60_3"))
  assert space.selection_mode == "elite_frontier"
  assert space.exit_modes_full_only is True
  assert space.rr_ratios == (3.5, 4.0)
  assert space.anti_chase is True
  assert space.anti_chase_fixed_rsi == 58.0
  assert space.target_trades_per_week == 3.0
  assert space.max_hold_bars == (288,)
  assert space.min_bars_between == (36,)
  assert space.max_trades_per_day == 2
  assert MiningSearchSpace().exit_modes_full_only is False
  assert RECOMMENDED_PRESET == "elite_or_quality"
  eoq = mining_search_space_from_dict(get_preset(RECOMMENDED_PRESET))
  assert eoq.anti_chase_use_vwap is True
  assert eoq.anti_chase_logic == "or"
  assert eoq.rr_ratios == (3.2, 3.5, 4.0)
  assert eoq.target_trades_per_week == 3.5
  assert eoq.min_bars_between == (36,)
  assert eoq.max_trades_per_day == 2
  assert "OR-quality" in preset_label(RECOMMENDED_PRESET)
  from mining_presets import CURATED_PRESETS, DEPRECATED_PRESETS, list_curated_presets
  assert RECOMMENDED_PRESET in CURATED_PRESETS
  assert "wr_rr_frontier" in DEPRECATED_PRESETS
  assert "wr_rr_frontier" not in list_curated_presets()
  assert "elite_or_quality" in list_curated_presets()
  assert list_curated_presets() == [
    "elite_or_quality",
    "elite_m5_balanced",
    "anti_chase_fixed_70",
    "elite_55_4",
    "baseline",
  ]
  assert "elite_60_3_vwap" in DEPRECATED_PRESETS
  assert "frontier_rr_hi" not in list_curated_presets()


def test_preset_blurbs_and_direction_line():
  from mining_presets import (
    RECOMMENDED_PRESET,
    curated_preset_catalog,
    get_preset,
    match_preset_name,
    preset_blurb,
    space_direction_line,
  )

  blurb = preset_blurb(RECOMMENDED_PRESET)
  assert "WR" in blurb["intent"] or "ưu tiên" in blurb["intent"].lower()
  assert blurb.get("knobs") and blurb.get("tradeoff")
  catalog = curated_preset_catalog()
  assert catalog and all("Ý định" in row for row in catalog)
  assert match_preset_name(get_preset(RECOMMENDED_PRESET)) == RECOMMENDED_PRESET
  line = space_direction_line(get_preset(RECOMMENDED_PRESET))
  assert "Elite OR-quality" in line
  assert "Baseline miner" in space_direction_line(None)


def test_app_settings_default_mining_preset():
  from gui.app_settings import DEFAULT_SETTINGS, _sanitize_settings
  assert DEFAULT_SETTINGS["mining_presets"] == ["elite_or_quality"]
  cleaned = _sanitize_settings({"learning_eras": DEFAULT_SETTINGS["learning_eras"]})
  assert cleaned["mining_presets"] == ["elite_or_quality"]


def test_anti_chase_prefers_low_rsi_shorts():
  from strategy import Trade
  from strategy_miner import calibrate_anti_chase
  import strategy_miner as sm

  class _FM:
    n = 6
    index = pd.date_range("2026-01-05 10:00", periods=6, freq="5min")
    warmup = 0
    def get(self, name):
      if name == "rsi":
        return np.array([70.0, 70.0, 70.0, 50.0, 50.0, 50.0])
      if name == "session_vwap_dist":
        return np.zeros(6)
      raise KeyError(name)

  # 3 chase shorts (lose) + 3 momentum shorts (win)
  trades = []
  for ts, r in [
    ("2026-01-05 10:00", -1.0), ("2026-01-05 10:15", -1.0), ("2026-01-05 10:30", -1.0),
    ("2026-01-05 10:45", 2.5), ("2026-01-05 11:00", 2.5), ("2026-01-05 11:15", 2.5),
  ]:
    trades.append(Trade(pd.Timestamp(ts), pd.Timestamp(ts), -1, 1.1, 1.0, 1.2, 1.0, 10, r, "x"))

  original_gen = sm.generate_signals_mined
  original_bt = sm.backtest_mined
  sm.generate_signals_mined = lambda *a, **k: None
  sm.backtest_mined = lambda *a, **k: trades
  try:
    out = calibrate_anti_chase(
      _FM(), MinedStrategy(name="t"), 0, 6,
      rsi_caps=(55.0, 60.0, 100.0), vwap_caps=(99.0,), min_tpw=1.0,
      selection_mode="expectancy_frontier",
    )
  finally:
    sm.generate_signals_mined = original_gen
    sm.backtest_mined = original_bt
  assert out.anti_chase is True
  assert out.anti_chase_rsi_short_max <= 60.0

