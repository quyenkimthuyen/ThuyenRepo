"""Grid Search must not score a KB against an overlapping OOS window."""
from __future__ import annotations

from gui.app_settings import (
  DEFAULT_LEARNING_ERAS,
  DEFAULT_OOS_WINDOW_KEYS,
  OOS_WALKFORWARD_ERAS,
  _append_oos_window,
  _sanitize_settings,
  count_valid_kb_oos_slots,
  describe_kb_oos_pairs,
  get_oos_window_catalog,
  kb_learn_overlaps_oos,
  periods_overlap,
  resolve_oos_windows,
)
from gui.grid_search_engine import build_grid, expected_grid_count_from_settings


def _settings(**kw) -> dict:
  catalog = [dict(e) for e in DEFAULT_LEARNING_ERAS] + [dict(e) for e in OOS_WALKFORWARD_ERAS]
  catalog.append({
    "key": "2025-full",
    "label": "2025 (12 tháng)",
    "learn_from": "2025-01-01",
    "learn_until": "2025-12-31",
    "kb_profile": "era_2025_full",
  })
  catalog.append({
    "key": "2025-q4",
    "label": "2025 (3 tháng cuối)",
    "learn_from": "2025-10-01",
    "learn_until": "2025-12-31",
    "kb_profile": "era_2025_q4",
  })
  base = {
    "learning_eras": catalog,
    "learning_era_keys": ["2025-h1"],
    "oos_window_keys": ["2026-h1", "2025-h2"],
    "strategy_train_weeks": [8],
    "learning_loops": 1,
    "mining_presets": ["eur_fill_ss_lab"],
    "backtest_from": "2026-01-01",
    "backtest_to": "2026-06-30",
  }
  base.update(kw)
  return _sanitize_settings(base)


def test_adjacent_learn_oos_is_not_overlap():
  assert not periods_overlap("2025-01-01", "2025-06-30", "2025-07-01", "2025-12-31")
  assert not kb_learn_overlaps_oos("2025-01-01", "2025-06-30", "2025-07-01", "2025-12-31")
  assert kb_learn_overlaps_oos("2025-07-01", "2025-12-31", "2025-07-01", "2025-12-31")
  assert kb_learn_overlaps_oos("2025-01-01", "2025-12-31", "2025-07-01", "2025-12-31")
  assert kb_learn_overlaps_oos("2025-10-01", "2025-12-31", "2025-07-01", "2025-12-31")
  assert not kb_learn_overlaps_oos("2025-07-01", "2025-12-31", "2026-01-01", "2026-06-30")


def test_sanitize_defaults_primary_oos_is_2026_h1():
  cleaned = _sanitize_settings({"learning_eras": DEFAULT_LEARNING_ERAS})
  assert cleaned["oos_window_keys"] == list(DEFAULT_OOS_WINDOW_KEYS) == ["2026-h1"]
  windows = resolve_oos_windows(cleaned)
  spans = {(w["oos_from"], w["oos_to"]) for w in windows}
  assert spans == {("2026-01-01", "2026-06-30")}
  assert [w["key"] for w in cleaned["oos_windows"]] == ["2026-h1", "2025-h2"]


def test_2025_h1_scores_both_windows_h2_skips_self():
  h1 = _settings(learning_era_keys=["2025-h1"])
  pairs = describe_kb_oos_pairs(h1)
  assert {(p["oos_key"], p["ok"]) for p in pairs} == {("2026-h1", True), ("2025-h2", True)}
  assert count_valid_kb_oos_slots(h1) == 2

  h2 = _settings(learning_era_keys=["2025-h2"])
  pairs_h2 = describe_kb_oos_pairs(h2)
  by_key = {p["oos_key"]: p["ok"] for p in pairs_h2}
  assert by_key["2026-h1"] is True
  assert by_key["2025-h2"] is False
  assert count_valid_kb_oos_slots(h2) == 1

  full = _settings(learning_era_keys=["2025-full"])
  assert count_valid_kb_oos_slots(full) == 1
  q4 = _settings(learning_era_keys=["2025-q4"])
  assert count_valid_kb_oos_slots(q4) == 1


