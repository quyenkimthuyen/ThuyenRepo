"""Tests for PA confluence features and retargeted fitness."""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from feature_engine import FeatureMatrix
from strategy_miner import MiningSearchSpace, score_strategy_metrics, MinedStrategy


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
  assert frontier.min_bars_between == (16,)
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
    index = pd.date_range("2026-01-05 08:00", periods=5, freq="15min")
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


def test_elite_presets_opt_in():
  from mining_presets import RECOMMENDED_PRESET, get_preset, preset_label
  from strategy_miner import mining_search_space_from_dict

  space = mining_search_space_from_dict(get_preset("elite_60_3"))
  assert space.selection_mode == "elite_frontier"
  assert space.exit_modes_full_only is True
  assert space.rr_ratios == (3.5, 4.0)
  assert space.anti_chase is True
  assert space.anti_chase_fixed_rsi == 58.0
  assert MiningSearchSpace().exit_modes_full_only is False
  assert RECOMMENDED_PRESET == "elite_or_quality"
  eoq = mining_search_space_from_dict(get_preset(RECOMMENDED_PRESET))
  assert eoq.anti_chase_use_vwap is True
  assert eoq.anti_chase_logic == "or"
  assert eoq.rr_ratios == (3.2, 3.5, 4.0)
  assert "OR-quality" in preset_label(RECOMMENDED_PRESET)
  from mining_presets import CURATED_PRESETS, DEPRECATED_PRESETS, list_curated_presets
  assert RECOMMENDED_PRESET in CURATED_PRESETS
  assert "wr_rr_frontier" in DEPRECATED_PRESETS
  assert "wr_rr_frontier" not in list_curated_presets("g23")
  assert "elite_or_quality" in list_curated_presets("g23")
  assert list_curated_presets("g23") == [
    "elite_or_quality",
    "anti_chase_fixed_70",
    "edge_gentle",
    "elite_55_4",
    "baseline",
  ]
  assert "elite_60_3_vwap" in DEPRECATED_PRESETS
  assert "frontier_rr_hi" not in list_curated_presets("g23")
  from mining_presets import recommended_preset, recommended_presets
  assert recommended_preset("g23") == "elite_or_quality"
  assert recommended_preset("e21") == "eur_r100_hyper"
  assert recommended_presets("e21") == ["eur_r100_hyper", "eur_r100_core"]
  e21_curated = list_curated_presets("e21")
  assert e21_curated[0] == "eur_r100_hyper"
  # 2026-08-31 audit: exactly 4 non-redundant presets, and the ones proven to be
  # subsets of a survivor must be gone from the Settings list.
  assert len(e21_curated) == 4
  for retired in ("eur_r100_dense", "eur_r100_elite_rr3", "eur_r100_london"):
    assert retired not in e21_curated, retired
    assert retired in DEPRECATED_PRESETS, retired
  assert "elite_or_quality" not in e21_curated
  assert "elite_or_quality" in list_curated_presets("g23")
  eur = mining_search_space_from_dict(get_preset("eur_wr55_london"))
  assert min(eur.rr_ratios) >= 2.6
  assert min(eur.atr_multipliers) >= 1.05
  assert eur.session_ranges == ((8, 17),)
  assert eur.exit_modes_full_only is True
  sniper = mining_search_space_from_dict(get_preset("eur_wr55_sniper"))
  assert sniper.selection_mode == "elite_frontier"
  assert min(sniper.rr_ratios) >= 2.8
  one = mining_search_space_from_dict(get_preset("eur_wr55_1td"))
  assert one.max_trades_per_day == 1
  two = mining_search_space_from_dict(get_preset("eur_wr55_2td"))
  assert two.max_trades_per_day == 2
  assert two.session_ranges == ((8, 17),)
  assert two.edge_surgery_min_hour_trades >= 6
  three = mining_search_space_from_dict(get_preset("eur_wr55_3td"))
  assert three.max_trades_per_day == 3
  assert three.session_ranges == ((8, 17),)
  assert min(three.rr_ratios) >= 2.6


