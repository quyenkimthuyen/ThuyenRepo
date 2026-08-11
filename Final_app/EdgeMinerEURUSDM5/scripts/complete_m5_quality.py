#!/usr/bin/env python3
"""Run KB→Grid→Promote and check M5 quality targets; iterate once if short.

Targets (OOS 2026 H1–Aug):
  EUR: R>=130, PF>=1.70, WR>=40, R/DD>=10  (or beat prior BestTotalR on R/DD with R>=150)
  GBP: R>=150, PF>=1.60, WR>=40, R/DD>=8

Usage:
  EdgeMinerM15B5/.venv/bin/python scripts/complete_m5_quality.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "results" / "research" / "m5_quality_complete"
PY = sys.executable

# Desk-specific floors (post-retune mong đợi — not full M15 parity yet).
TARGETS = {
  "EUR": {"total_r": 130.0, "profit_factor": 1.70, "win_rate_pct": 40.0, "r_dd": 10.0},
  "GBP": {"total_r": 150.0, "profit_factor": 1.60, "win_rate_pct": 40.0, "r_dd": 8.0},
}


def _desk_side() -> str:
  name = ROOT.name.upper()
  return "GBP" if "GBP" in name else "EUR"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  OUT.mkdir(parents=True, exist_ok=True)
  with open(OUT / "complete.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def run_pipeline() -> None:
  log("=== KB + Grid pipeline ===")
  subprocess.run(
    [PY, str(ROOT / "scripts" / "run_kb_then_grid.py")],
    cwd=str(ROOT),
    check=True,
  )


def promote() -> list[dict]:
  log("=== Promote top trade models ===")
  sys.path.insert(0, str(ROOT / "scripts"))
  from bootstrap_m5_pipeline import promote_top
  return promote_top(3)


def _metrics(row: dict) -> dict:
  r = float(row.get("total_r") or 0)
  dd = float(row.get("max_drawdown_r") or 0) or 1.0
  return {
    "label": row.get("label") or row.get("name"),
    "total_r": r,
    "n_trades": row.get("n_trades"),
    "profit_factor": float(row.get("profit_factor") or 0),
    "win_rate_pct": float(row.get("win_rate_pct") or 0),
    "max_drawdown_r": float(row.get("max_drawdown_r") or 0),
    "trades_per_week": row.get("trades_per_week"),
    "r_dd": r / max(dd, 0.5),
    "kb_profile": row.get("kb_profile"),
    "train_weeks": row.get("train_weeks"),
    "mining_preset": row.get("mining_preset"),
  }


def best_from_latest_grid() -> dict | None:
  from gui.grid_search_engine import load_latest_grid_run, _score
  run = load_latest_grid_run()
  if not run:
    return None
  rows = [r for r in (run.get("rows") or []) if not r.get("error")]
  if not rows:
    return None
  rows = sorted(rows, key=lambda r: _score(r, "quality"), reverse=True)
  return _metrics(rows[0])


def meets_target(m: dict, side: str) -> tuple[bool, list[str]]:
  t = TARGETS[side]
  misses = []
  if m["total_r"] < t["total_r"]:
    misses.append(f"R {m['total_r']:.1f} < {t['total_r']}")
  if m["profit_factor"] < t["profit_factor"]:
    misses.append(f"PF {m['profit_factor']:.2f} < {t['profit_factor']}")
  if m["win_rate_pct"] < t["win_rate_pct"]:
    misses.append(f"WR {m['win_rate_pct']:.1f} < {t['win_rate_pct']}")
  if m["r_dd"] < t["r_dd"]:
    misses.append(f"R/DD {m['r_dd']:.2f} < {t['r_dd']}")
  return (not misses), misses


def tighten_elite_preset() -> None:
  """Second-pass: nudge elite_or_quality toward higher RR / stricter void."""
  path = ROOT / "mining_presets.py"
  text = path.read_text(encoding="utf-8")
  # Only bump if still on first-pass values.
  if '"target_trades_per_week": 14.0' in text and "SECOND_PASS_QUALITY" not in text:
    text = text.replace(
      'ELITE_OR_QUALITY = {\n  **ELITE_60_3,\n  "rr_ratios": [3.2, 3.5, 4.0],',
      'ELITE_OR_QUALITY = {  # SECOND_PASS_QUALITY\n  **ELITE_60_3,\n  "rr_ratios": [3.5, 4.0],',
      1,
    )
    text = text.replace(
      '"anti_chase_fixed_vwap": 1.5,\n  "anti_chase_logic": "or",\n  "target_trades_per_week": 14.0,\n}',
      '"anti_chase_fixed_vwap": 1.2,\n  "anti_chase_logic": "or",\n  "target_trades_per_week": 12.0,\n}',
      1,
    )
    path.write_text(text, encoding="utf-8")
    log("Applied second-pass elite_or_quality tighten (RR/VWAP/TPW)")


def rerun_grid_only() -> None:
  log("=== Re-grid only (KB kept) ===")
  # Inline the grid portion of run_kb_then_grid
  from gui.app_settings import get_settings
  from gui.grid_search_engine import (
    build_grid_from_settings,
    grid_readiness,
    run_grid,
    save_grid_run,
  )
  r = grid_readiness()
  if not r["kb_complete"]:
    raise RuntimeError(f"KB incomplete: {r}")
  specs, config = build_grid_from_settings()
  objective = get_settings().get("grid_objective", "quality")
  log(f"Grid {len(specs)} combos · {objective}")

  def on_prog(done, total, label):
    log(f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=6)
  rid = save_grid_run(rows, config={**config, "timeframe": "M5", "pass": "second"}, objective=objective)
  ok = [x for x in rows if not x.get("error")]
  log(f"Grid done {rid}: {len(ok)}/{len(rows)} OK")


def main() -> int:
  side = _desk_side()
  OUT.mkdir(parents=True, exist_ok=True)
  log(f"Desk {ROOT.name} side={side} targets={TARGETS[side]}")

  run_pipeline()
  created = promote()
  best = best_from_latest_grid()
  if not best:
    log("No grid results")
    return 1

  ok, misses = meets_target(best, side)
  log(f"Best after pass1: {best}")
  if ok:
    log("TARGETS MET on pass1")
  else:
    log(f"TARGETS MISS: {misses} → second pass")
    tighten_elite_preset()
    rerun_grid_only()
    created = promote()
    best = best_from_latest_grid() or best
    ok, misses = meets_target(best, side)
    log(f"Best after pass2: {best}")
    log("TARGETS MET" if ok else f"TARGETS STILL SHORT: {misses}")

  payload = {
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "desk": ROOT.name,
    "side": side,
    "targets": TARGETS[side],
    "best": best,
    "meets_target": ok,
    "misses": misses,
    "promoted": [
      {"id": m.get("id"), "label": m.get("label"), "total_r": m.get("total_r"),
       "profit_factor": m.get("profit_factor"), "win_rate_pct": m.get("win_rate_pct"),
       "max_drawdown_r": m.get("max_drawdown_r")}
      for m in created
    ],
  }
  (OUT / "latest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
  log(f"Wrote {OUT / 'latest.json'}")
  return 0 if ok else 2


if __name__ == "__main__":
  raise SystemExit(main())
