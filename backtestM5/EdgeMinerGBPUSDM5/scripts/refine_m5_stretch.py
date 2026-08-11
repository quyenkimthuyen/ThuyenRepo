#!/usr/bin/env python3
"""Stretch refine: train new era if needed, latest-epoch grid with balanced preset.

Keeps existing KB for era_5 / era_h2 (no wipe). Adds era_2025_2026_6thang.
Grids latest snapshots only (faster) with quality + balanced presets.
Promotes if new best beats current BestQuality on stretch score.

Stretch targets (closer to M15 parity):
  EUR: R>=160, PF>=2.0, WR>=45, R/DD>=15
  GBP: R>=200, PF>=2.0, WR>=45, R/DD>=15
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "results" / "research" / "m5_stretch_refine"
PY = sys.executable

STRETCH = {
  "EUR": {"total_r": 160.0, "profit_factor": 2.0, "win_rate_pct": 45.0, "r_dd": 15.0},
  "GBP": {"total_r": 200.0, "profit_factor": 2.0, "win_rate_pct": 45.0, "r_dd": 15.0},
}

PRESETS = [
  "elite_or_quality",
  "elite_m5_balanced",
  "elite_55_4",
  "anti_chase_fixed_70",
]
ERAS = [
  ("5-thang-cuoi-2025", "era_5_thang_cuoi_2025", "5 thang cuoi 2025", "2025-08-01", "2025-12-31"),
  ("2025-h2", "era_2025_h2", "2025 (6 tháng cuối)", "2025-07-01", "2025-12-31"),
  ("2025-2026-6thang", "era_2025_2026_6thang", "2025-2026-6thang", "2025-10-01", "2026-03-31"),
]
LOOPS = 4


def side() -> str:
  return "GBP" if "GBP" in ROOT.name.upper() else "EUR"


def log(msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  OUT.mkdir(parents=True, exist_ok=True)
  with open(OUT / "refine.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def update_settings() -> None:
  from gui.app_settings import get_settings, save_settings
  s = get_settings()
  s["learning_era_keys"] = [e[0] for e in ERAS]
  s["learning_loops"] = LOOPS
  s["strategy_train_weeks"] = [3, 6]
  s["mining_presets"] = list(PRESETS)
  s["grid_objective"] = "quality"
  s["backtest_from"] = "2026-01-01"
  s["backtest_to"] = "2026-08-07"
  save_settings(s)
  log(f"settings eras={[e[0] for e in ERAS]} presets={PRESETS}")


def ensure_kb() -> None:
  from kb_profiles import get_profile
  for key, pid, label, fr, until in ERAS:
    p = get_profile(pid) or {}
    have = int(p.get("epochs") or 0)
    if have >= LOOPS and p.get("exists"):
      log(f"KB keep {pid} epochs={have}")
      continue
    log(f"KB train {pid} (have={have} need={LOOPS})")
    cmd = [
      PY, str(ROOT / "run_learning.py"),
      "--epochs", str(LOOPS),
      "--reset",
      "--kb-profile", pid,
      "--kb-name", label,
      "--from-date", fr,
      "--until-date", until,
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def run_latest_grid():
  from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
  from gui.app_settings import get_settings
  from gui.grid_search_engine import build_grid, run_grid, save_grid_run
  from gui.app_settings import resolve_learning_eras

  s = get_settings()
  eras = resolve_learning_eras(s)
  profiles = [e["kb_profile"] for e in eras]
  specs = build_grid(
    train_weeks=[3, 6],
    kb_profiles=profiles,
    include_kb_off=False,
    epoch_mode="latest",
    oos_from=s.get("backtest_from", "2026-01-01"),
    oos_to=s.get("backtest_to", "2026-08-07"),
    spread_pips=float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    slippage_pips=float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    max_runs=200,
    mining_presets=list(PRESETS),
  )
  log(f"Grid latest-only: {len(specs)} combos")

  def on_prog(done, total, label):
    log(f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective="quality", on_progress=on_prog, workers=6)
  rid = save_grid_run(
    rows,
    config={
      "source": "m5_stretch_refine",
      "timeframe": "M5",
      "epoch_mode": "latest",
      "mining_presets": PRESETS,
      "kb_profiles": profiles,
      "train_weeks": [3, 6],
      "oos_from": s.get("backtest_from"),
      "oos_to": s.get("backtest_to"),
    },
    objective="quality",
  )
  ok = [r for r in rows if not r.get("error")]
  log(f"Grid done {rid}: {len(ok)}/{len(rows)} OK")
  return rows, rid


def quality_score(r: dict) -> float:
  R = float(r.get("total_r") or 0)
  dd = float(r.get("max_drawdown_r") or 1) or 1
  pf = float(r.get("profit_factor") or 0)
  wr = float(r.get("win_rate_pct") or 0)
  n = int(r.get("n_trades") or 0)
  # Ignore tiny books — PF/WR on n<40 is not comparable.
  if R <= 0 or pf < 1.2 or n < 40:
    return -1e12
  return (R / max(dd, 0.5)) * 2.0 + pf * 25.0 + wr * 0.8 + R * 0.04


def metrics(r: dict) -> dict:
  R = float(r.get("total_r") or 0)
  dd = float(r.get("max_drawdown_r") or 1) or 1
  return {
    "label": r.get("label"),
    "total_r": R,
    "profit_factor": float(r.get("profit_factor") or 0),
    "win_rate_pct": float(r.get("win_rate_pct") or 0),
    "max_drawdown_r": float(r.get("max_drawdown_r") or 0),
    "n_trades": r.get("n_trades"),
    "trades_per_week": r.get("trades_per_week"),
    "r_dd": R / max(dd, 0.5),
    "kb_profile": r.get("kb_profile"),
    "train_weeks": r.get("train_weeks"),
    "mining_preset": r.get("mining_preset"),
    "q": quality_score(r),
  }


def meets(m: dict, sd: str) -> tuple[bool, list[str]]:
  t = STRETCH[sd]
  miss = []
  for k, floor in t.items():
    val = m["r_dd"] if k == "r_dd" else m[k]
    if val < floor:
      miss.append(f"{k} {val:.2f}<{floor}")
  return (not miss), miss


def current_best_quality_model() -> dict | None:
  from gui.trade_model import list_trade_models
  models = list_trade_models()
  best = None
  for m in models:
    row = {
      "total_r": m.get("total_r"),
      "max_drawdown_r": m.get("max_drawdown_r"),
      "profit_factor": m.get("profit_factor"),
      "win_rate_pct": m.get("win_rate_pct"),
      "label": m.get("label"),
      "n_trades": m.get("n_trades"),
      "kb_profile": m.get("kb_profile"),
      "train_weeks": m.get("train_weeks"),
      "mining_preset": (m.get("mining_search_space") or {}).get("selection_mode"),
    }
    sc = quality_score(row)
    if best is None or sc > best[0]:
      best = (sc, m, metrics(row))
  return None if not best else {"model": best[1], "metrics": best[2], "q": best[0]}


def promote_if_better(rows: list[dict], rid: str, prev_q: float) -> list[dict]:
  from gui.trade_model import create_trade_model, set_active_trade_model, load_active_model_id
  ok = [r for r in rows if not r.get("error")]
  ok = sorted(ok, key=quality_score, reverse=True)
  created = []
  if not ok:
    return created
  best = ok[0]
  bm = metrics(best)
  log(f"New grid best Q={bm['q']:.1f} {bm}")
  if bm["q"] > prev_q + 1.0:
    m = create_trade_model(
      best, run_id=rid, label="BestQuality", set_active=True, allow_duplicate_combo=True,
    )
    created.append(m)
    log(f"Promoted new BestQuality {m.get('id')} R={m.get('total_r')}")
  else:
    log(f"Keep previous BestQuality (prev_q={prev_q:.1f} >= new {bm['q']:.1f})")
  # Always add BestStretch if meets stretch and not duplicate of BestQuality
  sd = side()
  stretch_ok = [r for r in ok if meets(metrics(r), sd)[0]]
  if stretch_ok:
    top = stretch_ok[0]
    if top.get("key") != best.get("key") or not created:
      m2 = create_trade_model(
        top, run_id=rid, label="BestStretch", set_active=False, allow_duplicate_combo=True,
      )
      created.append(m2)
      log(f"Promoted BestStretch {m2.get('id')} R={m2.get('total_r')}")
  # Ensure active stays BestQuality id if we didn't replace
  if not created:
    pass
  return created


def main() -> int:
  sd = side()
  OUT.mkdir(parents=True, exist_ok=True)
  log(f"Desk {ROOT.name} stretch={STRETCH[sd]}")
  update_settings()
  prev = current_best_quality_model()
  prev_q = float(prev["q"]) if prev else -1e9
  log(f"Previous best Q={prev_q:.1f} {None if not prev else prev['metrics']}")
  ensure_kb()
  rows, rid = run_latest_grid()
  created = promote_if_better(rows, rid, prev_q)
  best_row = max((r for r in rows if not r.get("error")), key=quality_score, default=None)
  best_m = metrics(best_row) if best_row else None
  ok, miss = (False, ["no rows"]) if not best_m else meets(best_m, sd)
  # also check BestBalance-like: R>=160 & R/DD>=15 & PF>=1.9
  bal = None
  for r in sorted((x for x in rows if not x.get("error")), key=lambda x: float(x.get("total_r") or 0), reverse=True):
    m = metrics(r)
    if m["total_r"] >= 160 and m["r_dd"] >= 15 and m["profit_factor"] >= 1.9:
      bal = m
      break
  payload = {
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "desk": ROOT.name,
    "side": sd,
    "stretch_targets": STRETCH[sd],
    "previous": None if not prev else prev["metrics"],
    "best": best_m,
    "stretch_met": ok,
    "misses": miss,
    "balance_candidate": bal,
    "promoted": [
      {"id": m.get("id"), "label": m.get("label"), "total_r": m.get("total_r"),
       "profit_factor": m.get("profit_factor"), "win_rate_pct": m.get("win_rate_pct"),
       "max_drawdown_r": m.get("max_drawdown_r")}
      for m in created
    ],
  }
  (OUT / "latest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
  log(f"Wrote {OUT / 'latest.json'} stretch_met={ok} misses={miss}")
  return 0 if ok else 2


if __name__ == "__main__":
  raise SystemExit(main())