def test_eur_r100_presets_are_veto_aware_with_freq_floor():
  """eur_wr55_* capped Total R near 24R/year: the veto deleted mined signals
  after ranking, so n stayed ~20. eur_r100_* must rank with the veto on and hold
  a trades/week floor."""
  from mining_presets import get_preset
  from strategy_miner import MiningSearchSpace, mining_search_space_from_dict

  assert MiningSearchSpace().anti_chase_score_with_veto is False
  assert MiningSearchSpace().min_trades_per_week == 0.0
  legacy = mining_search_space_from_dict(get_preset("eur_wr55_london"))
  assert legacy.anti_chase_score_with_veto is False

  for name in (
    "eur_r100_core", "eur_r100_elite", "eur_r100_elite_rr3",
    "eur_r100_london", "eur_r100_dense", "eur_r100_trend", "eur_r100_wide",
  ):
    space = mining_search_space_from_dict(get_preset(name))
    assert space.anti_chase is True, name
    assert space.anti_chase_mode == "fixed", name
    assert space.anti_chase_score_with_veto is True, name
    assert space.min_trades_per_week >= 1.2, name
    assert min(space.rr_ratios) >= 2.6, name
    assert space.force_side == "both", name

  elite = mining_search_space_from_dict(get_preset("eur_r100_elite"))
  assert elite.selection_mode == "elite_frontier"
  dense = mining_search_space_from_dict(get_preset("eur_r100_dense"))
  assert dense.max_trades_per_day == 3
  assert dense.min_trades_per_week == 3.0
  trend = mining_search_space_from_dict(get_preset("eur_r100_trend"))
  assert trend.anti_chase_fixed_rsi == 50.0
  wide = mining_search_space_from_dict(get_preset("eur_r100_wide"))
  assert wide.anti_chase_fixed_rsi == 62.0


def test_active_e21_presets_carry_no_duplicate_search_space():
  """2026-08-31 audit. The miner scans the list knobs but reads selection_mode /
  anti_chase caps / trade caps as single values, so two presets are only worth
  running separately when a scalar differs. Guard both directions: no active pair
  may agree on every scalar while one's scanned space is contained in the other's,
  and every active preset must own a scalar combination no sibling has."""
  import itertools
  from mining_presets import get_preset, list_curated_presets
  from strategy_miner import mining_search_space_from_dict

  names = list_curated_presets("e21")
  spaces = {n: mining_search_space_from_dict(get_preset(n)) for n in names}
  scalars = (
    "selection_mode", "anti_chase_fixed_rsi", "anti_chase_fixed_vwap",
    "max_trades_per_day", "min_trades_per_week", "force_side",
  )
  scanned = (
    "rr_ratios", "atr_multipliers", "score_thresholds",
    "ml_probability_thresholds", "min_rules_matches", "min_bars_between",
    "session_ranges",
  )

  fingerprints = {n: tuple(getattr(s, k) for k in scalars) for n, s in spaces.items()}
  assert len(set(fingerprints.values())) == len(names), fingerprints

  for a, b in itertools.permutations(names, 2):
    if fingerprints[a] != fingerprints[b]:
      continue
    contained = all(
      set(getattr(spaces[a], k)) <= set(getattr(spaces[b], k)) for k in scanned
    )
    assert not contained, f"{a} search space is a subset of {b}"

  # London is folded in as a scanned range, so no preset needs to own those hours.
  for name, space in spaces.items():
    assert (8, 17) in space.session_ranges, name
    assert (7, 19) in space.session_ranges, name

  # R>100 at WR>55/RR>2.5 means n>=108; on the ~34-week OOS that is tpw>=3.17.
  # Three branches must be able to get there, and core stays as the slow control.
  fast = [n for n, s in spaces.items() if s.min_trades_per_week >= 3.17]
  assert len(fast) == 3, fast
  assert spaces["eur_r100_core"].min_trades_per_week < 3.17


