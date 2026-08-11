"""Assign Live magic numbers (isolated from lab desks)."""
from __future__ import annotations

import sys
from pathlib import Path

SPLIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPLIT))

from shared.constants import LIVE_MAGIC_BASE, LIVE_MAX_MODELS, LIVE_SIM_MAGIC_BASE  # noqa: E402


def assign_magics(roster_models: list[dict], *, sim: bool = False) -> list[dict]:
  base = LIVE_SIM_MAGIC_BASE if sim else LIVE_MAGIC_BASE
  out = []
  i = 0
  for row in roster_models:
    row = dict(row)
    if not row.get("enabled", True):
      row["magic"] = None
      out.append(row)
      continue
    if i >= LIVE_MAX_MODELS:
      row["enabled"] = False
      row["magic"] = None
      row["disabled_reason"] = f"exceeds LIVE_MAX_MODELS={LIVE_MAX_MODELS}"
      out.append(row)
      continue
    row["magic"] = int(base) + i
    i += 1
    out.append(row)
  return out
