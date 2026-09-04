#!/usr/bin/env python3
"""Chạy recipe đã chuẩn hóa: học KB theo Settings → Grid OOS 2026-h1 → tạo TM.

Không đổi weeks / preset / OOS (khác pipeline_kb_grid cũ).
Không đưa model lên Bridge.
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

# 6 tháng OOS: n mỏng hơn 12 tháng — không đòi n>=40 như quality score.
FILTER = {"wr_gt": 50.0, "total_r_gt": 15.0, "n_ge": 15, "max_dd_lt": 14.0}
MAX_MODELS = 3


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
  with open(log_dir / "std_recipe.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _row_nums(row: dict) -> tuple[float, float, float, int]:
  return (
    float(row.get("win_rate_pct") or 0),
    float(row.get("total_r") or 0),
    float(row.get("max_drawdown_r") or 999),
    int(row.get("n_trades") or 0),
  )


def _passes(row: dict) -> bool:
  if row.get("error"):
    return False
  wr, tot, dd, n = _row_nums(row)
  return wr > FILTER["wr_gt"] and tot > FILTER["total_r_gt"] and n >= FILTER["n_ge"] and dd < FILTER["max_dd_lt"]


def _fmt(row: dict) -> str:
  wr, tot, dd, n = _row_nums(row)
  rr = float(row.get("avg_rr") or 0)
  return (
    f"WR={wr:.1f} RR={rr:.2f} R={tot:+.1f} DD={dd:.1f} n={n} · {row.get('label')}"
  )


def _ensure_kb(desk: str, *, reset: bool) -> dict:
  from gui.app_settings import get_settings, resolve_learning_eras
  from gui.era_compare import ensure_profile_learned

  s = get_settings()
  eras = resolve_learning_eras(s)
  loops = int(s.get("learning_loops") or 3)
  learned, skipped = [], []
  for era in eras:
    label = era.get("label") or era["kb_profile"]
    _log(desk, f"KB {'RESET' if reset else 'ensure'} · {label} · {loops} epoch · {era['learn_from']}→{era['learn_until']}")
    spec = {
      "kb_profile": era["kb_profile"],
      "kb_name": era.get("label") or era["kb_profile"],
      "learn_from": era["learn_from"],
      "learn_until": era["learn_until"],
    }
    t0 = time.time()
    out = ensure_profile_learned(spec, epochs=loops, reset=reset)
    if out.get("skipped"):
      skipped.append(era["kb_profile"])
      _log(desk, f"KB skip · {era['kb_profile']} epochs={out.get('epochs')}")
    else:
      learned.append(era["kb_profile"])
      _log(desk, f"KB done · {era['kb_profile']} in {time.time() - t0:.0f}s")
  return {"learned": learned, "skipped": skipped, "loops": loops}


def _run_grid(desk: str, *, workers: int) -> dict:
  from gui.app_settings import get_settings
  from gui.grid_search_engine import (
    build_grid_from_settings, grid_readiness, run_grid, save_grid_run, _score,
  )
  from config import DEFAULT_TF

  s = get_settings()
  ready = grid_readiness(s)
  _log(
    desk,
    f"KB readiness complete={ready.get('kb_complete')} "
    f"ready={ready.get('ready_combos')}/{ready.get('expected_combos')}",
  )
  if not ready.get("kb_complete"):
    raise RuntimeError(f"{desk}: KB chưa đủ — {ready}")

  specs, config = build_grid_from_settings(s)
  objective = str(s.get("grid_objective") or "quality")
  _log(desk, f"Grid start {len(specs)} combo · obj={objective} · workers={workers}")
  t0 = time.time()

  def on_prog(done, total, label):
    _log(desk, f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=workers)
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": DEFAULT_TF,
      "filter_target": FILTER,
      "source": "std_recipe",
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  _log(desk, f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time() - t0:.0f}s")
  ranked = sorted(ok, key=lambda r: (_row_nums(r)[0], _row_nums(r)[1]), reverse=True)
  for r in ranked[:8]:
    _log(desk, f"top {_fmt(r)}")
  return {"run_id": rid, "rows": rows, "objective": objective}


def _create_models(desk: str, run: dict) -> list[dict]:
  from gui.trade_model import create_trade_model

  rows = [r for r in (run.get("rows") or []) if not r.get("error")]
  hits = [r for r in rows if _passes(r)]
  hits.sort(key=lambda r: (_row_nums(r)[0], _row_nums(r)[1]), reverse=True)
  _log(desk, f"Filter WR>{FILTER['wr_gt']} R>{FILTER['total_r_gt']} n>={FILTER['n_ge']}: {len(hits)}")
  created = []
  for i, row in enumerate(hits[:MAX_MODELS]):
    wr, tot, dd, n = _row_nums(row)
    label = f"WR{wr:.0f}R{tot:.0f}"
    model = create_trade_model(
      row,
      run_id=run.get("run_id"),
      label=label,
      set_active=(i == 0),
      build_report=False,
    )
    created.append(model)
    _log(
      desk,
      f"TM {model.get('id')} · {model.get('label')} · {_fmt(row)} · active={i == 0}",
    )
  if not created:
    _log(desk, "Không TM nào đạt WR>50 trên OOS 6 tháng — không tạo model")
  return created


def run_desk(desk: str, *, reset_kb: bool, workers: int) -> dict:
  cfg = _bind(desk)
  from gui.app_settings import default_settings_for_desk, save_settings, _sanitize_settings, get_settings

  pinned = _sanitize_settings(default_settings_for_desk())
  save_settings(pinned)
  s = get_settings()
  _log(
    desk,
    f"start pair={cfg.get('pair')} tf={cfg.get('tf')} "
    f"weeks={s.get('strategy_train_weeks')} eras={s.get('learning_era_keys')} "
    f"loops={s.get('learning_loops')} presets={s.get('mining_presets')} "
    f"oos={s.get('oos_window_keys')} {s.get('backtest_from')}→{s.get('backtest_to')} "
    f"spread={s.get('spread_pips')}/{s.get('slippage_pips')}",
  )
  kb = _ensure_kb(desk, reset=reset_kb)
  run = _run_grid(desk, workers=workers)
  created = _create_models(desk, run)
  out = {
    "desk": desk,
    "kb": kb,
    "run_id": run.get("run_id"),
    "n_combos": len(run.get("rows") or []),
    "created": [
      {
        "id": m.get("id"),
        "label": m.get("label"),
        "active": i == 0,
      }
      for i, m in enumerate(created)
    ],
  }
  _log(desk, f"RECIPE DONE {json.dumps(out, ensure_ascii=False)}")
  return out


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desks", default="e21,g23")
  ap.add_argument("--reset-kb", action="store_true", default=True)
  ap.add_argument("--no-reset-kb", action="store_true")
  ap.add_argument("--workers", type=int, default=2)
  args = ap.parse_args()
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  reset = bool(args.reset_kb) and not args.no_reset_kb
  summary = []
  rc = 0
  for desk in desks:
    try:
      summary.append(run_desk(desk, reset_kb=reset, workers=max(1, args.workers)))
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
