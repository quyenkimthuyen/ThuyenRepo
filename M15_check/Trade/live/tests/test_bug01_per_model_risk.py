"""BUG-01: each Live model must keep its own risk_pct through models.json + engines.

Failing contract before fix:
- write_models_json hardcodes top-level risk_pct=1.0 (OK as fallback) but
  host write_models_roster / build_engines wipe per-model risk and stamp one %.
- EA EffectiveRiskPct only reads the top-level field → wrong lots.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

from sync_bridge_roster import write_models_json  # noqa: E402


def _rows():
  return [
    {
      "enabled": True,
      "model_id": "tm_a",
      "magic": 20263001,
      "label": "A",
      "install_id": "inst_a",
      "symbol": "EURUSD",
      "timeframe": "M15",
      "risk_pct": 2.0,
    },
    {
      "enabled": True,
      "model_id": "tm_b",
      "magic": 20263002,
      "label": "B",
      "install_id": "inst_b",
      "symbol": "EURUSD",
      "timeframe": "M15",
      "risk_pct": 0.5,
    },
  ]


def test_write_models_json_keeps_distinct_per_model_risk(tmp_path):
  path = write_models_json(tmp_path, _rows(), base_magic=20263001)
  data = json.loads(path.read_text(encoding="utf-8"))
  by_id = {m["id"]: m for m in data["models"]}
  assert by_id["tm_a"]["risk_pct"] == pytest.approx(2.0)
  assert by_id["tm_b"]["risk_pct"] == pytest.approx(0.5)
  assert by_id["tm_a"]["risk_pct"] != by_id["tm_b"]["risk_pct"]
  # Top-level is EA fallback only — must reflect first model, not hardcode 1.0
  # (legacy EA reads only this field; new EA uses per-model).
  assert data["risk_pct"] == pytest.approx(2.0)


def test_apply_per_model_risk_restores_after_uniform_roster_wipe(tmp_path):
  """Simulate host write_models_roster wipe (no per-model risk, single top-level)."""
  from model_risk import apply_per_model_risk_to_bridge

  wiped = {
    "updated_at": "2026-01-01T00:00:00+00:00",
    "risk_pct": 2.0,  # first-model-only stamp from worker
    "base_magic": 20263001,
    "models": [
      {"id": "tm_a", "magic": 20263001, "label": "A"},
      {"id": "tm_b", "magic": 20263002, "label": "B"},
    ],
  }
  (tmp_path / "models.json").write_text(
    json.dumps(wiped, indent=2) + "\n", encoding="utf-8",
  )
  out = apply_per_model_risk_to_bridge(
    tmp_path,
    risk_by_id={"tm_a": 2.0, "tm_b": 0.5},
  )
  data = json.loads((tmp_path / "models.json").read_text(encoding="utf-8"))
  by_id = {m["id"]: m for m in data["models"]}
  assert by_id["tm_a"]["risk_pct"] == pytest.approx(2.0)
  assert by_id["tm_b"]["risk_pct"] == pytest.approx(0.5)
  assert out["tm_a"] == pytest.approx(2.0)
  assert out["tm_b"] == pytest.approx(0.5)


def test_apply_per_model_risk_to_engines_sets_distinct_values():
  from model_risk import apply_per_model_risk_to_engines

  class _Eng:
    def __init__(self, mid: str, risk: float):
      self.model_id = mid
      self.risk_pct = risk

  engines = {
    "tm_a": _Eng("tm_a", 1.0),
    "tm_b": _Eng("tm_b", 1.0),
  }
  apply_per_model_risk_to_engines(engines, {"tm_a": 2.0, "tm_b": 0.5})
  assert engines["tm_a"].risk_pct == pytest.approx(2.0)
  assert engines["tm_b"].risk_pct == pytest.approx(0.5)


def test_build_engines_wrapper_restores_risk_after_host_wipe(tmp_path):
  """Host build_engines writes uniform risk; wrapper must restore per-model."""
  from model_risk import build_engines_with_per_model_risk

  class _Eng:
    def __init__(self, mid: str, risk: float):
      self.model_id = mid
      self.risk_pct = risk

  def fake_build(model_ids, *, risk_pct, bridge_dir, base_magic, existing_engines=None):
    # Simulate write_models_roster wipe
    payload = {
      "risk_pct": float(risk_pct),
      "base_magic": int(base_magic),
      "models": [
        {"id": mid, "magic": int(base_magic) + i, "label": mid}
        for i, mid in enumerate(model_ids)
      ],
    }
    (Path(bridge_dir) / "models.json").write_text(
      json.dumps(payload, indent=2) + "\n", encoding="utf-8",
    )
    return {mid: _Eng(mid, float(risk_pct)) for mid in model_ids}

  engines = build_engines_with_per_model_risk(
    fake_build,
    ["tm_a", "tm_b"],
    risk_pct=2.0,
    bridge_dir=tmp_path,
    base_magic=20263001,
    risk_by_id={"tm_a": 2.0, "tm_b": 0.5},
  )
  assert engines["tm_a"].risk_pct == pytest.approx(2.0)
  assert engines["tm_b"].risk_pct == pytest.approx(0.5)
  data = json.loads((tmp_path / "models.json").read_text(encoding="utf-8"))
  by_id = {m["id"]: m for m in data["models"]}
  assert by_id["tm_a"]["risk_pct"] == pytest.approx(2.0)
  assert by_id["tm_b"]["risk_pct"] == pytest.approx(0.5)


def test_ea_models_json_contract_includes_risk_near_each_model(tmp_path):
  """EA parses each model object for risk_pct — contract must keep it in-entry."""
  path = write_models_json(tmp_path, _rows(), base_magic=20263001)
  raw = path.read_text(encoding="utf-8")
  assert raw.count('"risk_pct"') >= 3  # top-level + 2 models
  data = json.loads(raw)
  for m in data["models"]:
    assert "risk_pct" in m
    assert float(m["risk_pct"]) > 0
