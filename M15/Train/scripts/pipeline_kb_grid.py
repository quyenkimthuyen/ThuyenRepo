#!/usr/bin/env python3
"""Pipeline tối ưu 4 desk: học KB (nếu thiếu) → Grid Search tinh chỉnh → Trade Model.

Tinh chỉnh hợp lý (không nổ grid):
  - weeks: [3, 4, 5, 6, 9]  (làm mịn quanh 3/6/9 đã chứng minh)
  - presets: elite_or_quality, edge_gentle, elite_55_4, anti_chase_fixed_70
  - objective: quality
  - epoch: đủ 1..learning_loops (giữ vòng tốt như ep2)
  - KB: không reset nếu đã đủ epoch

Promote: ưu tiên filter chất lượng; fallback theo score quality nếu không có hit.
"""
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

# Fine-tune settings applied before grid.
FINE_WEEKS = [3, 4, 5, 6, 9]
FINE_PRESETS = [
  "elite_or_quality",
  "edge_gentle",
  "elite_55_4",
  "anti_chase_fixed_70",
]
FINE_OBJECTIVE = "quality"

# Primary quality book filter (slightly softer than sniper for live books).
FILTER = {"wr_gt": 45.0, "rr_gt": 2.2, "total_r_gt": 25.0, "max_dd_lt": 12.0}


def _purge() -> None:
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)