def test_freq_floor_penalty_and_veto_aware_scoring():
  from strategy_miner import (
    MiningSearchSpace,
    apply_breakthrough_filters,
    freq_floor_penalty,
  )

  off = MiningSearchSpace()
  assert freq_floor_penalty({"n_trades": 3}, 6.0, off) == 0.0
  floor = MiningSearchSpace(min_trades_per_week=1.5)
  # 3 trades / 6 weeks = 0.5 tpw → two thirds below the floor.
  assert freq_floor_penalty({"n_trades": 3}, 6.0, floor) > 300
  assert freq_floor_penalty({"n_trades": 9}, 6.0, floor) == 0.0
  assert freq_floor_penalty({"n_trades": 0}, 6.0, floor) == 500.0

  class _Strat:
    def __init__(self):
      self.anti_chase = False
      self.anti_chase_rsi_short_max = 100.0
      self.anti_chase_rsi_long_min = 0.0
      self.anti_chase_vwap_short_max = 99.0
      self.anti_chase_logic = "or"
      self.name = "probe"

  legacy_space = MiningSearchSpace(
    anti_chase=True, anti_chase_mode="fixed", anti_chase_fixed_rsi=55.0,
  )
  ranked = apply_breakthrough_filters(None, _Strat(), 0, 10, legacy_space, for_scoring=True)
  assert ranked.anti_chase is False

  veto_space = MiningSearchSpace(
    anti_chase=True, anti_chase_mode="fixed", anti_chase_fixed_rsi=55.0,
    anti_chase_score_with_veto=True,
  )
  ranked = apply_breakthrough_filters(None, _Strat(), 0, 10, veto_space, for_scoring=True)
  assert ranked.anti_chase is True
  assert ranked.anti_chase_rsi_long_min == 45.0


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


def test_settings_preset_help_text_cannot_drift_from_the_lineup():
  """The Settings tooltip was two hardcoded branches keyed on a preset name, so
  after e21 moved to eur_r100_* it still advertised "Elite OR-quality · RSI≥58 ·
  RR ladder 3.2–4.0" — knobs no offered preset used. It is derived now; guard that
  it describes the live recommendation and never a preset the desk dropped."""
  from mining_presets import (
    curated_presets_line,
    list_curated_presets,
    preset_label,
    recommended_direction_help,
    recommended_preset,
  )

  for desk in ("e21", "g23"):
    txt = recommended_direction_help(desk)
    assert preset_label(recommended_preset(desk)) in txt, desk
    assert txt.strip().endswith("Bỏ trống = miner baseline cũ."), desk
    # The knob summary must carry real content, not an empty blurb.
    assert len(txt) > 60, desk

  e21_txt = recommended_direction_help("e21")
  for stale in ("Elite OR-quality", "EUR WR55", "RR ladder", "RSI≥58"):
    assert stale not in e21_txt, stale

  line = curated_presets_line("e21")
  for name in list_curated_presets("e21"):
    assert name in line, name
  for retired in ("eur_wr55_london", "eur_r100_dense", "eur_r100_elite"):
    assert retired not in line, retired


def test_train_week_picker_never_drops_a_stored_window():
  """The picker offered a hardcoded [3, 6, 9] while the schema domain and the
  pipeline both use 4 and 8, so opening Settings rewrote the round's
  [4, 6, 8, 9] down to [6, 9] and silently halved the grid from 64 to 32
  combos. The picker derives its options now; guard both directions."""
  from gui.app_settings import TRAIN_WEEK_OPTIONS, _sanitize_settings
  from gui.views.settings_page import _train_week_options

  round_weeks = [4, 6, 8, 9]
  # The storage layer already accepted these — the picker was the narrow one.
  assert set(round_weeks) <= set(TRAIN_WEEK_OPTIONS)

  opts = _train_week_options({"strategy_train_weeks": round_weeks})
  for wk in round_weeks:
    assert wk in opts, wk
  kept = [t for t in round_weeks if t in opts]
  assert kept == round_weeks

  # A window outside the schema domain still survives a render round-trip.
  exotic = _train_week_options({"strategy_train_weeks": [13]})
  assert 13 in exotic
  assert set(TRAIN_WEEK_OPTIONS) <= set(exotic)

  # Junk must not crash the picker or leak into the options.
  messy = _train_week_options({"strategy_train_weeks": [6, None, "x", 8]})
  assert 6 in messy and 8 in messy
  assert all(isinstance(t, int) for t in messy)

  for bad in ({}, {"strategy_train_weeks": []}, {"strategy_train_weeks": None}):
    assert _train_week_options(bad) == sorted(TRAIN_WEEK_OPTIONS)

  # Sanity: sanitize keeps the round untouched, so 64 combos stay reachable.
  cleaned = _sanitize_settings({"strategy_train_weeks": round_weeks})
  assert cleaned["strategy_train_weeks"] == round_weeks


