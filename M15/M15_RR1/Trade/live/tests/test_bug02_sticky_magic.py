"""BUG-02: disabling a model must not clear/reuse its magic."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from magic_allocator import assign_magics  # noqa: E402
from shared.constants import LIVE_MAGIC_BASE  # noqa: E402


def _row(mid: str, magic: int | None, *, enabled: bool = True, sym="EURUSD", tf="M15"):
  return {
    "model_id": mid,
    "enabled": enabled,
    "magic": magic,
    "symbol": sym,
    "timeframe": tf,
    "risk_pct": 1.0,
    "label": mid,
  }


def test_disable_keeps_magic_and_blocks_reuse():
  rows = [
    _row("tm_a", LIVE_MAGIC_BASE, enabled=True),
    _row("tm_b", LIVE_MAGIC_BASE + 1, enabled=True),
  ]
  assigned = assign_magics(rows, sim=False)
  by = {r["model_id"]: r for r in assigned}
  assert by["tm_a"]["magic"] == LIVE_MAGIC_BASE

  # User turns A off
  by["tm_a"]["enabled"] = False
  again = assign_magics(list(by.values()) + [
    _row("tm_c", None, enabled=True),  # new model must not steal A's magic
  ], sim=False)
  out = {r["model_id"]: r for r in again}
  assert out["tm_a"]["enabled"] is False
  assert out["tm_a"]["magic"] == LIVE_MAGIC_BASE  # sticky
  assert out["tm_c"]["magic"] != LIVE_MAGIC_BASE
  assert out["tm_c"]["magic"] == LIVE_MAGIC_BASE + 2  # next free after A,B reserved


def test_reenable_reuses_same_sticky_magic():
  rows = [
    _row("tm_a", LIVE_MAGIC_BASE, enabled=False),
    _row("tm_b", LIVE_MAGIC_BASE + 1, enabled=True),
  ]
  assigned = assign_magics(rows, sim=False)
  by = {r["model_id"]: r for r in assigned}
  assert by["tm_a"]["magic"] == LIVE_MAGIC_BASE
  by["tm_a"]["enabled"] = True
  again = assign_magics(list(by.values()), sim=False)
  out = {r["model_id"]: r for r in again}
  assert out["tm_a"]["magic"] == LIVE_MAGIC_BASE


def test_flatten_targets_disabled_models_with_magic(tmp_path, monkeypatch):
  """Kill/flatten must write FLAT for disabled rows that still own a magic."""
  import json
  import safety as safety_mod

  monkeypatch.setattr(safety_mod, "RESULTS_DIR", tmp_path)
  monkeypatch.setattr(safety_mod, "BRIDGE_DIR", tmp_path / "bridge_live")

  roster = {
    "models": [
      _row("tm_on", LIVE_MAGIC_BASE, enabled=True),
      _row("tm_off", LIVE_MAGIC_BASE + 1, enabled=False),
    ]
  }

  def _fake_roster():
    return roster

  monkeypatch.setattr(safety_mod, "load_roster", _fake_roster)
  bdir = tmp_path / "bridge_live_eurusd_m15"
  safety_mod.write_flatten_command(bridge_dir=bdir, reason="test_flatten")
  off = json.loads((bdir / "decisions" / "tm_off.json").read_text(encoding="utf-8"))
  on = json.loads((bdir / "decisions" / "tm_on.json").read_text(encoding="utf-8"))
  assert off["action"] == "FLAT"
  assert on["action"] == "FLAT"
