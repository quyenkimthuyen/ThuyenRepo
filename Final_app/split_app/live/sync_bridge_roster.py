#!/usr/bin/env python3
"""Sync enabled models → per-book bridge_*/models.json for ForgeBridgeLive."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path(__file__).resolve().parent
SPLIT = LIVE.parent
sys.path.insert(0, str(SPLIT))
sys.path.insert(0, str(LIVE))

from books import bridge_dir, group_models_by_book  # noqa: E402
from live_config import BRIDGE_DIR, BRIDGE_SIM_DIR  # noqa: E402
from magic_allocator import assign_magics  # noqa: E402
from package_store import default_roster_from_installed, load_roster, save_roster  # noqa: E402
from shared.constants import LIVE_MAGIC_BASE, LIVE_SIM_MAGIC_BASE  # noqa: E402


def write_models_json(bridge_dir: Path, rows: list[dict], *, base_magic: int) -> Path:
  bridge_dir.mkdir(parents=True, exist_ok=True)
  (bridge_dir / "decisions").mkdir(exist_ok=True)
  models = []
  for r in rows:
    if not r.get("enabled") or not r.get("magic"):
      continue
    models.append({
      "id": r.get("model_id"),
      "magic": int(r["magic"]),
      "label": r.get("label") or r.get("model_id"),
      "install_id": r.get("install_id"),
      "symbol": r.get("symbol"),
      "timeframe": r.get("timeframe"),
      "risk_pct": float(r.get("risk_pct") or 1.0),
    })
  payload = {
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "risk_pct": 1.0,
    "base_magic": int(base_magic),
    "models": models,
  }
  path = bridge_dir / "models.json"
  path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return path


def main() -> int:
  roster = load_roster()
  models = roster.get("models") or default_roster_from_installed()
  live_rows = assign_magics(models, sim=False)
  save_roster(live_rows, active_book=roster.get("active_book"))
  sim_rows = assign_magics(live_rows, sim=True)

  enabled_live = [r for r in live_rows if r.get("enabled")]
  enabled_sim = [r for r in sim_rows if r.get("enabled")]
  groups_live = group_models_by_book(enabled_live)
  groups_sim = group_models_by_book(enabled_sim)
  if not groups_live:
    write_models_json(BRIDGE_DIR, [], base_magic=LIVE_MAGIC_BASE)
    write_models_json(BRIDGE_SIM_DIR, [], base_magic=LIVE_SIM_MAGIC_BASE)
    print("No enabled models")
    return 0

  first = True
  for (sym, tf), rows in groups_live.items():
    p = write_models_json(bridge_dir(sym, tf, sim=False), rows, base_magic=LIVE_MAGIC_BASE)
    sim_book = groups_sim.get((sym, tf), [])
    write_models_json(bridge_dir(sym, tf, sim=True), sim_book, base_magic=LIVE_SIM_MAGIC_BASE)
    if first:
      write_models_json(BRIDGE_DIR, rows, base_magic=LIVE_MAGIC_BASE)
      write_models_json(BRIDGE_SIM_DIR, sim_book, base_magic=LIVE_SIM_MAGIC_BASE)
      first = False
    print(f"Wrote {p} ({len(rows)} models) {sym} {tf}")
    for r in rows:
      print(f"  live magic={r.get('magic')} {r.get('label')}")
    for r in sim_book:
      print(f"  sim  magic={r.get('magic')} {r.get('label')}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