def test_open_settings_page_yields_to_a_pipeline_rewrite_of_train_weeks():
  """Reverting the picker domain is not enough: a page already open holds the old
  weeks in widget state and would save them back over the round the pipeline just
  wrote. An external change must win; a user's own edit must not be stomped."""
  from gui.views.settings_page import _reconcile_train_weeks, _train_week_options

  opts = _train_week_options({"strategy_train_weeks": [4, 6, 8, 9]})

  # Page opened on [6, 9]; pipeline then wrote the round's [4, 6, 8, 9].
  value, seen = _reconcile_train_weeks([4, 6, 8, 9], [6, 9], [6, 9], opts)
  assert value == [4, 6, 8, 9]
  assert seen == [4, 6, 8, 9]

  # Settings unchanged since last render → the user's edit survives.
  value, seen = _reconcile_train_weeks([4, 6, 8, 9], [4, 6, 8, 9], [6], opts)
  assert value == [6]
  assert seen == [4, 6, 8, 9]

  # First render of a fresh session adopts the stored value.
  value, seen = _reconcile_train_weeks([4, 6, 8, 9], None, None, opts)
  assert value == [4, 6, 8, 9]

  # Emptying the picker falls back rather than persisting an unusable grid.
  value, _ = _reconcile_train_weeks([4, 6, 8, 9], [4, 6, 8, 9], [], opts)
  assert value == [4, 6, 8, 9]
  value, _ = _reconcile_train_weeks([], [], [], opts)
  assert value == opts


def test_app_settings_default_mining_preset(monkeypatch):
  from gui.app_settings import DEFAULT_SETTINGS, _sanitize_settings
  assert "mining_presets" not in DEFAULT_SETTINGS
  monkeypatch.delenv("TRAINAPP_DESK", raising=False)
  cleaned = _sanitize_settings({"learning_eras": DEFAULT_SETTINGS["learning_eras"]})
  assert cleaned["mining_presets"] == ["elite_or_quality"]
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  e21 = _sanitize_settings({"learning_eras": DEFAULT_SETTINGS["learning_eras"]})
  assert e21["mining_presets"] == ["eur_r100_hyper", "eur_r100_core"]


def test_e21_wr50_short_oos_r_bar():
  import importlib.util
  import sys
  from pathlib import Path
  root = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(root))
  path = root / "scripts" / "pipeline_m15_tune.py"
  spec = importlib.util.spec_from_file_location("pipeline_m15_tune", path)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  assert mod.FILTER_WR55_SHORT_OOS["total_r_gt"] == 45.0
  assert mod.FILTER_WR55["total_r_gt"] == 100.0
  assert mod.FILTER_WR55["n_ge"] == 50

  # Verify on 2026 only. Every round must run that window under the strict bar —
  # no round may quietly use the reduced R.
  for rnd in mod.E21_WR50_ROUNDS:
    # The lineup itself is an experiment knob and moves as results come in, so pin
    # the property instead: at least two eras, all distinct, so era length is
    # actually contrasted rather than assumed.
    assert len(rnd["era_keys"]) >= 2
    assert len(set(rnd["era_keys"])) == len(rnd["era_keys"])
    assert rnd["oos_from"] == "2026-01-01"
    assert rnd["oos_to"] == "2026-08-28"
    # Both learn windows must be declared in the catalog and must end before the
    # OOS starts, otherwise the KB would be trained on the window it is scored on.
    eras = {e["key"]: e for e in rnd["catalog_eras"]}
    # The catalog may keep retired eras around so they stay selectable in the GUI
    # without a code edit; every active key must still be declared in it.
    assert set(rnd["era_keys"]) <= set(eras)
    for key, era in eras.items():
      assert era["learn_until"] < rnd["oos_from"], key
      # oos_by_profile is keyed per kb_profile, so a per-era OOS that drifted from
      # the round's window would silently score two eras on different books.
      assert era["oos_from"] == rnd["oos_from"], key
      assert era["oos_to"] == rnd["oos_to"], key
    assert len({e["kb_profile"] for e in eras.values()}) == len(eras)
    assert rnd["filter_q"]["total_r_gt"] == 100.0
    assert rnd["filter_q"]["wr_gt"] == 54.99
    assert rnd["filter_q"]["rr_gt"] == 2.5
    # Measured epoch effect (324 combos): median OOS R falls +1.07 → -0.59 from
    # epoch 1 to 4, so deeper KB evolution must stay out of the grid.
    assert rnd["epochs"] == 2

  # WR>55 at RR>2.5 pins EV at 0.925R/trade, so R>100 is exactly n≥108. Guard the
  # arithmetic: the lead round has to carry a preset allowed to fill that often,
  # otherwise the bar is unreachable no matter how good the rules are.
  lead = mod.E21_WR50_ROUNDS[0]
  oos_weeks = (
    datetime.fromisoformat(lead["oos_to"])
    - datetime.fromisoformat(lead["oos_from"])
  ).days / 7.0
  ev_per_trade = 0.55 * 2.5 - 0.45
  needed_tpw = (mod.FILTER_WR55["total_r_gt"] / ev_per_trade) / oos_weeks
  assert 3.0 < needed_tpw < 3.4
  from mining_presets import PRESETS, list_curated_presets
  floors = [
    float(PRESETS[p].get("min_trades_per_week") or 0.0) for p in lead["presets"]
  ]
  assert max(floors) >= needed_tpw
  # 2026-08-31 audit: one round of exactly the 4 audited presets. A second round
  # would re-run the same spaces, since only 4 non-redundant presets remain.
  assert len(mod.E21_WR50_ROUNDS) == 1
  assert lead["presets"] == list(list_curated_presets("e21"))
  # Three of the four must be able to reach the n>=108 bar; core is the control.
  assert sum(1 for f in floors if f >= needed_tpw) == 3


