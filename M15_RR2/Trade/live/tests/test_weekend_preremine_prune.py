"""Pre-remine UI state must drop removed / re-imported models."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

import weekend_preremine as wp  # noqa: E402


def _write(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_prune_drops_removed_and_reimported(tmp_path, monkeypatch):
  monkeypatch.setattr(wp, "RESULTS_DIR", tmp_path)
  _write(
    tmp_path / "weekend_preremine_eurusd_m15.json",
    {
      "models": {
        "tm_keep": {
          "week_start": "2026-08-17",
          "ok": True,
          "source": "schedule_hit",
          "updated_at": "2026-08-17T21:00:00+07:00",
        },
        "tm_old": {
          "week_start": "2026-08-17",
          "ok": True,
          "source": "remine",
          "updated_at": "2026-08-15T08:00:00+07:00",
        },
        "tm_reimport": {
          "week_start": "2026-08-17",
          "ok": True,
          "source": "schedule_fallback",
          "updated_at": "2026-08-15T08:00:00+07:00",
        },
      }
    },
  )
  _write(
    tmp_path / "weekend_preremine.json",
    {
      "books": {
        "eurusd_m5": {
          "models": {
            "tm_m5_gone": {
              "week_start": "2026-08-17",
              "ok": True,
              "source": "schedule_hit",
              "updated_at": "2026-08-15T08:00:00+07:00",
            }
          }
        }
      }
    },
  )
  live = [
    {
      "symbol": "EURUSD",
      "timeframe": "M15",
      "model_id": "tm_keep",
      "installed_at": "2026-08-17T20:00:00+07:00",
    },
    {
      "symbol": "EURUSD",
      "timeframe": "M15",
      "model_id": "tm_reimport",
      "installed_at": "2026-08-17T20:49:00+07:00",
    },
  ]
  out = wp.prune_preremine_to_live_models(live)
  reasons = {(d["model_id"], d["reason"]) for d in out["dropped"]}
  assert ("tm_old", "removed") in reasons
  assert ("tm_reimport", "reimport") in reasons
  assert ("tm_m5_gone", "removed") in reasons
  kept = json.loads((tmp_path / "weekend_preremine_eurusd_m15.json").read_text(encoding="utf-8"))
  assert set(kept["models"]) == {"tm_keep"}
  legacy = json.loads((tmp_path / "weekend_preremine.json").read_text(encoding="utf-8"))
  assert "eurusd_m5" not in (legacy.get("books") or {})


def test_prune_reimport_keeps_installed_at_when_roster_lacks_it(tmp_path, monkeypatch):
  monkeypatch.setattr(wp, "RESULTS_DIR", tmp_path)
  _write(
    tmp_path / "weekend_preremine_eurusd_m15.json",
    {
      "models": {
        "tm_reimport": {
          "week_start": "2026-08-17",
          "ok": True,
          "source": "schedule_fallback",
          "updated_at": "2026-08-15T08:00:00+07:00",
        },
      }
    },
  )
  live = [
    {
      "symbol": "EURUSD",
      "timeframe": "M15",
      "model_id": "tm_reimport",
      "installed_at": "2026-08-17T20:49:00+07:00",
    },
    {
      "symbol": "EURUSD",
      "timeframe": "M15",
      "model_id": "tm_reimport",
    },
  ]
  out = wp.prune_preremine_to_live_models(live)
  assert any(d["reason"] == "reimport" for d in out["dropped"])
  assert not (tmp_path / "weekend_preremine_eurusd_m15.json").exists()


def test_drop_preremine_model(tmp_path, monkeypatch):
  monkeypatch.setattr(wp, "RESULTS_DIR", tmp_path)
  _write(
    tmp_path / "weekend_preremine_gbpusd_m15.json",
    {
      "models": {
        "tm_a": {"week_start": "2026-08-17", "ok": True, "source": "remine"},
        "tm_b": {"week_start": "2026-08-17", "ok": True, "source": "remine"},
      }
    },
  )
  assert wp.drop_preremine_model("GBPUSD", "M15", "tm_a")
  data = json.loads((tmp_path / "weekend_preremine_gbpusd_m15.json").read_text(encoding="utf-8"))
  assert set(data["models"]) == {"tm_b"}


def test_quality_status_week_is_trading_week_on_monday():
  week, mode = wp.quality_status_week(pd.Timestamp("2026-08-17 21:00:00"))
  assert week == "2026-08-17"
  assert mode == "trading"
  week2, mode2 = wp.quality_status_week(pd.Timestamp("2026-08-21 19:00:00"))
  assert week2 == "2026-08-24"
  assert mode2 == "preremine"


def test_freeze_info_for_week_reads_live_weeks(tmp_path, monkeypatch):
  monkeypatch.setattr(wp, "RESULTS_DIR", tmp_path)
  p = tmp_path / "trade_models"
  p.mkdir()
  _write(
    p / "tm_x_live_weeks.json",
    {
      "meta": {"source": "live_remine"},
      "weekly": [{"week_start": "2026-08-17", "strategy": {"name": "Forge"}}],
    },
  )
  info = wp.freeze_info_for_week("tm_x", "2026-08-17")
  assert info["ok"] is True
  assert info["source"] == "remine"
  assert wp.freeze_info_for_week("tm_x", "2026-08-24") == {}
