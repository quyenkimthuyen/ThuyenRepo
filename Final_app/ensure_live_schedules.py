#!/usr/bin/env python3
"""Backfill missing Trade Model schedules on Final_app desks (required for Live parity)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

FINAL = Path(__file__).resolve().parent
PY = Path("/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python")

DESKS = [
  "EdgeMinerEURUSDM15",
  "EdgeMinerGBPUSDM15",
  "EdgeMinerEURUSDM5",
  "EdgeMinerGBPUSDM5",
]


def models_needing_schedule(desk: Path, *, only_ids: set[str] | None = None) -> list[str]:
  store = json.loads((desk / "results" / "trade_models.json").read_text(encoding="utf-8"))
  out = []
  for m in store.get("models") or []:
    if m.get("archived"):
      continue
    mid = str(m.get("id") or "")
    if only_ids is not None and mid not in only_ids:
      continue
    sched = desk / "results" / "trade_models" / f"{mid}_schedule.json"
    if not sched.exists():
      out.append(mid)
      continue
    try:
      data = json.loads(sched.read_text(encoding="utf-8"))
      if not (data.get("weekly") or []):
        out.append(mid)
    except Exception:
      out.append(mid)
  return out


def export_schedule(desk: Path, model_id: str) -> int:
  script = desk / "scripts" / "export_model_schedule.py"
  if not script.exists():
    print(f"SKIP {desk.name}: no export_model_schedule.py", flush=True)
    return 2
  cmd = [str(PY), str(script), "--model-id", model_id, "--quiet"]
  print(f"==> {desk.name} {model_id}", flush=True)
  return subprocess.run(cmd, cwd=str(desk)).returncode


def sync_schedule_into_packages(desk: Path, model_id: str) -> int:
  """Copy lab schedule.json into matching Live installed package dirs."""
  src = desk / "results" / "trade_models" / f"{model_id}_schedule.json"
  if not src.exists():
    return 0
  inst = FINAL / "split_app" / "live" / "installed_models"
  if not inst.exists():
    return 0
  n = 0
  for d in inst.iterdir():
    if not d.is_dir():
      continue
    man = d / "manifest.json"
    mid = None
    if man.exists():
      try:
        mid = json.loads(man.read_text(encoding="utf-8")).get("model_id")
      except Exception:
        mid = None
    if str(mid) != str(model_id) and model_id not in d.name:
      continue
    dest = d / "schedule.json"
    dest.write_bytes(src.read_bytes())
    # also refresh Live materialized copy if present
    live_tm = FINAL / "split_app" / "live" / "results" / "trade_models" / f"{model_id}_schedule.json"
    live_tm.parent.mkdir(parents=True, exist_ok=True)
    live_tm.write_bytes(src.read_bytes())
    print(f"  synced → {dest}", flush=True)
    n += 1
  return n


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desk", action="append", default=None)
  ap.add_argument("--model-id", action="append", default=None)
  ap.add_argument("--from-live-roster", action="store_true",
                  help="Only models currently installed/enabled in Live roster")
  ap.add_argument("--limit", type=int, default=0)
  ap.add_argument("--sync-packages-only", action="store_true",
                  help="Only copy existing lab schedules into Live packages")
  args = ap.parse_args()

  desks = args.desk or DESKS
  only_ids: set[str] | None = set(args.model_id) if args.model_id else None
  if args.from_live_roster:
    roster_path = FINAL / "split_app" / "live" / "results" / "live_roster.json"
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    only_ids = {str(r.get("model_id")) for r in (roster.get("models") or []) if r.get("model_id")}
    # also include installed packages
    inst = FINAL / "split_app" / "live" / "installed_models"
    if inst.exists():
      for d in inst.iterdir():
        man = d / "manifest.json"
        if man.exists():
          mid = json.loads(man.read_text(encoding="utf-8")).get("model_id")
          if mid:
            only_ids.add(str(mid))

  done = failed = synced = 0
  for name in desks:
    desk = FINAL / name
    if not desk.exists():
      continue
    if args.sync_packages_only:
      ids = only_ids or {
        str(m.get("id"))
        for m in json.loads((desk / "results" / "trade_models.json").read_text(encoding="utf-8")).get("models") or []
        if m.get("id") and not m.get("archived")
      }
      print(f"\n=== {name}: sync schedules → packages ===", flush=True)
      for mid in sorted(ids):
        synced += sync_schedule_into_packages(desk, mid)
      continue
    need = models_needing_schedule(desk, only_ids=only_ids)
    print(f"\n=== {name}: {len(need)} missing schedules ===", flush=True)
    for mid in need:
      if args.limit and done >= args.limit:
        break
      rc = export_schedule(desk, mid)
      if rc == 0:
        done += 1
        synced += sync_schedule_into_packages(desk, mid)
      else:
        failed += 1
  # Always sync any already-present lab schedules for roster ids
  if not args.sync_packages_only and only_ids:
    for name in desks:
      desk = FINAL / name
      if not desk.exists():
        continue
      for mid in sorted(only_ids):
        synced += sync_schedule_into_packages(desk, mid)

  print(f"\nDone ok={done} failed={failed} package_syncs={synced}", flush=True)
  return 0 if failed == 0 else 1


if __name__ == "__main__":
  raise SystemExit(main())