def test_build_grid_skips_overlapping_kb_oos(monkeypatch):
  monkeypatch.setattr(
    "gui.grid_search_engine.kb_valid_for_backtest",
    lambda *a, **k: (True, "ok"),
  )
  windows = [("2026-01-01", "2026-06-30"), ("2025-07-01", "2025-12-31")]
  specs = build_grid(
    train_weeks=[8],
    kb_profiles=["era_2025_h2", "era_2025_h1"],
    include_kb_off=False,
    epoch_mode="selected",
    selected_epochs={"era_2025_h2": [1], "era_2025_h1": [1]},
    oos_from="2026-01-01",
    oos_to="2026-06-30",
    oos_windows=windows,
    kb_learn_by_profile={
      "era_2025_h2": ("2025-07-01", "2025-12-31"),
      "era_2025_h1": ("2025-01-01", "2025-06-30"),
    },
    mining_presets=["eur_fill_ss_lab"],
    max_runs=200,
  )
  got = {(s.kb_profile, s.oos_from, s.oos_to) for s in specs}
  assert ("era_2025_h2", "2026-01-01", "2026-06-30") in got
  assert ("era_2025_h2", "2025-07-01", "2025-12-31") not in got
  assert ("era_2025_h1", "2026-01-01", "2026-06-30") in got
  assert ("era_2025_h1", "2025-07-01", "2025-12-31") in got
  assert len(specs) == 3


def test_expected_count_uses_valid_pairs_only():
  h1 = _settings(learning_era_keys=["2025-h1"], strategy_train_weeks=[8, 12], learning_loops=3)
  # 2 trains × 2 OOS × 3 epochs × 1 preset
  assert expected_grid_count_from_settings(h1) == 12
  h2 = _settings(learning_era_keys=["2025-h2"], strategy_train_weeks=[6, 8], learning_loops=3)
  # 2025-h2 × 2025-h2 OOS skipped → only 2026-h1
  assert expected_grid_count_from_settings(h2) == 6


def test_add_custom_oos_window_to_catalog():
  s = _settings(learning_era_keys=["2025-h1"], oos_window_keys=["2026-h1"])
  s2 = _append_oos_window(
    s,
    label="2024 (6 tháng cuối)",
    oos_from="2024-07-01",
    oos_to="2024-12-31",
    activate=True,
  )
  keys = [w["key"] for w in get_oos_window_catalog(s2)]
  assert "2026-h1" in keys
  assert any(w["oos_from"] == "2024-07-01" and w["oos_to"] == "2024-12-31" for w in get_oos_window_catalog(s2))
  assert "2026-h1" in s2["oos_window_keys"]
  spans = {(w["oos_from"], w["oos_to"]) for w in resolve_oos_windows(s2)}
  assert ("2026-01-01", "2026-06-30") in spans
  assert ("2024-07-01", "2024-12-31") in spans
  # Adjacent to 2025-h1 learn (2025-01-01→06-30) — both windows valid.
  assert count_valid_kb_oos_slots(s2) == 2

  dropped = [w for w in get_oos_window_catalog(s2) if not (w["oos_from"] == "2024-07-01")]
  s3 = dict(s2)
  s3["oos_windows"] = dropped
  s3["oos_window_keys"] = [k for k in s2["oos_window_keys"] if k in {w["key"] for w in dropped}]
  s3 = _sanitize_settings(s3)
  spans3 = {(w["oos_from"], w["oos_to"]) for w in resolve_oos_windows(s3)}
  assert ("2024-07-01", "2024-12-31") not in spans3
  assert ("2026-01-01", "2026-06-30") in spans3


def test_cannot_add_duplicate_oos_span():
  s = _settings()
  try:
    _append_oos_window(
      s,
      label="2026 copy",
      oos_from="2026-01-01",
      oos_to="2026-06-30",
    )
  except ValueError as exc:
    assert "đã có" in str(exc)
  else:
    raise AssertionError("expected duplicate OOS to fail")
