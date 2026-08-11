#!/usr/bin/env python3
"""Sync enabled installed models → mt5/bridge_live/models.json for ForgeBridgeLive."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path(__file__).resolve().parent
SPLIT = LIVE.parent
sys.path.insert(0, str(SPLIT))
sys.path.insert(0, str(LIVE))

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
  sim_rows = assign_magics(models, sim=True)
  save_roster(live_rows)
  p1 = write_models_json(BRIDGE_DIR, live_rows, base_magic=LIVE_MAGIC_BASE)
  # sim uses same logical models, sim magic block
  write_models_json(BRIDGE_SIM_DIR, sim_rows, base_magic=LIVE_SIM_MAGIC_BASE)
  print(f"Wrote {p1} ({sum(1 for r in live_rows if r.get('enabled'))} enabled)")
  for r in live_rows:
    if r.get("enabled"):
      print(f"  magic={r.get('magic')} {r.get('label')} {r.get('symbol')} {r.get('timeframe')}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
