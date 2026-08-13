"""Assign Live magic numbers (isolated from lab desks)."""
from __future__ import annotations

import sys
from pathlib import Path

SPLIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPLIT))

from shared.constants import (  # noqa: E402
  LIVE_MAGIC_BASE,
  LIVE_MAX_MODELS,
  LIVE_MAX_MODELS_PER_CHART,
  LIVE_SIM_MAGIC_BASE,
)


def assign_magics(roster_models: list[dict], *, sim: bool = False) -> list[dict]:
  """Unique magics for enabled models; max per chart (symbol+TF) and global."""
  base = LIVE_SIM_MAGIC_BASE if sim else LIVE_MAGIC_BASE
  out: list[dict] = []
  global_i = 0
  per_book: dict[tuple[str, str], int] = {}
  for row in roster_models:
    row = dict(row)
    if not row.get("enabled", True):
      row["magic"] = None
      row.pop("disabled_reason", None)
      out.append(row)
      continue
    sym = str(row.get("symbol") or "").upper()
    tf = str(row.get("timeframe") or "").upper()
    book = (sym, tf)
    n_book = per_book.get(book, 0)
    if global_i >= LIVE_MAX_MODELS:
      row["enabled"] = False
      row["magic"] = None
      row["disabled_reason"] = f"exceeds LIVE_MAX_MODELS={LIVE_MAX_MODELS}"
      out.append(row)
      continue
    if n_book >= LIVE_MAX_MODELS_PER_CHART:
      row["enabled"] = False
      row["magic"] = None
      row["disabled_reason"] = (
        f"max {LIVE_MAX_MODELS_PER_CHART} models per chart ({sym} {tf})"
      )
      out.append(row)
      continue
    row["magic"] = int(base) + global_i
    row.pop("disabled_reason", None)
    global_i += 1
    per_book[book] = n_book + 1
    out.append(row)
  return out
