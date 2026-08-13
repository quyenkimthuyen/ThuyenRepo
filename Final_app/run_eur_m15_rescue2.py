#!/usr/bin/env python3
"""EUR M15 rescue round 2 — unlock deepened KB epochs + hybrid presets.

Round1 deepened KB to ep8 but grid only tested vòng 1–4.
This round grids ep5–12 (after +4 deepen) on era_2025_h2 with hybrid presets.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

FINAL = Path(__file__).resolve().parent
DESK = FINAL / "EdgeMinerEURUSDM15"
PY = Path("/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python")
LOG = FINAL / "eur_m15_rescue2.log"

KB_PROFILE = "era_2025_h2"
ERA = {
  "key": "2025-h2",
  "label": "2025 (6 tháng cuối)",
  "learn_from": "2025-07-01",
  "learn_until": "2025-12-31",
  "kb_profile": KB_PROFILE,
}
TRAIN_WEEKS = [6, 9]
PRESETS = [
  "eur_m15_balance",
  "eur_m15_balance_v2",
  "eur_m15_wr",
  "eur_m15_stretch_wr",
  "eur_m15_london",
  "eur_m15_hi_r",
  "frontier_rr_hi",
  "anti_chase_fixed_65",
]
KB_EXTRA = 4
# After deepen, history should be 12; grid the unused + new epochs.
EPOCHS = [5, 6, 7, 8, 9, 10, 11, 12]


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def snapshot_count() -> int:
  root = DESK / "learning" / "kb_profiles" / "snapshots" / KB_PROFILE
  if not root.exists():
    return 0
  return len(list(root.glob("ep*.json")))


def deepen_kb() -> None:
  have = snapshot_count()
  log(f"KB {KB_PROFILE} snapshots before deepen: {have}")
  log(f"=== Deepen KB {KB_PROFILE} (+{KB_EXTRA} epochs, no reset) ===")
  cmd = [
    str(PY), str(DESK / "run_learning.py"),
    "--epochs", str(KB_EXTRA),
    "--kb-profile", KB_PROFILE,
    "--kb-name", ERA["label"],
    "--from-date", ERA["learn_from"],
    "--until-date", ERA["learn_until"],
  ]
  subprocess.run(cmd, cwd=str(DESK), check=True)
  log(f"KB snapshots after deepen: {snapshot_count()}")


def run_grid() -> None:
  have = snapshot_count()
  epochs = [e for e in EPOCHS if e <= have]
  if not epochs:
    raise SystemExit(f"No epochs to grid (have={have}, want={EPOCHS})")
  n = len(TRAIN_WEEKS) * len(epochs) * len(PRESETS)
  log(
    f"=== Grid rescue2: era={KB_PROFILE} tw={TRAIN_WEEKS} "
    f"epochs={epochs} presets={len(PRESETS)} → {n} combos ==="
  )
  code = r"""
import inspect, json, sys
from pathlib import Path
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT))
from gui.grid_search_engine import build_grid, run_grid, save_grid_run

payload = json.loads(Path('_rescue2_grid_args.json').read_text())
specs = build_grid(
  train_weeks=payload['train_weeks'],
  kb_profiles=payload['kb_profiles'],
  include_kb_off=False,
  epoch_mode='selected',
  selected_epochs=payload['selected_epochs'],
  oos_from=payload['oos_from'],
  oos_to=payload['oos_to'],
  spread_pips=payload['spread_pips'],
  slippage_pips=payload['slippage_pips'],
  max_runs=300,
  mining_presets=payload['presets'],
)
print(f"Grid specs={len(specs)}", flush=True)

def on_prog(done, total, label):
  print(f"Grid {done}/{total}: {label}", flush=True)

kwargs = dict(objective='quality', on_progress=on_prog)
if 'workers' in inspect.signature(run_grid).parameters:
  kwargs['workers'] = 6
