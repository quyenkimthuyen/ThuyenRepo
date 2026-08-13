#!/usr/bin/env python3
"""Round-2 expand: train era_2025_2026_6thang + grid with extra presets (no wipe of old KB)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

FINAL = Path(__file__).resolve().parent
PY = Path("/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python")

DESKS = {
  "EdgeMinerEURUSDM15": {
    "presets": ["elite_or_quality", "anti_chase_fixed_70", "elite_55_4", "elite_60_3"],
  },
  "EdgeMinerGBPUSDM15": {
    "presets": ["elite_or_quality", "anti_chase_fixed_70", "elite_55_4", "elite_60_3"],
  },
  "EdgeMinerEURUSDM5": {
    "presets": ["elite_or_quality", "elite_m5_balanced", "anti_chase_fixed_70", "elite_55_4"],
  },
  "EdgeMinerGBPUSDM5": {
    "presets": ["elite_or_quality", "elite_m5_balanced", "anti_chase_fixed_70", "elite_55_4"],
  },
}

NEW_ERA = {
  "key": "2025-2026-6thang",
  "label": "2025-2026-6thang",
  "learn_from": "2025-10-01",
  "learn_until": "2026-03-31",
  "kb_profile": "era_2025_2026_6thang",
}


def log(desk: Path, msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  p = desk / "results" / "pipeline_round2.log"
  p.parent.mkdir(parents=True, exist_ok=True)
  with open(p, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def update_settings(desk: Path, presets: list[str], *, grid_era_keys: list[str] | None = None) -> dict:
  path = desk / "results" / "app_settings.json"
  s = json.loads(path.read_text(encoding="utf-8"))
  eras = list(s.get("learning_eras") or [])
  if not any(e.get("key") == NEW_ERA["key"] for e in eras):
    eras.append(dict(NEW_ERA))
  s["learning_eras"] = eras
  # Keep all known eras listed; grid uses grid_era_keys (default: new era only for round2 speed)
  all_keys = []
  for e in eras:
    k = e.get("key")
    if k and k not in all_keys:
      all_keys.append(k)
  s["learning_era_keys"] = list(grid_era_keys or [NEW_ERA["key"]])
  s["_all_learning_era_keys"] = all_keys
  s["mining_presets"] = list(presets)
  s["grid_objective"] = "quality"
  s["backtest_from"] = "2026-01-01"
  s["backtest_to"] = "2026-08-07"
  s["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
  path.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return s


def kb_ready(desk: Path, profile: str, loops: int = 4) -> bool:
  idx = desk / "learning" / "kb_profiles" / "index.json"
  if not idx.exists():
    return False
  data = json.loads(idx.read_text(encoding="utf-8"))
  # formats vary — also check file + learning_report
  prof = desk / "learning" / "kb_profiles" / f"{profile}.json"
  if not prof.exists():
    return False
  try:
    blob = json.loads(prof.read_text(encoding="utf-8"))
    epochs = blob.get("epochs") or blob.get("n_epochs") or 0
    if isinstance(blob.get("epoch_history"), list):
      epochs = max(epochs, len(blob["epoch_history"]))
    return int(epochs) >= loops
  except Exception:
    return False


def train_new_era(desk: Path, loops: int = 4) -> None:
  profile = NEW_ERA["kb_profile"]
  if kb_ready(desk, profile, loops):
    log(desk, f"KB {profile} already ready — skip learn")
    return
  log(desk, f"=== Học KB mới: {profile} ({loops} vòng) ===")
  cmd = [
    str(PY), str(desk / "run_learning.py"),
    "--epochs", str(loops),
    "--reset",
    "--kb-profile", profile,
    "--kb-name", NEW_ERA["label"],
    "--from-date", NEW_ERA["learn_from"],
    "--until-date", NEW_ERA["learn_until"],
  ]
  subprocess.run(cmd, cwd=str(desk), check=True)


def run_grid_only(desk: Path) -> None:
  log(desk, "=== Grid Search (round2 settings) ===")
  code = r"""
import inspect
import sys
from pathlib import Path
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT))
from gui.app_settings import get_settings
from gui.grid_search_engine import build_grid_from_settings, grid_readiness, run_grid, save_grid_run

r = grid_readiness()
print(f"Grid readiness: {r['ready_combos']}/{r['expected_combos']} kb_complete={r['kb_complete']}", flush=True)
if not r['kb_complete']:
  raise SystemExit(f"KB incomplete: {r}")
specs, config = build_grid_from_settings()
objective = get_settings().get('grid_objective', 'quality')
print(f"Grid specs={len(specs)} objective={objective}", flush=True)

def on_prog(done, total, label):
  print(f"Grid {done}/{total}: {label}", flush=True)

kwargs = dict(objective=objective, on_progress=on_prog)
if 'workers' in inspect.signature(run_grid).parameters:
  kwargs['workers'] = 6
rows = run_grid(specs, **kwargs)
tf = 'M5' if 'M5' in ROOT.name else 'M15'
rid = save_grid_run(rows, config={**config, 'timeframe': tf, 'round': 'round2'}, objective=objective)
ok = [x for x in rows if not x.get('error')]
print(f"Grid xong: {rid} · {len(ok)}/{len(rows)} combo OK", flush=True)
if ok:
  print(f"Best: {ok[0].get('label')} · {ok[0].get('total_r')}R", flush=True)
"""
  subprocess.run([str(PY), "-c", code], cwd=str(desk), check=True)


def restore_all_era_keys(desk: Path) -> None:
  path = desk / "results" / "app_settings.json"
  s = json.loads(path.read_text(encoding="utf-8"))
  keys = list(s.get("_all_learning_era_keys") or [])
  if not keys:
    keys = [e.get("key") for e in (s.get("learning_eras") or []) if e.get("key")]
  if NEW_ERA["key"] not in keys:
    keys.append(NEW_ERA["key"])
  s["learning_era_keys"] = keys
  path.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  log(desk, f"restored learning_era_keys={keys}")


def harvest_desk(name: str) -> None:
  log(FINAL / name, f"=== Harvest after round2 {name} ===")
  subprocess.run(
    [str(PY), str(FINAL / "harvest_more_models.py"), "--desk", name, "--max-new", "6"],
    cwd=str(FINAL),
    check=False,
  )


def main() -> int:
  import argparse
  ap = argparse.ArgumentParser()
  ap.add_argument("--desk", action="append", default=None)
  ap.add_argument("--skip-kb", action="store_true")
  ap.add_argument("--skip-grid", action="store_true")
  args = ap.parse_args()
  names = args.desk or list(DESKS)
  for name in names:
    desk = FINAL / name
    cfg = DESKS[name]
    log(desk, f"==== Round2 start {name} ====")
    update_settings(desk, cfg["presets"], grid_era_keys=[NEW_ERA["key"]])
    log(desk, f"presets={cfg['presets']} · grid eras=[{NEW_ERA['kb_profile']}]")
    if not args.skip_kb:
      train_new_era(desk, loops=4)
    if not args.skip_grid:
      run_grid_only(desk)
    harvest_desk(name)
    restore_all_era_keys(desk)
    log(desk, f"==== Round2 HOÀN TẤT {name} ====")
  # final pareto
  subprocess.run([str(PY), str(FINAL / "build_final_pareto.py")], cwd=str(FINAL), check=False)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
