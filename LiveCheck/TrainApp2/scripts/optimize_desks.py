#!/usr/bin/env python3
"""Optimize TrainApp desks: Grid Search then promote Trade Models by filters."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env  # noqa: E402

FILTER = {"wr_gt": 50.0, "rr_gt": 2.5, "total_r_gt": 100.0, "max_dd_lt": 10.0}


def _purge_modules() -> None:
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)


def _bind_desk(desk: str) -> dict:
  cfg = apply_desk_env(desk)
  _purge_modules()
  for p in (str(ROOT), cfg["core_root"]):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def _log(desk: str, msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [{desk}] {msg}"
  print(line, flush=True)
  log_dir = Path(os.environ["TRAINAPP_RUNTIME"]) / "results"
  log_dir.mkdir(parents=True, exist_ok=True)
  with open(log_dir / "optimize_desks.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _widen_settings() -> None:
  from gui.app_settings import get_settings, save_settings, TRAIN_WEEK_OPTIONS
  s = get_settings()
  want = [3, 4, 5, 6, 7, 8, 9, 12]
  allowed = set(TRAIN_WEEK_OPTIONS) if TRAIN_WEEK_OPTIONS else set(want)
  s["strategy_train_weeks"] = [w for w in want if w in allowed] or want
  if str(s.get("grid_objective") or "") in ("", "total_r"):
    s["grid_objective"] = "risk_adjusted"
  save_settings(s)
  _log(os.environ.get("TRAINAPP_DESK", "?"), f"settings weeks={s['strategy_train_weeks']} objective={s['grid_objective']}")


def _run_grid(desk: str, *, workers: int) -> dict:
  from gui.app_settings import get_settings
  from gui.grid_search_engine import build_grid_from_settings, grid_readiness, run_grid, save_grid_run
  from config import DEFAULT_TF
  r = grid_readiness()
  _log(desk, f"KB readiness {r}")
  if not r.get("kb_complete"):
    raise RuntimeError(f"{desk}: KB chua du — can hoc KB truoc ({r})")
  specs, config = build_grid_from_settings()
  objective = get_settings().get("grid_objective", "risk_adjusted")
  _log(desk, f"Grid start: {len(specs)} combo · objective={objective} · workers={workers}")
  t0 = time.time()
  def on_prog(done, total, label):
    if done == 1 or done == total or done % 5 == 0:
      _log(desk, f"Grid {done}/{total}: {label}")
  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=workers)
  rid = save_grid_run(rows, config={**config, "timeframe": DEFAULT_TF, "filter_target": FILTER}, objective=objective)
  ok = [x for x in rows if not x.get("error")]
  _log(desk, f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time()-t0:.0f}s")
  return {"run_id": rid, "rows": rows}


def _passes(row: dict) -> bool:
  if row.get("error"):
    return False
  try:
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    dd = float(row.get("max_drawdown_r") or 999)
  except Exception:
    return False
  return wr > FILTER["wr_gt"] and rr > FILTER["rr_gt"] and tot > FILTER["total_r_gt"] and dd < FILTER["max_dd_lt"]


def _promote(desk: str, run: dict | None = None, *, max_models: int = 5) -> list[dict]:
  from gui.grid_search_engine import load_latest_grid_run
  from gui.trade_model import create_trade_model
  payload = run or load_latest_grid_run() or {}
  rows = [r for r in (payload.get("rows") or []) if _passes(r)]
  rows.sort(key=lambda r: float(r.get("total_r") or 0), reverse=True)
  _log(desk, f"Filter matches: {len(rows)}")
  created = []
  for i, row in enumerate(rows[:max_models]):
    label = f"Filt WR{float(row.get('win_rate_pct') or 0):.0f} RR{float(row.get('avg_rr') or 0):.2f} +{float(row.get('total_r') or 0):.0f}R"
    model = create_trade_model(row, run_id=payload.get("run_id"), label=label, set_active=(i == 0))
    created.append(model)
    _log(desk, f"Promoted {model.get('id')} · {label} · dd={row.get('max_drawdown_r')}")
  if not created:
    cand = [r for r in (payload.get("rows") or []) if not r.get("error") and float(r.get("max_drawdown_r") or 999) < FILTER["max_dd_lt"]]
    cand.sort(key=lambda r: float(r.get("total_r") or 0), reverse=True)
    for r in cand[:5]:
      _log(desk, f"near WR={float(r.get('win_rate_pct') or 0):.1f} RR={float(r.get('avg_rr') or 0):.2f} R={float(r.get('total_r') or 0):.1f} DD={float(r.get('max_drawdown_r') or 0):.1f}")
  return created


def run_desk(desk: str, *, promote_only: bool, widen: bool, workers: int) -> dict:
  cfg = _bind_desk(desk)
  _log(desk, f"start pair={cfg.get('pair')} tf={cfg.get('tf')}")
  if widen and not promote_only:
    _widen_settings()
  run_payload = None
  if not promote_only:
    run_payload = _run_grid(desk, workers=workers)
  created = _promote(desk, run_payload)
  return {"desk": desk, "promoted": len(created), "models": [m.get("id") for m in created]}


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desks", default="e21,g23,e31,g33")
  ap.add_argument("--promote-only", action="store_true")
  ap.add_argument("--widen-weeks", action="store_true", default=True)
  ap.add_argument("--no-widen-weeks", action="store_true")
  ap.add_argument("--workers", type=int, default=0)
  args = ap.parse_args()
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  widen = bool(args.widen_weeks) and not args.no_widen_weeks
  summary = []
  for desk in desks:
    workers = args.workers if args.workers > 0 else (6 if desk in ("e31", "g33") else 1)
    try:
      summary.append(run_desk(desk, promote_only=args.promote_only, widen=widen, workers=workers))
    except Exception as exc:
      try:
        _bind_desk(desk)
        _log(desk, f"FAILED: {exc}")
      except Exception:
        print(f"FAILED {desk}: {exc}", flush=True)
      summary.append({"desk": desk, "error": str(exc)})
  print(json.dumps(summary, indent=2, ensure_ascii=False))
  return 0 if all("error" not in s for s in summary) else 1


if __name__ == "__main__":
  raise SystemExit(main())
