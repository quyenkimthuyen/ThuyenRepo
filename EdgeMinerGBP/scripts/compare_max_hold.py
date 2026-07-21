#!/usr/bin/env python3
"""So sánh max_hold_bars: 24 / 36 / 48 / 72 nến H1 (+ auto từ miner)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from config import MAX_HOLD_GRID
from data_loader import load_gbpusd_h1
from gui.trade_model import get_model_run_params, load_active_model_id
from run_backtest import run_walk_forward


def _summary(result: dict) -> dict:
  o = result["overall_oos"]
  y = result["last_1_year"]
  cfg = result.get("config") or {}
  hold = cfg.get("max_hold_bars")
  return {
    "hold_bars": hold if hold is not None else "auto",
    "n_trades": o["n_trades"],
    "trades_per_week": o["trades_per_week"],
    "win_rate_pct": o["win_rate_pct"],
    "avg_rr": o["avg_rr"],
    "profit_factor": o["profit_factor"],
    "total_r": o["total_r"],
    "max_dd_r": o["max_drawdown_r"],
    "year_total_r": y["total_r"],
  }


def main():
  import argparse
  p = argparse.ArgumentParser()
  p.add_argument("--oos-from", default="2025-01-01")
  p.add_argument("--oos-to", default="2026-12-31")
  p.add_argument("--out", type=Path, default=ROOT / "results" / "max_hold_compare.json")
  args = p.parse_args()

  params = get_model_run_params()
  df = load_gbpusd_h1("2022-01-01")
  print(f"So sánh max_hold | model={load_active_model_id()} | OOS {args.oos_from} → {args.oos_to}")
  print(f"Miner grid: {MAX_HOLD_GRID} · test override: 24, 36, 48, 72 + auto\n")

  common = dict(
    df=df,
    use_learning=params["use_kb"],
    train_months=params["train_months"],
    spread_pips=params["spread_pips"],
    slippage_pips=params["slippage_pips"],
    kb_profile=params["kb_profile"] if params["use_kb"] else None,
    kb_snapshot=params.get("kb_snapshot"),
    oos_from=args.oos_from,
    oos_to=args.oos_to,
    reopt_period="week",
    verbose=True,
  )

  scenarios: list[tuple[str, dict]] = [
    ("h24", {"max_hold_bars": 24}),
    ("h36", {"max_hold_bars": 36}),
    ("h48", {"max_hold_bars": 48}),
    ("h72", {"max_hold_bars": 72}),
    ("auto", {"max_hold_bars": None}),
  ]
  results = {}
  for key, kw in scenarios:
    label = f"{kw['max_hold_bars']} bars" if kw["max_hold_bars"] else "auto (miner chọn)"
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    results[key] = run_walk_forward(**common, **kw)

  rows = [_summary(results[k]) for k, _ in scenarios]
  base = rows[1]  # h36 baseline

  print(f"\n{'='*60}")
  print("SO SÁNH MAX HOLD (nến H1)")
  print(f"{'='*60}")
  print(f"{'Hold':<8} {'Lệnh':>6} {'WR%':>7} {'AvgRR':>7} {'PF':>7} {'TotalR':>9} {'DD':>7}")
  print("-" * 60)
  for r in rows:
    h = str(r["hold_bars"])
    print(
      f"{h:<8} {r['n_trades']:6.0f} {r['win_rate_pct']:7.1f} "
      f"{r['avg_rr']:7.3f} {r['profit_factor']:7.3f} {r['total_r']:+9.2f} {r['max_dd_r']:7.2f}"
    )

  best = max(rows, key=lambda r: r["total_r"])
  print(f"\nKết luận: hold **{best['hold_bars']}** bars tốt nhất — Total R {best['total_r']:+.2f}")
  auto = rows[-1]
  if auto["hold_bars"] == "auto":
    print(f"  · Auto (miner {MAX_HOLD_GRID}): {auto['total_r']:+.2f}R vs cố định 36: {base['total_r']:+.2f}R")

  out = {
    "model_id": load_active_model_id(),
    "miner_grid": MAX_HOLD_GRID,
    "summary": {scenarios[i][0]: rows[i] for i in range(len(scenarios))},
    "winner": best["hold_bars"],
  }
  args.out.parent.mkdir(parents=True, exist_ok=True)
  with open(args.out, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
  print(f"\nĐã lưu: {args.out}")


if __name__ == "__main__":
  main()
