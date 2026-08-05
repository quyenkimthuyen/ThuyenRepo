"""Trade Model freeze schedule — hydrate + Bridge prefers schedule over remine (M15)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from strategy_miner import MinedStrategy, Rule
from trade_model_schedule import (
  append_live_week,
  full_strategy_dict,
  lookup_week_strategy,
  model_live_weeks_path,
  model_schedule_path,
  save_model_schedule,
  strategy_from_dict,
  week_entry_from_strategy,
)


@pytest.fixture()
def tmp_models_dir(tmp_path, monkeypatch):
  models = tmp_path / "trade_models"
  models.mkdir(parents=True)
  monkeypatch.setattr("trade_model_schedule.MODELS_DIR", models)
  monkeypatch.setattr("trade_model_schedule.REPORT_DIR", tmp_path)
  return models


def _sample_strat(name: str = "Forge RR3 hybrid 3L2S test #ABCD") -> MinedStrategy:
  return MinedStrategy(
    long_rules=[Rule("rsi", "long", "lt", 40.123456, 1.5)],
    short_rules=[Rule("rsi", "short", "gt", 60.987654, 2.25)],
    score_threshold=1.6,
    atr_mult_sl=0.7,
    rr_ratio=3.0,
    min_rules_match=2,
    max_trades_per_day=2,
    min_bars_between=16,
    max_hold_bars=96,
    ml_prob_min=0.358,
    exit_mode="hybrid",
    trail_activate_r=1.8,
    trail_distance_r=0.6,
    session_filter=True,
    session_start_hour=8,
    session_end_hour=17,
    name=name,
  )


def test_strategy_roundtrip_preserves_genome():
  strat = _sample_strat()
  blob = full_strategy_dict(strat)
  back = strategy_from_dict(blob)
  assert back.name == strat.name
  assert back.exit_mode == "hybrid"
  assert back.rr_ratio == 3.0
  assert back.min_bars_between == 16
  assert back.session_start_hour == 8
  assert abs(back.long_rules[0].threshold - 40.123456) < 1e-9


def test_lookup_prefers_oos_schedule_over_live(tmp_models_dir):
  mid = "tm_test_schedule"
  save_model_schedule(mid, {
    "meta": {"model_id": mid},
    "weekly": [
      week_entry_from_strategy(
        week_start="2026-01-06",
        strat=_sample_strat("oos #1111"),
        train_start_idx=100,
        train_end_idx=600,
      ),
    ],
  })
  append_live_week(mid, week_entry_from_strategy(
    week_start="2026-01-06",
    strat=_sample_strat("live #2222"),
    train_start_idx=100,
    train_end_idx=600,
  ))
  hit = lookup_week_strategy(mid, "2026-01-06")
  assert hit is not None
  assert hit["strategy"]["name"] == "oos #1111"
  assert model_schedule_path(mid).exists()
  assert model_live_weeks_path(mid).exists()


def test_bridge_uses_schedule_without_remine(tmp_models_dir, monkeypatch):
  from mt5_bridge import engine as eng_mod
  from mt5_bridge.engine import BridgeEngine

  mid = "tm_test_bridge_sched"
  strat = _sample_strat("scheduled #ZZZZ")
  save_model_schedule(mid, {
    "meta": {"model_id": mid},
    "weekly": [
      week_entry_from_strategy(
        week_start="2026-01-26",
        strat=strat,
        train_start_idx=10,
        train_end_idx=600,
      ),
    ],
  })

  called = {"n": 0}

  def _boom(*_a, **_k):
    called["n"] += 1
    raise AssertionError("optimize_on_window must not run for scheduled week")

  monkeypatch.setattr(eng_mod, "optimize_on_window", _boom)

  idx = pd.date_range("2025-01-01", periods=800, freq="15min")
  df = pd.DataFrame(
    {"Open": 1.1, "High": 1.11, "Low": 1.09, "Close": 1.1, "Volume": 100.0},
    index=idx,
  )

  class _FakeFM:
    def __init__(self, frame):
      self.n = len(frame)
      self.index = frame.index

  engine = BridgeEngine(model_id=mid)
  engine._df = df
  engine.model_id = mid
  monkeypatch.setattr(engine, "_canonical_frame", lambda: df)
  monkeypatch.setattr(engine, "_sync_working_frame_from_canonical", lambda c: df)
  monkeypatch.setattr(engine, "_feature_matrix", lambda d, p: _FakeFM(d))
  monkeypatch.setattr(eng_mod, "attach_ml_scorer", lambda strat_obj, *_a, **_k: strat_obj)

  out = engine._remine_week_strategy(
    week_start=pd.Timestamp("2026-01-26"),
    cache_key="test",
    train_weeks=3,
    use_learning=True,
    kb_profile=None,
    kb_snapshot=None,
    feature_profile="current",
    search_space=None,
  )
  assert out is not None
  assert out.name == "scheduled #ZZZZ"
  assert called["n"] == 0


def test_bridge_remine_appends_live_week(tmp_models_dir, monkeypatch):
  from mt5_bridge import engine as eng_mod
  from mt5_bridge.engine import BridgeEngine

  mid = "tm_test_live_append"
  strat = _sample_strat("fresh remine #9999")

  monkeypatch.setattr(eng_mod, "optimize_on_window", lambda *_a, **_k: strat)
  monkeypatch.setattr(eng_mod, "lookup_week_strategy", lambda *_a, **_k: None)
  monkeypatch.setattr(eng_mod, "get_train_window_indices", lambda *_a, **_k: (10, 600))

  idx = pd.date_range("2025-01-01", periods=800, freq="15min")
  df = pd.DataFrame(
    {"Open": 1.1, "High": 1.11, "Low": 1.09, "Close": 1.1, "Volume": 100.0},
    index=idx,
  )

  class _FakeFM:
    def __init__(self, frame):
      self.n = len(frame)
      self.index = frame.index

  engine = BridgeEngine(model_id=mid)
  engine._df = df
  engine.model_id = mid
  monkeypatch.setattr(engine, "_canonical_frame", lambda: df)
  monkeypatch.setattr(engine, "_sync_working_frame_from_canonical", lambda c: df)
  monkeypatch.setattr(engine, "_feature_matrix", lambda d, p: _FakeFM(d))

  out = engine._remine_week_strategy(
    week_start=pd.Timestamp("2026-07-20"),
    cache_key="live",
    train_weeks=3,
    use_learning=False,
    kb_profile=None,
    kb_snapshot=None,
    feature_profile="current",
    search_space=None,
  )
  assert out.name.startswith("fresh remine")
  hit = lookup_week_strategy(mid, "2026-07-20")
  assert hit is not None
  assert hit["strategy"]["name"] == strat.name
  assert model_live_weeks_path(mid).exists()
