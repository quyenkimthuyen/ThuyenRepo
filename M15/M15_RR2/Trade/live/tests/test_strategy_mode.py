"""Frozen strategy mode reuses last genome and skips weekly remine."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

import strategy_mode as sm  # noqa: E402
import weekend_preremine as wp  # noqa: E402


def test_pick_carry_forward_latest_on_or_before():
  merged = {
    "2026-08-03": {"week_start": "2026-08-03", "strategy": {"name": "A"}},
    "2026-08-10": {"week_start": "2026-08-10", "strategy": {"name": "B"}},
    "2026-08-17": {"week_start": "2026-08-17", "strategy": {"name": "C"}},
  }
  hit = sm.pick_carry_forward(merged, "2026-08-17")
  assert hit["strategy"]["name"] == "C"
  hit = sm.pick_carry_forward(merged, "2026-08-24")
  assert hit["strategy"]["name"] == "C"
  hit = sm.pick_carry_forward(merged, "2026-08-12")
  assert hit["strategy"]["name"] == "B"
  assert sm.pick_carry_forward(merged, "2026-07-01") is None


def test_merge_weekly_schedule_wins_same_week():
  sched = {
    "weekly": [
      {"week_start": "2026-08-10", "strategy": {"name": "sched"}},
    ]
  }
  live = {
    "weekly": [
      {"week_start": "2026-08-10", "strategy": {"name": "live"}},
      {"week_start": "2026-08-17", "strategy": {"name": "live17"}},
    ]
  }
  merged = sm.merge_weekly(sched, live)
  assert merged["2026-08-10"]["strategy"]["name"] == "sched"
  assert merged["2026-08-17"]["strategy"]["name"] == "live17"


def test_carry_forward_uses_injected_payloads():
  sched = {"weekly": [{"week_start": "2026-08-10", "strategy": {"name": "s"}}]}
  live = {"weekly": []}
  hit = sm.carry_forward_week_strategy(
    "tm_x", "2026-08-24", schedule=sched, live_weeks=live,
  )
  assert hit["strategy"]["name"] == "s"


def test_prefs_roundtrip(tmp_path, monkeypatch):
  monkeypatch.setattr(sm, "PREFS_PATH", tmp_path / "strategy_mode.json")
  monkeypatch.delenv("LIVE_STRATEGY_MODE", raising=False)
  assert sm.strategy_mode() == "weekly"
  assert sm.frozen_enabled() is False
  sm.save_prefs({"mode": "frozen"})
  assert sm.strategy_mode() == "frozen"
  assert sm.frozen_enabled() is True
  monkeypatch.setenv("LIVE_STRATEGY_MODE", "weekly")
  assert sm.frozen_enabled() is False


def test_bootstrap_patch_skips_remine_in_frozen_mode():
  src = (LIVE / "runtime_bootstrap.py").read_text(encoding="utf-8")
  assert "frozen_missing" in src
  assert "carry_forward_week_strategy" in src
  assert 'self._last_strategy_source = "frozen"' in src
  assert "engine.lookup_week_strategy = lookup_week_strategy" in src
  assert "week cache cleared" in src
  assert "_force_remine_enabled" not in src
  assert "LIVE_REPLAY_FORCE_REMINE" not in src


def test_replay_start_does_not_set_force_remine_env():
  src = (LIVE / "replay_control.py").read_text(encoding="utf-8")
  assert '["LIVE_REPLAY_FORCE_REMINE"] = "1" if force else "0"' not in src
  gui = (LIVE / "gui" / "app.py").read_text(encoding="utf-8")
  assert "Force remine" not in gui
  assert "replay_force_remine" not in gui
  assert "Save strategy mode" not in gui
  assert "restore_widget_choice" in gui
  assert 'save_sm_prefs({"mode": sm_mode})' in gui


def test_preremine_skips_when_frozen(monkeypatch):
  import strategy_mode as sm_mod
  monkeypatch.setattr(sm_mod, "frozen_enabled", lambda: True)
  out = wp.maybe_preremine_engines({}, symbol="EURUSD", timeframe="M15")
  assert out["skipped"] is True
  assert out["reason"] == "frozen_mode"