def _bind(desk: str) -> dict:
  cfg = apply_desk_env(desk)
  _purge()
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def _log(desk: str, msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [{desk}] {msg}"
  try:
    print(line, flush=True)
  except UnicodeEncodeError:
    print(line.encode("ascii", "replace").decode("ascii"), flush=True)
  log_dir = Path(os.environ["TRAINAPP_RUNTIME"]) / "results"
  log_dir.mkdir(parents=True, exist_ok=True)
  with open(log_dir / "pipeline_kb_grid.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _clear_stale_jobs(desk: str) -> None:
  """Mark interrupted/stale long tasks so GUI doesn't think something is running."""
  jobs = Path(os.environ["TRAINAPP_RUNTIME"]) / "results" / "jobs" / "long_task_state.json"
  if not jobs.exists():
    return
  try:
    state = json.loads(jobs.read_text(encoding="utf-8"))
  except Exception:
    return
  if state.get("status") in ("running", "interrupted"):
    state["status"] = "cancelled"
    state["error"] = "Cleared by pipeline_kb_grid before re-run"
    state["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    state["updated_at"] = state["finished_at"]
    jobs.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _log(desk, f"cleared stale job {state.get('job_id')} ({state.get('status')})")


def _apply_fine_settings() -> dict:
  from gui.app_settings import get_settings, save_settings, TRAIN_WEEK_OPTIONS

  s = get_settings()
  allowed = set(TRAIN_WEEK_OPTIONS) if TRAIN_WEEK_OPTIONS else set(FINE_WEEKS)
  s["strategy_train_weeks"] = [w for w in FINE_WEEKS if w in allowed] or list(FINE_WEEKS)
  s["mining_presets"] = list(FINE_PRESETS)
  s["grid_objective"] = FINE_OBJECTIVE
  if not s.get("learning_era_keys"):
    s["learning_era_keys"] = ["2025-full", "2025-h2"]
  s["learning_loops"] = int(s.get("learning_loops") or 4)
  save_settings(s)
  _log(
    os.environ.get("TRAINAPP_DESK", "?"),
    f"fine settings weeks={s['strategy_train_weeks']} presets={s['mining_presets']} "
    f"obj={s['grid_objective']} loops={s['learning_loops']} eras={s['learning_era_keys']}",
  )
  return s


def _ensure_kb(desk: str, *, reset: bool) -> dict:
  from gui.app_settings import get_settings, resolve_learning_eras
  from gui.era_compare import ensure_profile_learned

  s = get_settings()
  eras = resolve_learning_eras(s)
  loops = int(s.get("learning_loops") or 4)
  learned, skipped = [], []
  for era in eras:
    label = era.get("label") or era["kb_profile"]
    _log(desk, f"KB ensure · {label} · target {loops} epochs · reset={reset}")
    spec = {
      "kb_profile": era["kb_profile"],
      "kb_name": era.get("label") or era["kb_profile"],
      "learn_from": era["learn_from"],
      "learn_until": era["learn_until"],
    }
    out = ensure_profile_learned(spec, epochs=loops, reset=reset)
    if out.get("skipped"):
      skipped.append(era["kb_profile"])
      _log(desk, f"KB skip (đã đủ) · {era['kb_profile']} epochs={out.get('epochs')}")
    else:
      learned.append(era["kb_profile"])
      _log(desk, f"KB learned · {era['kb_profile']}")
  return {"learned": learned, "skipped": skipped}


def _passes(row: dict) -> bool:
  if row.get("error"):
    return False
  try:
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    dd = float(row.get("max_drawdown_r") or 999)
    n = int(row.get("n_trades") or 0)
  except Exception:
    return False
  return (
    wr > FILTER["wr_gt"]
    and rr > FILTER["rr_gt"]
    and tot > FILTER["total_r_gt"]
    and dd < FILTER["max_dd_lt"]
    and n >= 20
  )


def _run_grid(desk: str, *, workers: int) -> dict:
  from gui.app_settings import get_settings
  from gui.grid_search_engine import (
    build_grid_from_settings, grid_readiness, run_grid, save_grid_run, _score,
  )
  from config import DEFAULT_TF

  s = get_settings()
  ready = grid_readiness(s)
  _log(desk, f"KB readiness kb_complete={ready.get('kb_complete')} "
       f"expected={ready.get('expected_combos')} ready={ready.get('ready_combos')}")
  if not ready.get("kb_complete"):
    raise RuntimeError(f"{desk}: KB chưa đủ — {ready}")

  specs, config = build_grid_from_settings(s)
  objective = str(s.get("grid_objective") or FINE_OBJECTIVE)
  _log(desk, f"Grid start: {len(specs)} combo · objective={objective} · workers={workers}")
  t0 = time.time()

  def on_prog(done, total, label):
    if done == 1 or done == total or done % 5 == 0:
      _log(desk, f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=workers)
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": DEFAULT_TF,
      "filter_target": FILTER,
      "source": "pipeline_kb_grid",
      "fine_tune": {
        "weeks": FINE_WEEKS,
        "presets": FINE_PRESETS,
        "objective": FINE_OBJECTIVE,
      },
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  _log(desk, f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time() - t0:.0f}s")

  ranked = sorted(ok, key=lambda r: _score(r, objective), reverse=True)
  for r in ranked[:8]:
    _log(
      desk,
      f"top WR={float(r.get('win_rate_pct') or 0):.1f} RR={float(r.get('avg_rr') or 0):.2f} "
      f"R={float(r.get('total_r') or 0):.1f} DD={float(r.get('max_drawdown_r') or 0):.1f} "
      f"n={r.get('n_trades')} · {r.get('label')}",
    )
  return {"run_id": rid, "rows": rows, "objective": objective}


def _promote(desk: str, run: dict, *, max_models: int = 5) -> list[dict]:
  from gui.grid_search_engine import _score
  from gui.trade_model import create_trade_model

  rows = [r for r in (run.get("rows") or []) if not r.get("error")]
  objective = str(run.get("objective") or FINE_OBJECTIVE)
  hits = [r for r in rows if _passes(r)]
  hits.sort(key=lambda r: _score(r, objective), reverse=True)
  _log(desk, f"Filter hits WR>{FILTER['wr_gt']}/RR>{FILTER['rr_gt']}/"
       f"R>{FILTER['total_r_gt']}/DD<{FILTER['max_dd_lt']}: {len(hits)}")

  if not hits:
    _log(desk, "No strict hits — fallback: DD<14, R>15, n>=20, sort by quality")
    hits = [
      r for r in rows
      if float(r.get("max_drawdown_r") or 999) < 14.0
      and float(r.get("total_r") or 0) > 15.0
      and int(r.get("n_trades") or 0) >= 20
    ]
    hits.sort(key=lambda r: _score(r, objective), reverse=True)

  created = []
  for i, row in enumerate(hits[:max_models]):
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    label = f"Fine WR{wr:.0f} RR{rr:.2f} +{tot:.0f}R"
    model = create_trade_model(
      row,
      run_id=run.get("run_id"),
      label=label,
      set_active=(i == 0),
    )
    created.append(model)
    _log(desk, f"Promoted {model.get('id')} · {label} · dd={row.get('max_drawdown_r')} "
         f"n={row.get('n_trades')} active={i == 0}")
  if not created:
    _log(desk, "Không promote được model nào — kiểm tra OOS data / grid rows")
  return created


def run_desk(desk: str, *, reset_kb: bool, workers: int, skip_grid: bool) -> dict:
  cfg = _bind(desk)
  _log(desk, f"start pair={cfg.get('pair')} tf={cfg.get('tf')}")
  _clear_stale_jobs(desk)
  _apply_fine_settings()
  kb = _ensure_kb(desk, reset=reset_kb)
  if skip_grid:
    from gui.grid_search_engine import load_latest_grid_run
    run = load_latest_grid_run() or {}
    created = _promote(desk, run)
    return {
      "desk": desk, "kb": kb, "run_id": run.get("run_id"),
      "promoted": len(created), "models": [m.get("id") for m in created],
    }
  run = _run_grid(desk, workers=workers)
  created = _promote(desk, run)
  return {
    "desk": desk,
    "kb": kb,
    "run_id": run.get("run_id"),
    "n_combos": len(run.get("rows") or []),
    "promoted": len(created),
    "models": [m.get("id") for m in created],
  }


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desks", default="e21,g23")
  ap.add_argument("--reset-kb", action="store_true")
  ap.add_argument("--workers", type=int, default=0,
                  help="0 = auto (2)")
  ap.add_argument("--promote-only", action="store_true")
  args = ap.parse_args()
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  summary = []
  rc = 0
  for desk in desks:
    auto_w = 2
    workers = args.workers if args.workers > 0 else auto_w
    try:
      summary.append(run_desk(
        desk,
        reset_kb=bool(args.reset_kb),
        workers=max(1, workers),
        skip_grid=bool(args.promote_only),
      ))
    except Exception as exc:
      rc = 1
      try:
        _bind(desk)
        _log(desk, f"FAILED: {exc}")
      except Exception:
        print(f"FAILED {desk}: {exc}", flush=True)
      summary.append({"desk": desk, "error": str(exc)})
  print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
  return rc


if __name__ == "__main__":
  raise SystemExit(main())
