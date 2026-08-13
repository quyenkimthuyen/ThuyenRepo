#!/usr/bin/env python3
"""EUR M15 rescue: hunt better WR + TotalR.

Diagnosis (current roster):
  - elite_* → PF ok nhưng WR≤42% và TotalR thấp (ít lệnh)
  - anti_chase_fixed_70 → TotalR~61 nhưng WR~36%
  - era 2025-2026-6thang → toàn âm trên OOS 2026

Plan:
  1) Deepen KB on good eras only (h2 + 5-thang), no reset
  2) Grid: those eras × train 6/9w × R/WR presets (skip toxic 6thang)
  3) Harvest + pick active by WR×R composite (not PF-only)
"""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

FINAL = Path(__file__).resolve().parent
DESK = FINAL / "EdgeMinerEURUSDM15"
PY = Path("/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python")
LOG = FINAL / "eur_m15_rescue.log"

# Skip toxic overlapping era that produced negative OOS for EUR M15.
ERA_KEYS = ["2025-h2", "5-thang-cuoi-2025"]
TRAIN_WEEKS = [6, 9]
PRESETS = [
  "eur_m15_balance",
  "eur_m15_wr",
  "edge_gentle",
  "anti_chase_fixed_65",
  "anti_chase_fixed_68",
  "anti_chase",
  "anti_chase_and_70_15",
  "frontier_rr_hi",
]
KB_EXTRA_EPOCHS = 4  # deepen existing 4 → ~8


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def update_settings() -> None:
  path = DESK / "results" / "app_settings.json"
  s = json.loads(path.read_text(encoding="utf-8"))
  all_keys = []
  for e in s.get("learning_eras") or []:
    k = e.get("key")
    if k and k not in all_keys:
      all_keys.append(k)
  s["_all_learning_era_keys"] = all_keys
  s["learning_era_keys"] = list(ERA_KEYS)
  s["strategy_train_weeks"] = list(TRAIN_WEEKS)
  s["mining_presets"] = list(PRESETS)
  s["grid_objective"] = "quality"
  s["backtest_from"] = "2026-01-01"
  s["backtest_to"] = "2026-08-07"
  s["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
  path.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  log(
    f"settings: eras={ERA_KEYS} tw={TRAIN_WEEKS} presets={PRESETS} "
    f"(~{len(ERA_KEYS)*len(TRAIN_WEEKS)*len(PRESETS)*4} combos)"
  )


def deepen_kb() -> None:
  catalog = {
    e["key"]: e
    for e in json.loads((DESK / "results" / "app_settings.json").read_text(encoding="utf-8")).get(
      "learning_eras"
    )
    or []
  }
  for key in ERA_KEYS:
    era = catalog.get(key)
    if not era:
      raise SystemExit(f"missing era {key}")
    profile = era["kb_profile"]
    log(f"=== Deepen KB {profile} (+{KB_EXTRA_EPOCHS} epochs, no reset) ===")
    cmd = [
      str(PY),
      str(DESK / "run_learning.py"),
      "--epochs",
      str(KB_EXTRA_EPOCHS),
      "--kb-profile",
      profile,
      "--kb-name",
      era.get("label") or profile,
      "--from-date",
      era["learn_from"],
      "--until-date",
      era["learn_until"],
    ]
    subprocess.run(cmd, cwd=str(DESK), check=True)


def run_grid() -> None:
  log("=== Grid Search EUR M15 rescue ===")
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
rid = save_grid_run(rows, config={**config, 'timeframe': 'M15', 'round': 'eur_m15_rescue'}, objective=objective)
ok = [x for x in rows if not x.get('error')]
pos = [x for x in ok if float(x.get('total_r') or 0) > 0]
print(f"Grid xong: {rid} · {len(ok)}/{len(rows)} OK · {len(pos)} positive-R", flush=True)
if pos:
  by_r = max(pos, key=lambda x: float(x.get('total_r') or 0))
  by_wr = max(pos, key=lambda x: float(x.get('win_rate_pct') or 0))
  print(f"BestR: {by_r.get('label')} · {by_r.get('total_r')}R WR={by_r.get('win_rate_pct')}", flush=True)
  print(f"BestWR: {by_wr.get('label')} · {by_wr.get('total_r')}R WR={by_wr.get('win_rate_pct')}", flush=True)
"""
  subprocess.run([str(PY), "-c", code], cwd=str(DESK), check=True)


def harvest_and_pick_active() -> None:
  log("=== Harvest + active by WR×R composite ===")
  subprocess.run(
    [str(PY), str(FINAL / "harvest_more_models.py"), "--desk", DESK.name, "--max-new", "8"],
    cwd=str(FINAL),
    check=False,
  )
  # Re-pick active: prefer models with WR≥40 and solid R; else best composite.
  code = r"""
import sys
from pathlib import Path
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT))
from gui.trade_model import load_models_store, save_models_store, set_active_trade_model

