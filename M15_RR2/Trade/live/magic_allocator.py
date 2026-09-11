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


def _parse_magic(raw, *, base: int) -> int | None:
  try:
    if raw is None:
      return None
    m = int(raw)
  except (TypeError, ValueError):
    return None
  if m < int(base):
    return None
  return m


def assign_magics(roster_models: list[dict], *, sim: bool = False) -> list[dict]:
  """Unique magics for enabled models; max per chart (symbol+TF) and global.

  Prefer keeping an existing magic when still unique — avoids orphaning MT5
  tickets after Rebuild roster / restart.

  Disabled rows keep their magic and reserve it so a later model cannot reuse
  the number while an unmanaged ticket may still be open (BUG-02).
  """
  base = LIVE_SIM_MAGIC_BASE if sim else LIVE_MAGIC_BASE
  out: list[dict] = []
  used: set[int] = set()
  per_book: dict[tuple[str, str], int] = {}

  # First pass: reserve sticky magics for every row (enabled + disabled).
  sticky: list[dict] = []
  for row in roster_models:
    row = dict(row)
    m = _parse_magic(row.get("magic"), base=base)
    if m is not None and m not in used:
      row["magic"] = m
      used.add(m)
    else:
      # Invalid / colliding magic — drop; enabled rows get a fresh one below.
      row["magic"] = None
    if not row.get("enabled", True):
      row.pop("disabled_reason", None)
    sticky.append(row)

  next_magic = int(base)

  def _alloc() -> int | None:
    nonlocal next_magic
    while next_magic in used:
      next_magic += 1
    if next_magic >= int(base) + LIVE_MAX_MODELS:
      return None
    m = next_magic
    used.add(m)
    next_magic += 1
    return m

  for row in sticky:
    if not row.get("enabled", True):
      # Keep sticky magic (already reserved). Never allocate while Off.
      out.append(row)
      continue
    sym = str(row.get("symbol") or "").upper()
    tf = str(row.get("timeframe") or "").upper()
    book = (sym, tf)
    n_book = per_book.get(book, 0)
    if row.get("magic") is None and len(used) >= LIVE_MAX_MODELS:
      row["enabled"] = False
      row["disabled_reason"] = f"exceeds LIVE_MAX_MODELS={LIVE_MAX_MODELS}"
      out.append(row)
      continue
    if n_book >= LIVE_MAX_MODELS_PER_CHART:
      row["enabled"] = False
      # Keep sticky magic reserved so it cannot be hijacked.
      row["disabled_reason"] = (
        f"max {LIVE_MAX_MODELS_PER_CHART} models per chart ({sym} {tf})"
      )
      out.append(row)
      continue
    if row.get("magic") is None:
      m = _alloc()
      if m is None:
        row["enabled"] = False
        row["magic"] = None
        row["disabled_reason"] = f"exceeds LIVE_MAX_MODELS={LIVE_MAX_MODELS}"
        out.append(row)
        continue
      row["magic"] = m
    row.pop("disabled_reason", None)
    per_book[book] = n_book + 1
    out.append(row)
  return out