def test_roster_aggregate_sums_distinct_models():
  import importlib.util
  import sys
  from pathlib import Path
  root = Path(__file__).resolve().parents[3]
  sys.path.insert(0, str(root))
  path = root / "scripts" / "pipeline_m15_tune.py"
  spec = importlib.util.spec_from_file_location("pipeline_m15_tune", path)
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)

  filt = mod.FILTER_WR55
  rows = [
    # 3 distinct presets, each WR 60 / RR 2.6 / R 40 at n=40 → stack clears R>100.
    {"mining_preset": "a", "win_rate_pct": 60.0, "avg_rr": 2.6,
     "total_r": 40.0, "n_trades": 40, "max_drawdown_r": 5.0},
    {"mining_preset": "b", "win_rate_pct": 60.0, "avg_rr": 2.6,
     "total_r": 40.0, "n_trades": 40, "max_drawdown_r": 4.0},
    {"mining_preset": "c", "win_rate_pct": 60.0, "avg_rr": 2.6,
     "total_r": 40.0, "n_trades": 40, "max_drawdown_r": 6.0},
    # Same preset as "a" — must not be stacked twice.
    {"mining_preset": "a", "win_rate_pct": 58.0, "avg_rr": 2.7,
     "total_r": 30.0, "n_trades": 30, "max_drawdown_r": 3.0},
    # Below the WR bar — excluded.
    {"mining_preset": "d", "win_rate_pct": 40.0, "avg_rr": 2.9,
     "total_r": 90.0, "n_trades": 90, "max_drawdown_r": 8.0},
  ]
  agg = mod.roster_aggregate(rows, filt)
  assert [r["mining_preset"] for r in agg["picks"]] == ["a", "b", "c"]
  assert agg["n_trades"] == 120
  assert agg["total_r"] == 120.0
  assert abs(agg["win_rate_pct"] - 60.0) < 1e-6
  # 72 wins, 48 losses: (120 + 48) / 72 = 2.333
  assert abs(agg["avg_rr"] - (120.0 + 48) / 72) < 1e-6
  assert agg["max_drawdown_r"] == 15.0
  # RR of the summed book falls below 2.5, so the roster does not clear the bar.
  assert agg["ok"] is False

  strong = [
    {"mining_preset": p, "win_rate_pct": 60.0, "avg_rr": 3.0,
     "total_r": 50.0, "n_trades": 40, "max_drawdown_r": 4.0}
    for p in ("a", "b", "c")
  ]
  agg2 = mod.roster_aggregate(strong, filt)
  assert agg2["total_r"] == 150.0
  assert agg2["ok"] is True

  assert mod.roster_aggregate([], filt)["picks"] == []


def test_anti_chase_prefers_low_rsi_shorts():
  from strategy import Trade
  from strategy_miner import calibrate_anti_chase
  import strategy_miner as sm

  class _FM:
    n = 6
    index = pd.date_range("2026-01-05 10:00", periods=6, freq="15min")
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