rows = run_grid(specs, **kwargs)
rid = save_grid_run(
  rows,
  config={
    'timeframe': 'M15',
    'round': 'eur_m15_rescue2',
    'train_weeks': payload['train_weeks'],
    'kb_profiles': payload['kb_profiles'],
    'selected_epochs': payload['selected_epochs'],
    'mining_presets': payload['presets'],
    'oos_from': payload['oos_from'],
    'oos_to': payload['oos_to'],
  },
  objective='quality',
)
ok = [x for x in rows if not x.get('error')]
pos = [x for x in ok if float(x.get('total_r') or 0) > 0]
print(f"Grid xong: {rid} · {len(ok)}/{len(rows)} OK · {len(pos)} positive-R", flush=True)
if pos:
  by_r = max(pos, key=lambda x: float(x.get('total_r') or 0))
  by_wr = max(pos, key=lambda x: float(x.get('win_rate_pct') or 0))
  good = [x for x in pos if float(x.get('win_rate_pct') or 0) >= 40 and float(x.get('total_r') or 0) >= 50]
  print(f"BestR: {by_r.get('label')} · {by_r.get('total_r')}R WR={by_r.get('win_rate_pct')}", flush=True)
  print(f"BestWR: {by_wr.get('label')} · {by_wr.get('total_r')}R WR={by_wr.get('win_rate_pct')}", flush=True)
  print(f"WR>=40 & R>=50: {len(good)}", flush=True)
  for x in sorted(good, key=lambda r: -float(r.get('total_r') or 0))[:5]:
    print(f"  hit R={x.get('total_r')} WR={x.get('win_rate_pct')} PF={x.get('profit_factor')} | {x.get('label')}", flush=True)
"""
  args = {
    "train_weeks": TRAIN_WEEKS,
    "kb_profiles": [KB_PROFILE],
    "selected_epochs": {KB_PROFILE: epochs},
    "presets": PRESETS,
    "oos_from": "2026-01-01",
    "oos_to": "2026-08-07",
    "spread_pips": 1.0,
    "slippage_pips": 0.3,
  }
  (DESK / "_rescue2_grid_args.json").write_text(json.dumps(args), encoding="utf-8")
  # also mirror settings for UI consistency
  sp = DESK / "results" / "app_settings.json"
  s = json.loads(sp.read_text(encoding="utf-8"))
  s["_all_learning_era_keys"] = list(s.get("_all_learning_era_keys") or s.get("learning_era_keys") or [])
  s["learning_era_keys"] = ["2025-h2"]
  s["strategy_train_weeks"] = list(TRAIN_WEEKS)
  s["mining_presets"] = list(PRESETS)
  s["learning_loops"] = max(epochs)
  s["grid_objective"] = "quality"
  s["backtest_from"] = "2026-01-01"
  s["backtest_to"] = "2026-08-07"
  s["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
  sp.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  subprocess.run([str(PY), "-c", code], cwd=str(DESK), check=True)


def harvest_and_pick() -> None:
  log("=== Harvest + WR×R active pick ===")
  subprocess.run(
    [str(PY), str(FINAL / "harvest_more_models.py"), "--desk", DESK.name, "--max-new", "8"],
    cwd=str(FINAL),
    check=False,
  )
  code = r"""
import sys
from pathlib import Path
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT))
from gui.trade_model import load_models_store, set_active_trade_model

def f(m,k,d=0.0):
  try: return float(m.get(k) if m.get(k) is not None else d)
  except: return d

def composite(m):
  R, PF, WR, DD = f(m,'total_r'), f(m,'profit_factor'), f(m,'win_rate_pct'), max(f(m,'max_drawdown_r',1),0.5)
  if R<=0 or PF<1.15: return -1e12
  return R*0.55 + WR*2.2 + PF*18.0 + (R/DD)*3.0 - DD*0.8

store = load_models_store()
models = [m for m in store.get('models') or [] if not m.get('archived')]
scored = sorted(((composite(m), m) for m in models), key=lambda x: x[0], reverse=True)
print('Top composite:', flush=True)
for sc, m in scored[:10]:
  print(f"  {m.get('label')}: {sc:.1f} · R={m.get('total_r')} WR={m.get('win_rate_pct')} PF={m.get('profit_factor')} DD={m.get('max_drawdown_r')}", flush=True)
prefer = [m for sc,m in scored if sc>-1e11 and f(m,'win_rate_pct')>=41 and f(m,'total_r')>=55]
pick = prefer[0] if prefer else (scored[0][1] if scored and scored[0][0]>-1e11 else None)
if pick:
  set_active_trade_model(pick['id'])
  print(f"ACTIVE → {pick.get('label')} R={pick.get('total_r')} WR={pick.get('win_rate_pct')} PF={pick.get('profit_factor')}", flush=True)
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
  args = ap.parse_args()
  log("==== EUR M15 rescue2 START ====")
  if not args.skip_kb:
    deepen_kb()
  if not args.skip_grid:
    run_grid()
  harvest_and_pick()
  restore_era_keys()
  subprocess.run([str(PY), str(FINAL / "build_final_pareto.py")], cwd=str(FINAL), check=False)
  log("==== EUR M15 rescue2 DONE ====")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
