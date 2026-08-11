"""KB pin beside Trade Models — freeze, load preference, delete cleanup."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from trade_model_kb_pin import (
  backfill_kb_pins,
  ensure_model_kb_pin,
  load_kb_for_run,
  model_kb_pin_path,
  pin_kb_for_model,
  resolve_pin_absolute,
)


@pytest.fixture()
def pin_env(tmp_path, monkeypatch):
  models = tmp_path / "trade_models"
  models.mkdir(parents=True)
  kb_src = tmp_path / "kb_src.json"
  kb_src.write_text(json.dumps({
    "epoch_count": 3,
    "rule_stats": {},
    "genomes": [],
    "ml_experience": [],
    "rule_events": [],
    "epoch_history": [],
    "best_fitness_ever": 0,
  }), encoding="utf-8")

  monkeypatch.setattr("trade_model_kb_pin.MODELS_DIR", models)
  monkeypatch.setattr("trade_model_kb_pin.REPORT_DIR", tmp_path)

  def fake_resolve(profile, snapshot=None):
    return kb_src

  monkeypatch.setattr("trade_model_kb_pin.resolve_kb_path", fake_resolve)
  return {"models": models, "kb_src": kb_src, "root": tmp_path}


def test_pin_copies_kb_and_fingerprint(pin_env):
  meta = pin_kb_for_model("tm_demo", "era_x", 3)
  assert meta is not None
  dest = model_kb_pin_path("tm_demo")
  assert dest.exists()
  assert dest.read_bytes() == pin_env["kb_src"].read_bytes()
  assert meta["kb_fingerprint"]
  assert resolve_pin_absolute(meta["kb_pin_path"]) == dest


def test_load_prefers_pin_over_profile(pin_env, monkeypatch):
  meta = pin_kb_for_model("tm_demo", "era_x", 3)
  calls = {"n": 0}

  def boom(*_a, **_k):
    calls["n"] += 1
    raise AssertionError("profile load should not run when pin exists")

  monkeypatch.setattr("kb_profiles.load_kb", boom)
  kb = load_kb_for_run(
    use_learning=True,
    kb_profile="era_x",
    kb_snapshot=3,
    kb_pin_path=meta["kb_pin_path"],
  )
  assert kb is not None
  assert calls["n"] == 0
  assert kb.path == model_kb_pin_path("tm_demo")


def test_ensure_and_backfill(pin_env):
  m = {
    "id": "tm_bf",
    "use_kb": True,
    "kb_profile": "era_x",
    "kb_snapshot": 2,
  }
  ensure_model_kb_pin(m)
  assert m.get("kb_pin_path")
  assert model_kb_pin_path("tm_bf").exists()

  m2 = {"id": "tm_bf2", "use_kb": True, "kb_profile": "era_x", "kb_snapshot": 1}
  updated = backfill_kb_pins([m, m2])
  assert len(updated) == 1
  assert updated[0]["id"] == "tm_bf2"


def test_kb_off_skips_pin(pin_env):
  m = {"id": "tm_off", "use_kb": False, "kb_profile": "era_x", "kb_snapshot": 1}
  ensure_model_kb_pin(m)
  assert "kb_pin_path" not in m
  assert not model_kb_pin_path("tm_off").exists()