def f(m,k,d=0.0):
  try: return float(m.get(k) if m.get(k) is not None else d)
  except: return d

def composite(m):
  R, PF, WR, DD = f(m,'total_r'), f(m,'profit_factor'), f(m,'win_rate_pct'), max(f(m,'max_drawdown_r',1),0.5)
  if R<=0 or PF<1.15: return -1e12
  # Weight WR and TotalR harder than default harvest quality (EUR pain points).
  return R*0.55 + WR*2.2 + PF*18.0 + (R/DD)*3.0 - DD*0.8

store = load_models_store()
models = [m for m in store.get('models') or [] if not m.get('archived')]
scored = sorted(((composite(m), m) for m in models), key=lambda x: x[0], reverse=True)
print('Top by WR×R composite:', flush=True)
for sc, m in scored[:8]:
  print(f"  {m.get('label')}: score={sc:.1f} R={m.get('total_r')} PF={m.get('profit_factor')} WR={m.get('win_rate_pct')} DD={m.get('max_drawdown_r')}", flush=True)
# Prefer WR>=40 among positive score; else best composite
prefer = [m for sc,m in scored if sc>-1e11 and f(m,'win_rate_pct')>=40 and f(m,'total_r')>=40]
pick = prefer[0] if prefer else (scored[0][1] if scored and scored[0][0]>-1e11 else None)
if pick:
  set_active_trade_model(pick['id'])
  print(f"ACTIVE → {pick.get('label')} ({pick.get('id')}) R={pick.get('total_r')} WR={pick.get('win_rate_pct')} PF={pick.get('profit_factor')}", flush=True)
"""
  subprocess.run([str(PY), "-c", code], cwd=str(DESK), check=True)


def restore_era_keys() -> None:
  path = DESK / "results" / "app_settings.json"
  s = json.loads(path.read_text(encoding="utf-8"))
  keys = list(s.get("_all_learning_era_keys") or [])
  if not keys:
    keys = [e.get("key") for e in (s.get("learning_eras") or []) if e.get("key")]
  s["learning_era_keys"] = keys
  path.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  log(f"restored learning_era_keys={keys}")


def main() -> int:
  import argparse

  ap = argparse.ArgumentParser()
  ap.add_argument("--skip-kb", action="store_true")
  ap.add_argument("--skip-grid", action="store_true")
  ap.add_argument("--harvest-only", action="store_true")
  args = ap.parse_args()

  log("==== EUR M15 rescue START ====")
  if args.harvest_only:
    harvest_and_pick_active()
    restore_era_keys()
    subprocess.run([str(PY), str(FINAL / "build_final_pareto.py")], cwd=str(FINAL), check=False)
    log("==== EUR M15 rescue DONE (harvest-only) ====")
    return 0

  update_settings()
  if not args.skip_kb:
    deepen_kb()
  if not args.skip_grid:
    run_grid()
  harvest_and_pick_active()
  restore_era_keys()
  subprocess.run([str(PY), str(FINAL / "build_final_pareto.py")], cwd=str(FINAL), check=False)
  log("==== EUR M15 rescue DONE ====")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
