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
  assert back.tp_ignores_spread_buffer is False
  assert abs(back.long_rules[0].threshold - 40.123456) < 1e-9


def test_strategy_roundtrip_tp_geometry():
  strat = _sample_strat()
  strat.tp_ignores_spread_buffer = True
  strat.min_atr_spread_ratio = 5.0
  back = strategy_from_dict(full_strategy_dict(strat))
  assert back.tp_ignores_spread_buffer is True
  assert back.min_atr_spread_ratio == 5.0


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


def test_lookup_prefers_forced_live_over_schedule(tmp_models_dir):
  from trade_model_schedule import lookup_week_strategy_with_source

  mid = "tm_test_forced"
  save_model_schedule(mid, {
    "meta": {"model_id": mid},
    "weekly": [
      week_entry_from_strategy(
        week_start="2026-08-24",
        strat=_sample_strat("oos #old"),
        train_start_idx=100,
        train_end_idx=600,
      ),
    ],
  })
  append_live_week(mid, week_entry_from_strategy(
    week_start="2026-08-24",
    strat=_sample_strat("manual #new"),
    train_start_idx=100,
    train_end_idx=600,
    forced=True,
  ))
  hit, src = lookup_week_strategy_with_source(mid, "2026-08-24")
  assert src == "manual_remine"
  assert hit["strategy"]["name"] == "manual #new"


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
  monkeypatch.setattr(
    eng_mod, "lookup_week_strategy_with_source", lambda *_a, **_k: (None, None),
  )
  monkeypatch.setattr(eng_mod, "get_train_window_indices", lambda *_a, **_k: (10, 600))
  from mt5_bridge.background import invalidate_config_cache
  invalidate_config_cache()
  monkeypatch.setattr(
    "mt5_bridge.background.load_config_cached",
    lambda **_: {"remine_each_week": True},
  )

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


def test_bridge_freeze_first_skips_second_remine(tmp_models_dir, monkeypatch):
  from mt5_bridge import engine as eng_mod
  from mt5_bridge.engine import BridgeEngine

  mid = "tm_test_freeze"
  strat = _sample_strat("frozen #7777")
  calls = {"n": 0}

  def _opt(*_a, **_k):
    calls["n"] += 1
    return strat

  monkeypatch.setattr(eng_mod, "optimize_on_window", _opt)
  monkeypatch.setattr(
    eng_mod, "lookup_week_strategy_with_source", lambda *_a, **_k: (None, None),
  )
  monkeypatch.setattr(eng_mod, "get_train_window_indices", lambda *_a, **_k: (10, 600))
  monkeypatch.setattr(eng_mod, "append_live_week", lambda *_a, **_k: (_ for _ in ()).throw(
    AssertionError("append_live_week must not run when remine_each_week=False"),
  ))

  from mt5_bridge.background import invalidate_config_cache
  invalidate_config_cache()
  monkeypatch.setattr(
    "mt5_bridge.background.load_config_cached",
    lambda **_: {"remine_each_week": False},
  )

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

  w1 = pd.Timestamp("2026-07-20")
  w2 = pd.Timestamp("2026-07-27")
  out1 = engine._remine_week_strategy(
    week_start=w1,
    cache_key="w1",
    train_weeks=3,
    use_learning=False,
    kb_profile=None,
    kb_snapshot=None,
    feature_profile="current",
    search_space=None,
  )
  out2 = engine._remine_week_strategy(
    week_start=w2,
    cache_key="w2",
    train_weeks=3,
    use_learning=False,
    kb_profile=None,
    kb_snapshot=None,
    feature_profile="current",
    search_space=None,
  )
  assert out1.name == strat.name
  assert out2.name == strat.name
  assert calls["n"] == 1
  assert engine._last_remine_source == "frozen"


def test_force_remine_skips_schedule_and_writes_live_weeks(tmp_models_dir, monkeypatch):
  from mt5_bridge import engine as eng_mod
  from mt5_bridge.engine import BridgeEngine
  from trade_model_schedule import lookup_week_strategy_with_source

  mid = "tm_test_force_remine"
  scheduled = _sample_strat("scheduled #OLD")
  fresh = _sample_strat("forced #NEW")
  save_model_schedule(mid, {
    "meta": {"model_id": mid},
    "weekly": [
      week_entry_from_strategy(
        week_start="2026-08-24",
        strat=scheduled,
        train_start_idx=10,
        train_end_idx=600,
      ),
    ],
  })
  monkeypatch.setattr(eng_mod, "optimize_on_window", lambda *_a, **_k: fresh)
  from mt5_bridge.background import invalidate_config_cache
  invalidate_config_cache()
  monkeypatch.setattr(
    "mt5_bridge.background.load_config_cached",
    lambda **_: {"remine_each_week": True},
  )

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
  monkeypatch.setattr(eng_mod, "get_train_window_indices", lambda *_a, **_k: (10, 600))

  kept = engine._remine_week_strategy(
    week_start=pd.Timestamp("2026-08-24"),
    cache_key="sched",
    train_weeks=3,
    use_learning=False,
    kb_profile=None,
    kb_snapshot=None,
    feature_profile="current",
    search_space=None,
  )
  assert kept.name.startswith("scheduled")

  out = engine._remine_week_strategy(
    week_start=pd.Timestamp("2026-08-24"),
    cache_key="force",
    train_weeks=3,
    use_learning=False,
    kb_profile=None,
    kb_snapshot=None,
    feature_profile="current",
    search_space=None,
    force=True,
  )
  assert out.name.startswith("forced")
  assert engine._last_remine_source == "manual_remine"
  hit, src = lookup_week_strategy_with_source(mid, "2026-08-24")
  assert src == "manual_remine"
  assert hit["forced"] is True
  assert hit["strategy"]["name"] == fresh.name

