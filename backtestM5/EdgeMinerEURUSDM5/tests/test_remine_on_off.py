"""Remine ON/OFF — freeze_first walk-forward mines once then reuses strategy."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from strategy_miner import MinedStrategy, Rule


def _fake_strat(name: str = "freeze-test") -> MinedStrategy:
  return MinedStrategy(
    name=name,
    long_rules=[Rule("rsi_14", "long", "<", 30.0, 1.0)],
    short_rules=[Rule("rsi_14", "short", ">", 70.0, 1.0)],
    score_threshold=1.0,
    atr_mult_sl=1.0,
    rr_ratio=2.0,
    exit_mode="full",
    ml_prob_min=0.0,
    min_rules_match=1,
    max_trades_per_day=3,
    min_bars_between=4,
    max_hold_bars=48,
    partial_pct=0.0,
    partial_at_r=1.0,
    trail_activate_r=0.0,
    trail_distance_r=0.0,
    session_filter=False,
    session_start_hour=0,
    session_end_hour=24,
  )


def test_freeze_first_calls_optimize_once():
  from run_backtest import run_walk_forward

  idx = pd.date_range("2026-01-01", periods=96 * 40, freq="5min")
  df = pd.DataFrame(
    {
      "Open": 1.1, "High": 1.101, "Low": 1.099, "Close": 1.1, "Volume": 100,
    },
    index=idx,
  )

  strat = _fake_strat()
  calls = {"n": 0}

  def _opt(*_a, **_k):
    calls["n"] += 1
    return strat

  with patch("run_backtest.require_canonical_mt5_data", return_value={"fingerprint": "x"}), \
       patch("run_backtest.FeatureMatrix") as FM, \
       patch("run_backtest.optimize_on_window", side_effect=_opt), \
       patch("run_backtest.generate_signals_mined", return_value=[]), \
       patch("run_backtest.backtest_mined", return_value=[]), \
       patch("run_backtest.compute_metrics", return_value={
         "n_trades": 0, "win_rate": 0, "avg_rr": 0, "profit_factor": 0,
         "total_pips": 0, "total_r": 0, "max_drawdown_r": 0,
         "max_win_streak": 0, "max_loss_streak": 0, "risk_of_ruin_pct": 0,
       }), \
       patch("run_backtest.get_train_window_indices", return_value=(0, 500)), \
       patch("run_backtest.get_week_indices", return_value=(500, 600)), \
       patch("run_backtest.MIN_TRAIN_BARS", 10):
    fm = MagicMock()
    fm.n = len(df)
    FM.return_value = fm
    result = run_walk_forward(
      df,
      use_learning=False,
      train_weeks=2,
      oos_from="2026-01-20",
      oos_to="2026-02-20",
      remine_each_week=False,
      verbose=False,
    )

  assert result["config"]["remine_mode"] == "freeze_first"
  assert result["config"]["remine_each_week"] is False
  assert calls["n"] == 1, f"expected 1 mine, got {calls['n']}"
  names = {w.get("strategy") for w in result["weekly_log"] if w.get("strategy")}
  assert names == {"freeze-test"} or calls["n"] == 1


def test_monthly_figure_accepts_remine_labels():
  from gui.model_health import build_monthly_kb_compare_figure

  on = pd.DataFrame({
    "month": ["2026-04", "2026-05"],
    "total_r": [2.0, 3.0],
    "cum_r": [2.0, 5.0],
  })
  off = pd.DataFrame({
    "month": ["2026-04", "2026-05"],
    "total_r": [1.0, 1.5],
    "cum_r": [1.0, 2.5],
  })
  fig = build_monthly_kb_compare_figure(
    on, off,
    title="Remine test",
    on_name="Remine ON",
    off_name="Remine OFF",
  )
  assert fig is not None
  names = [t.name for t in fig.data]
  assert "Remine ON" in names
  assert "Remine OFF" in names
