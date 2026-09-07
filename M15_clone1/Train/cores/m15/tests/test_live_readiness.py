"""Live readiness checklist unit tests."""
from __future__ import annotations

from gui.live_readiness import assess_live_readiness


def test_blocked_without_model():
  out = assess_live_readiness({}, include_bridge=False)
  assert out["verdict"] == "blocked"
  assert out["ready"] is False
  assert out["n_fail"] >= 1


def test_assess_with_minimal_model(monkeypatch):
  model = {
    "id": "tm_test",
    "label": "Test model",
    "train_weeks": 6,
    "use_kb": True,
    "kb_profile": "default",
    "mining_search_space": None,
  }

  monkeypatch.setattr(
    "gui.trade_model.load_model_report", lambda *_a, **_k: None,
  )
  monkeypatch.setattr(
    "gui.trade_model.load_model_kb_off_report", lambda *_a, **_k: None,
  )
  monkeypatch.setattr(
    "gui.trade_model.load_model_remine_off_report", lambda *_a, **_k: None,
  )
  monkeypatch.setattr(
    "gui.trade_model.load_model_mining_baseline_report", lambda *_a, **_k: None,
  )
  monkeypatch.setattr(
    "gui.trade_model.format_model_label", lambda m: m.get("label") or m["id"],
  )

  out = assess_live_readiness(model, include_bridge=False)
  assert out["verdict"] == "blocked"
  keys = {i["key"]: i["status"] for i in out["items"]}
  assert keys["model"] == "pass"
  assert keys["health_on"] == "fail"


def test_ready_when_health_ok(monkeypatch):
  model = {
    "id": "tm_ok",
    "label": "OK",
    "train_weeks": 6,
    "use_kb": True,
    "kb_profile": "era_x",
    "mining_search_space": {
      "session_ranges": [[7, 20]],
      "min_bars_between": [12],
      "max_hold_bars": [96],
    },
  }
  report = {
    "overall_oos": {"total_r": 20.0, "win_rate_pct": 62.0},
    "config": {
      "mining_search_space": model["mining_search_space"],
    },
  }
  kb_off = {"overall_oos": {"total_r": 10.0, "win_rate_pct": 50.0}}

  monkeypatch.setattr(
    "gui.trade_model.load_model_report", lambda *_a, **_k: report,
  )
  monkeypatch.setattr(
    "gui.trade_model.load_model_kb_off_report", lambda *_a, **_k: kb_off,
  )
  monkeypatch.setattr(
    "gui.trade_model.load_model_remine_off_report", lambda *_a, **_k: None,
  )
  monkeypatch.setattr(
    "gui.trade_model.load_model_mining_baseline_report", lambda *_a, **_k: None,
  )
  monkeypatch.setattr(
    "gui.trade_model.report_search_space_matches_model",
    lambda *_a, **_k: True,
  )
  monkeypatch.setattr(
    "gui.trade_model.format_model_label", lambda m: m.get("label") or m["id"],
  )
  monkeypatch.setattr(
    "mining_presets.match_preset_name", lambda *_a, **_k: "elite_or_quality",
  )

  out = assess_live_readiness(model, include_bridge=False)
  assert out["ready"] is True
  assert out["verdict"] in ("ready", "caution")
  keys = {i["key"]: i["status"] for i in out["items"]}
  assert keys["health_on"] == "pass"
  assert keys["kb_off"] == "pass"
  assert keys["space"] == "warn"


def test_bridge_model_mismatch_is_fail(monkeypatch):
  model = {
    "id": "tm_active",
    "label": "Active",
    "train_weeks": 6,
    "use_kb": True,
    "mining_search_space": None,
  }
  report = {"overall_oos": {"total_r": 5.0, "win_rate_pct": 55.0}, "config": {}}
  monkeypatch.setattr("gui.trade_model.load_model_report", lambda *_a, **_k: report)
  monkeypatch.setattr("gui.trade_model.load_model_kb_off_report", lambda *_a, **_k: report)
  monkeypatch.setattr("gui.trade_model.load_model_remine_off_report", lambda *_a, **_k: None)
  monkeypatch.setattr("gui.trade_model.load_model_mining_baseline_report", lambda *_a, **_k: None)
  monkeypatch.setattr("gui.trade_model.report_search_space_matches_model", lambda *_a, **_k: True)
  monkeypatch.setattr("gui.trade_model.format_model_label", lambda m: m["id"])
  monkeypatch.setattr(
    "mt5_bridge.models.get_model_run_params",
    lambda *_a, **_k: {"train_weeks": 6},
  )
  monkeypatch.setattr(
    "mt5_bridge.models.conditions_fingerprint",
    lambda *_a, **_k: "fp_active",
  )
  monkeypatch.setattr(
    "gui.bridge_model_monitor.compare_live_week_to_oos",
    lambda *_a, **_k: {"status": "waiting_strategy", "message": "wait"},
  )

  out = assess_live_readiness(
    model,
    decision={"model_id": "tm_other", "conditions_fp": "fp_active"},
    include_bridge=True,
  )
  keys = {i["key"]: i for i in out["items"]}
  assert keys["bridge_model"]["status"] == "fail"
  assert "tm_other" in keys["bridge_model"]["detail"]
  assert out["verdict"] == "blocked"
