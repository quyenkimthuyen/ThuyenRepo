from __future__ import annotations

import numpy as np
import pandas as pd

from feature_engine import FEATURE_PROFILES, FeatureMatrix
from mt5_bridge import history_sync


def _frame(periods: int = 450, start: str = "2026-01-01") -> pd.DataFrame:
  index = pd.date_range(start, periods=periods, freq="15min")
  close = 1.1 + np.sin(np.arange(periods) / 20) * 0.002
  return pd.DataFrame({
    "Open": close - 0.0001,
    "High": close + 0.0003,
    "Low": close - 0.0003,
    "Close": close,
  }, index=index)


def test_h4_trend_ignores_future_bars_in_open_h4_candle():
  baseline = _frame(periods=816)
  baseline.loc[:, ["Open", "High", "Low", "Close"]] = [99.9, 100.1, 99.8, 100.0]
  shocked = baseline.copy()

  open_h4_start = shocked.index[-1].floor("4h")
  future = (shocked.index >= open_h4_start + pd.Timedelta(hours=3))
  shocked.loc[future, ["Open", "High", "Low", "Close"]] = [
    999.0, 1001.0, 998.0, 1000.0,
  ]

  before_future = (
    (baseline.index >= open_h4_start)
    & (baseline.index < open_h4_start + pd.Timedelta(hours=3))
  )
  baseline_trend = FeatureMatrix(baseline).get("htf_trend")
  shocked_trend = FeatureMatrix(shocked).get("htf_trend")

  np.testing.assert_array_equal(
    shocked_trend[before_future], baseline_trend[before_future]
  )


def test_session_features_use_broker_hour_mapping(monkeypatch):
  frame = _frame(periods=4, start="2026-07-15 01:00")
  calls = []

  def _map_to_broker(value):
    calls.append(value)
    return pd.Timestamp(value) + pd.Timedelta(hours=7)

  monkeypatch.setattr(history_sync, "utc_to_broker_time", _map_to_broker)
  matrix = FeatureMatrix(frame)

  assert len(calls) == len(frame)
  np.testing.assert_array_equal(matrix.utc_hours, np.full(len(frame), 1))
  np.testing.assert_array_equal(matrix.hours, np.full(len(frame), 8))
  np.testing.assert_array_equal(matrix.get("london_session"), np.ones(len(frame)))
  np.testing.assert_array_equal(matrix.get("london_open"), np.ones(len(frame)))


def test_current_and_m15_native_profiles_construct_with_stable_names():
  frame = _frame()
  current = FeatureMatrix(frame)
  explicit_current = FeatureMatrix(frame, profile="current")
  legacy = FeatureMatrix(frame, profile="legacy")
  slower = FeatureMatrix(frame, profile="m15_native")

  assert current.profile == FEATURE_PROFILES["current"]
  assert current.profile == explicit_current.profile
  assert current.warmup == 120
  assert slower.warmup >= 400
  assert slower.profile.atr_period == 28
  assert slower.profile.rsi_period == 28
  assert slower.profile.adx_period == 28
  assert (
    slower.profile.ema_fast,
    slower.profile.ema_slow,
    slower.profile.ema_trend,
    slower.profile.ema_long,
  ) == (16, 48, 96, 384)
  assert slower.profile.bb_period == 40
  assert slower.profile.zscore_period == 40
  assert slower.profile.roc_period == 12
  assert slower.profile.sweep_period == 40
  assert slower.profile.percentile_period == 100
  assert legacy.profile.causal_h4 is False
  assert legacy.profile.broker_sessions is False
  np.testing.assert_array_equal(legacy.hours, legacy.utc_hours)
  assert current.feature_names == slower.feature_names
  assert "ema_slope_8" in slower.feature_names
  assert "price_vs_ema21" in slower.feature_names
  assert "zscore_20" in slower.feature_names
  assert "roc_5" in slower.feature_names
