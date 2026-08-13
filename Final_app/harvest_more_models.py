#!/usr/bin/env python3
"""Harvest more Trade Models from existing Final_app grid runs (no retrain).

Runs each desk in a fresh subprocess to avoid cross-desk import pollution.
"""
from __future__ import annotations

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
OOS_FROM, OOS_TO = "2026-01-01", "2026-08-07"

WORKER = r'''
from __future__ import annotations
import json, sys
from pathlib import Path

desk = Path(sys.argv[1]).resolve()
max_new = int(sys.argv[2])
oos_from, oos_to = sys.argv[3], sys.argv[4]
sys.path.insert(0, str(desk))

def _f(r, k, default=0.0):
  try:
    return float(r.get(k) if r.get(k) is not None else default)
  except Exception:
    return default

def quality(r):
  total_r=_f(r,"total_r"); pf=_f(r,"profit_factor"); wr=_f(r,"win_rate_pct")
  dd=max(_f(r,"max_drawdown_r",1.0),0.5)
  if total_r<=0 or pf<1.2: return -1e12
  return (total_r/dd)*2.0 + pf*25.0 + wr*0.8 + total_r*0.04

def rdd(r):
  return _f(r,"total_r")/max(_f(r,"max_drawdown_r",1.0),0.5)

def fp(r):
  return (
    round(_f(r,"total_r"),2), round(_f(r,"profit_factor"),3), int(_f(r,"n_trades")),
    int(_f(r,"train_weeks")), str(r.get("kb_profile") or ""),
    str(r.get("preset") or r.get("mining_preset") or ""),
  )

from gui.grid_search_engine import load_latest_grid_run
from gui.trade_model import (
  create_trade_model, load_models_store, save_models_store, set_active_trade_model,
)

run = load_latest_grid_run() or {}
rows = [r for r in (run.get("rows") or []) if not r.get("error") and _f(r,"total_r")>0]
store = load_models_store()
models = list(store.get("models") or [])
have = {fp(m) for m in models}
# also by grid_key
have_keys = {m.get("grid_key") for m in models if m.get("grid_key")}
existing_labels = {str(m.get("label") or "") for m in models}

def unused(pool):
  out=[]
  for r in pool:
    gk=r.get("key") or r.get("grid_key")
    if gk and gk in have_keys: continue
    if fp(r) in have: continue
    out.append(r)
  return out

ok=rows
by_q=unused(sorted(ok, key=quality, reverse=True))
by_pf=unused(sorted(ok, key=lambda r: _f(r,"profit_factor"), reverse=True))
by_rdd=unused(sorted(ok, key=rdd, reverse=True))
by_r=unused(sorted(ok, key=lambda r: _f(r,"total_r"), reverse=True))
by_wr=unused(sorted(ok, key=lambda r: _f(r,"win_rate_pct"), reverse=True))
by_dd=unused(sorted(
  [r for r in ok if _f(r,"total_r")>=20 and _f(r,"profit_factor")>=1.35],
  key=lambda r: _f(r,"max_drawdown_r"),
))

slots=[
  ("EliteQuality", by_q, lambda r: quality(r)>0),
  ("ElitePF", by_pf, lambda r: _f(r,"profit_factor")>=1.5 and _f(r,"total_r")>=15),
  ("EliteRDD", by_rdd, lambda r: rdd(r)>=5 and _f(r,"profit_factor")>=1.3),
  ("LowDD", by_dd, lambda r: _f(r,"max_drawdown_r")>0),
  ("StretchR", by_r, lambda r: _f(r,"profit_factor")>=1.35 and _f(r,"total_r")>=40),
  ("EliteWR", by_wr, lambda r: _f(r,"win_rate_pct")>=40 and _f(r,"profit_factor")>=1.3),
]

picks=[]; used=set(have); used_keys=set(x for x in have_keys if x)
for label, pool, pred in slots:
  if len(picks)>=max_new: break
  for r in pool:
    if not pred(r): continue
    fpr=fp(r); gk=r.get("key") or r.get("grid_key")
    if fpr in used: continue
    if gk and gk in used_keys: continue
    lab=label; n=2
    while lab in existing_labels or lab in {p[0] for p in picks}:
      lab=f"{label}_{n}"; n+=1
    picks.append((lab,r)); used.add(fpr)
    if gk: used_keys.add(gk)
    break

created=0
for lab,row in picks:
  try:
    m=create_trade_model(
      row, run_id=run.get("id") or run.get("run_id"),
      label=lab, set_active=False, allow_duplicate_combo=False,
    )
    store=load_models_store()
    for x in store["models"]:
      if x.get("id")==m.get("id"):
        x["oos_from"]=oos_from; x["oos_to"]=oos_to; m=x; break
    save_models_store(store)
    created+=1
    print(f"  + {desk.name}/{lab}: R={m.get('total_r')} PF={m.get('profit_factor')} WR={m.get('win_rate_pct')} DD={m.get('max_drawdown_r')} tw={m.get('train_weeks')} kb={m.get('kb_profile')}", flush=True)
  except Exception as exc:
    print(f"  ! {desk.name}/{lab}: {exc}", flush=True)

store=load_models_store(); models=list(store.get("models") or [])
scored=[(quality(m), m) for m in models if not m.get("archived") and quality(m)>-1e11]
scored.sort(key=lambda x: x[0], reverse=True)
if scored:
  aid=scored[0][1].get("id"); set_active_trade_model(aid)
  print(f"  active → {scored[0][1].get('label')} ({aid})", flush=True)
print(f"  created={created} total_models={len(models)}", flush=True)
'''


def main() -> int:
  import argparse
  ap = argparse.ArgumentParser()
  ap.add_argument("--desk", action="append", default=None)
  ap.add_argument("--max-new", type=int, default=6)
  args = ap.parse_args()
  desks = args.desk or DESKS
  print("=== Harvest more models from existing grids ===", flush=True)
  worker = FINAL / "_harvest_worker.py"
  worker.write_text(WORKER, encoding="utf-8")
  try:
    for name in desks:
      desk = FINAL / name
      print(f"\n## {name}", flush=True)
      r = subprocess.run(
        [str(PY), str(worker), str(desk), str(args.max_new), OOS_FROM, OOS_TO],
        cwd=str(desk),
      )
      if r.returncode != 0:
        print(f"  worker exit {r.returncode}", flush=True)
  finally:
    try:
      worker.unlink()
    except OSError:
      pass
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
