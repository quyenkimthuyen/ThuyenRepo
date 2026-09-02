#!/usr/bin/env python3
"""Grid g23 theo app_settings hiện tại. KB giữ nguyên. Không promote Active."""
from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/thuyenng/work/ThuyenRepo/M15/Train")
sys.path.insert(0, str(ROOT))
from desk_context import apply_desk_env

LOG = ROOT / "runtime" / "g23" / "results" / "pipeline_kb_grid.log"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [g23] {msg}"
  print(line, flush=True)
  LOG.parent.mkdir(parents=True, exist_ok=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def bind():
  cfg = apply_desk_env("g23")
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def main() -> int:
  cfg = bind()
  log(f"ss-grid start pair={cfg.get('pair')} tf={cfg.get('tf')}")
  from gui.app_settings import get_settings, settings_grid_signature
  from gui.grid_search_engine import (
    build_grid_from_settings, grid_readiness, run_grid, save_grid_run, _score,
  )
  from config import DEFAULT_TF

  s = get_settings()
  log(
    f"settings weeks={s.get('strategy_train_weeks')} eras={s.get('learning_era_keys')} "
    f"loops={s.get('learning_loops')} presets={s.get('mining_presets')} "
    f"spread={s.get('spread_pips')}/{s.get('slippage_pips')} obj={s.get('grid_objective')} "
    f"oos={s.get('backtest_from')}→{s.get('backtest_to')}"
  )
  ready = grid_readiness(s)
  log(
    f"KB readiness complete={ready.get('kb_complete')} "
    f"ready={ready.get('ready_combos')}/{ready.get('expected_combos')}"
  )
  if not ready.get("kb_complete"):
    log(f"FAILED KB chưa đủ: {ready}")
    print("PIPELINE FAILED", flush=True)
    return 1

  specs, config = build_grid_from_settings(s)
  objective = str(s.get("grid_objective") or "quality")
  log(f"Grid start {len(specs)} combo · no KB reset · obj={objective}")
  t0 = time.time()

  def on_prog(done, total, label):
    log(f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=2)
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": DEFAULT_TF,
      "source": "gbp_ss_lab_grid_cli",
      "settings_signature": settings_grid_signature(s),
      "promote": False,
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  log(f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time()-t0:.0f}s")
  ranked = sorted(ok, key=lambda r: _score(r, objective), reverse=True)
  for r in ranked[:16]:
    log(
      f"top WR={float(r.get('win_rate_pct') or 0):.1f} RR={float(r.get('avg_rr') or 0):.2f} "
      f"R={float(r.get('total_r') or 0):.1f} DD={float(r.get('max_drawdown_r') or 0):.1f} "
      f"n={r.get('n_trades')} PF={r.get('profit_factor')} · {r.get('label')}"
    )
  quality = [
    r for r in ranked
    if float(r.get("total_r") or 0) > 0
    and float(r.get("profit_factor") or 0) >= 1.2
    and int(r.get("n_trades") or 0) >= 40
  ]
  log(f"quality-gate hits={len(quality)} / {len(ok)}")
  log("SS GRID DONE (no promote, no Active)")
  print("PIPELINE DONE", flush=True)
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except Exception as exc:
    log(f"FAILED: {exc}")
    print("PIPELINE FAILED", flush=True)
    raise
