"""BUG-12: Rebuild from installed must keep sticky magics / risk from prior roster."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from shared.constants import LIVE_MAGIC_BASE  # noqa: E402


def test_rebuild_roster_preserves_sticky_magic_and_risk(monkeypatch):
  import package_store as ps

  installed = [
    {
      "install_id": "inst_a",
      "model_id": "tm_a",
      "label": "A",
      "symbol": "EURUSD",
      "timeframe": "M15",
      "ready": True,
      "has_schedule": True,
      "schedule_weeks": 10,
    },
    {
      "install_id": "inst_b",
      "model_id": "tm_b",
      "label": "B",
      "symbol": "EURUSD",
      "timeframe": "M15",
      "ready": True,
      "has_schedule": True,
      "schedule_weeks": 10,
    },
  ]
  monkeypatch.setattr(ps, "list_installed", lambda: installed)

  prev = {
    "models": [
      {
        "install_id": "inst_a",
        "model_id": "tm_a",
        "enabled": True,
        "magic": LIVE_MAGIC_BASE,
        "risk_pct": 2.0,
        "symbol": "EURUSD",
        "timeframe": "M15",
      },
      {
        "install_id": "inst_b",
        "model_id": "tm_b",
        "enabled": False,
        "magic": LIVE_MAGIC_BASE + 1,
        "risk_pct": 0.5,
        "symbol": "EURUSD",
        "timeframe": "M15",
      },
    ]
  }
  monkeypatch.setattr(ps, "load_roster", lambda: prev)

  rows = ps.rebuild_roster_preserving_sticky()
  by = {r["install_id"]: r for r in rows}
  assert by["inst_a"]["magic"] == LIVE_MAGIC_BASE
  assert by["inst_a"]["risk_pct"] == 2.0
  assert by["inst_b"]["magic"] == LIVE_MAGIC_BASE + 1
  assert by["inst_b"]["enabled"] is False
  assert by["inst_b"]["risk_pct"] == 0.5
