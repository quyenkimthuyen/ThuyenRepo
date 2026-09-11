"""Weekend pre-remine window + roster prune (Train Live Bridge)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _write(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_quality_status_week_preremine_on_friday_evening(monkeypatch):
  from mt5_bridge import weekend_preremine as wp

  week, mode = wp.quality_status_week(pd.Timestamp("2026-08-21 19:00:00"))
  assert week == "2026-08-24"
  assert mode == "preremine"


def test_quality_status_week_trading_on_monday():
  from mt5_bridge import weekend_preremine as wp

  week, mode = wp.quality_status_week(pd.Timestamp("2026-08-17 21:00:00"))
  assert week == "2026-08-17"
  assert mode == "trading"


def test_prune_drops_removed_models(tmp_path, monkeypatch):
  from mt5_bridge import weekend_preremine as wp

  monkeypatch.setattr(wp, "STATE_PATH", tmp_path / "weekend_preremine.json")
  _write(
    tmp_path / "weekend_preremine.json",
    {
      "models": {
        "tm_keep": {"week_start": "2026-08-24", "ok": True, "source": "live_remine"},
        "tm_gone": {"week_start": "2026-08-24", "ok": True, "source": "live_remine"},
      }
    },
  )
  out = wp.prune_preremine_to_roster(["tm_keep"])
  assert out["dropped"] == ["tm_gone"]
  kept = json.loads((tmp_path / "weekend_preremine.json").read_text(encoding="utf-8"))
  assert set(kept["models"]) == {"tm_keep"}


def test_maybe_preremine_skips_outside_window(monkeypatch):
  from mt5_bridge import weekend_preremine as wp

  monkeypatch.setattr(wp, "weekend_preremine_target", lambda: None)
  out = wp.maybe_preremine_engines({})
  assert out["skipped"] is True
  assert out["reason"] == "outside_window"


def test_maybe_preremine_skips_when_freeze_strat_in_memory(monkeypatch, tmp_path):
  from mt5_bridge import weekend_preremine as wp

  monkeypatch.setattr(wp, "STATE_PATH", tmp_path / "weekend_preremine.json")
  monkeypatch.setattr(wp, "weekend_preremine_target", lambda: wp.next_week_start())
  monkeypatch.setattr(
    "mt5_bridge.background.load_config_cached",
    lambda **_: {"remine_each_week": False, "weekend_preremine_enabled": True},
  )

  class _Eng:
    model_id = "tm_freeze_skip"
    _frozen_strat = object()
    _last_remine_source = "frozen"

    def prewarm_week(self, _ts):
      raise AssertionError("prewarm_week must not run when frozen_strat set")

  out = wp.maybe_preremine_engines({"tm_freeze_skip": _Eng()}, force=True)
  assert out["skipped"] is False
  assert out["models"][0]["action"] == "skip_freeze"
  assert out["models"][0]["ok"] is True


def test_load_config_cached_avoids_repeated_disk_reads(monkeypatch):
  from mt5_bridge import background as bg

  bg.invalidate_config_cache()
  calls = {"n": 0}
  real = bg.load_config

  def _counting_load():
    calls["n"] += 1
    return real()

  monkeypatch.setattr(bg, "load_config", _counting_load)
  bg.load_config_cached(force=True)
  bg.load_config_cached()
  bg.load_config_cached()
  assert calls["n"] == 1
  bg.invalidate_config_cache()
  bg.load_config_cached()
  assert calls["n"] == 2
