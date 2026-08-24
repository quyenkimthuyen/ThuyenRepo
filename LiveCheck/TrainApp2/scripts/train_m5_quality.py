#!/usr/bin/env python3
"""Train M5 quality books (E31/G33) with M15-parity elite presets.

Uses latest KB snapshot only (not every epoch) so the grid stays small:
  2 weeks × 2 presets × 3 eras ≈ 12 walk-forwards per desk.
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

FILTER = {"wr_gt": 52.0, "rr_gt": 2.45, "total_r_gt": 40.0, "max_dd_lt": 8.0}


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
  with open(log_dir / "train_m5_quality.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


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
  return (
    wr > FILTER["wr_gt"]
    and rr > FILTER["rr_gt"]
    and tot > FILTER["total_r_gt"]
    and dd < FILTER["max_dd_lt"]
  )


def _run_desk(desk: str, *, workers: int) -> dict:
  cfg = _bind(desk)
  _log(desk, f"start pair={cfg.get('pair')} tf={cfg.get('tf')} target_tpw={cfg.get('target_trades_per_week')} max/day={cfg.get('max_trades_per_day')}")

  from gui.app_settings import get_settings, resolve_learning_eras
  from gui.grid_search_engine import build_grid, grid_readiness, run_grid, save_grid_run, _score
  from gui.trade_model import create_trade_model
  from config import DEFAULT_TF

  s = get_settings()
  ready = grid_readiness(s)
  _log(desk, f"KB readiness kb_complete={ready.get('kb_complete')} missing={ready.get('missing_profiles')} under={ready.get('under_trained')}")
  if not ready.get("kb_complete"):
    raise RuntimeError(f"{desk}: KB chua du — {ready}")

  eras = resolve_learning_eras(s)
  presets = list(s.get("mining_presets") or ["elite_or_quality"])
  weeks = list(s.get("strategy_train_weeks") or [3, 6])
  specs = build_grid(
    train_weeks=weeks,
    kb_profiles=[e["kb_profile"] for e in eras],
    include_kb_off=False,
    epoch_mode="latest",
    oos_from=str(s.get("backtest_from") or "2026-01-01"),
    oos_to=str(s.get("backtest_to") or "2026-08-07"),
    spread_pips=float(s.get("spread_pips") or cfg.get("spread_pips") or 1.0),
    slippage_pips=float(s.get("slippage_pips") or 0.3),
    max_runs=200,
    mining_presets=presets,
  )
  objective = str(s.get("grid_objective") or "quality")
  _log(
    desk,
    f"Grid start: {len(specs)} combo · weeks={weeks} · presets={presets} "
    f"· eras={[e.get('kb_profile') for e in eras]} · objective={objective} · workers={workers}",
  )
  t0 = time.time()

  def on_prog(done, total, label):
    _log(desk, f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=workers)
  rid = save_grid_run(
    rows,
    config={
      "timeframe": DEFAULT_TF,
      "filter_target": FILTER,
      "epoch_mode": "latest",
      "source": "train_m5_quality",
      "mining_presets": presets,
      "train_weeks": weeks,
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
      f"tpw={float(r.get('trades_per_week') or 0):.2f} n={r.get('n_trades')} · {r.get('label')}",
    )

  def _n(row: dict) -> int:
    try:
      return int(row.get("n_trades") or 0)
    except Exception:
      return 0

  def _tpw(row: dict) -> float:
    try:
      return float(row.get("trades_per_week") or 0)
    except Exception:
      return 0.0

  hits = [r for r in ranked if _passes(r) and _n(r) >= 20]
  if not hits:
    _log(desk, "No row passed WR52/RR2.45/R40/DD8 n>=20 — promoting best WR with DD<10 n>=20 R>15")
    fallback = [
      r for r in ranked
      if float(r.get("max_drawdown_r") or 999) < 10.0
      and float(r.get("win_rate_pct") or 0) >= 40.0
      and float(r.get("total_r") or 0) > 15.0
      and _n(r) >= 20
    ]
    fallback.sort(key=lambda r: float(r.get("win_rate_pct") or 0), reverse=True)
    hits = fallback[:3]
  # Prefer a live-usable book (tpw>=1.2) as Active; keep sniper rows in the store.
  bookish = [r for r in hits if _tpw(r) >= 1.2 and _n(r) >= 40]
  active_row = max(bookish, key=lambda r: float(r.get("win_rate_pct") or 0)) if bookish else (hits[0] if hits else None)
  created = []
  for i, row in enumerate(hits[:5]):
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    label = f"M5Q WR{wr:.0f} RR{rr:.2f} +{tot:.0f}R"
    model = create_trade_model(
      row,
      run_id=rid,
      label=label,
      set_active=(active_row is not None and row is active_row),
    )
    created.append(model)
    _log(desk, f"Promoted {model.get('id')} · {label} · dd={row.get('max_drawdown_r')} n={_n(row)}")
  if active_row is not None and created:
    _log(
      desk,
      f"Active book WR={float(active_row.get('win_rate_pct') or 0):.1f} "
      f"tpw={_tpw(active_row):.2f} n={_n(active_row)}",
    )
  return {"desk": desk, "run_id": rid, "promoted": len(created), "models": [m.get("id") for m in created]}


def main() -> int:
  raise SystemExit(
    "M5 desks e31/g33 are retired. This app only runs M15 desks e21 and g23."
  )
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desks", default="e31,g33")
  ap.add_argument("--workers", type=int, default=6)
  args = ap.parse_args()
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  summary = []
  rc = 0
  for desk in desks:
    try:
      summary.append(_run_desk(desk, workers=max(1, int(args.workers))))
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
