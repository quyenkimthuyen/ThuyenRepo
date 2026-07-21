#!/usr/bin/env python3
"""A/B: min_bars_between (2/4/6) và trail hybrid (3 cặp)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from config import HYBRID_TRAIL_COMPARE_GRID, MIN_BARS_BETWEEN_GRID
from data_loader import load_gbpusd_h1
from gui.trade_model import get_model_run_params, load_active_model_id
from run_backtest import run_walk_forward


def _pack(result: dict, label: str) -> dict:
  o = result["overall_oos"]
  y = result["last_1_year"]
  return {
    "label": label,
    "n_trades": o["n_trades"],
    "trades_per_week": o["trades_per_week"],
    "win_rate_pct": o["win_rate_pct"],
    "avg_rr": o["avg_rr"],
    "profit_factor": o["profit_factor"],
    "total_r": o["total_r"],
    "max_dd_r": o["max_drawdown_r"],
    "year_total_r": y["total_r"],
  }


def _print_table(title: str, rows: list[dict]):
  print(f"\n{'='*60}\n{title}\n{'='*60}")
  print(f"{'Case':<22} {'Lệnh':>6} {'WR%':>7} {'PF':>7} {'TotalR':>9} {'DD':>7}")
  print("-" * 60)
  for r in rows:
    print(
      f"{r['label']:<22} {r['n_trades']:6.0f} {r['win_rate_pct']:7.1f} "
      f"{r['profit_factor']:7.3f} {r['total_r']:+9.2f} {r['max_dd_r']:7.2f}"
    )
  best = max(rows, key=lambda x: x["total_r"])
  print(f"\n→ Tốt nhất: **{best['label']}** ({best['total_r']:+.2f}R)")


def main():
  import argparse
  p = argparse.ArgumentParser()
  p.add_argument("--oos-from", default="2025-01-01")
  p.add_argument("--oos-to", default="2026-12-31")
  p.add_argument("--out", type=Path, default=ROOT / "results" / "exec_params_compare.json")
  p.add_argument("--only", choices=["bars", "trail", "all"], default="all")
  args = p.parse_args()

  params = get_model_run_params()
  df = load_gbpusd_h1("2022-01-01")
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

  out_data: dict = {"model_id": load_active_model_id()}

  if args.only in ("bars", "all"):
    print("\n### MIN_BARS_BETWEEN ###")
    bar_rows = []
    scenarios = [(g, {"min_bars_between": g}) for g in MIN_BARS_BETWEEN_GRID]
    scenarios.append(("auto", {}))
    for key, kw in scenarios:
      label = f"gap={key}" if key != "auto" else "auto (miner)"
      print(f"\n--- {label} ---")
      r = run_walk_forward(**common, **kw)
      bar_rows.append(_pack(r, label))
    _print_table("MIN BARS BETWEEN", bar_rows)
    out_data["min_bars"] = bar_rows
    out_data["min_bars_winner"] = max(bar_rows, key=lambda x: x["total_r"])["label"]

  if args.only in ("trail", "all"):
    print("\n### TRAIL HYBRID ###")
    trail_rows = []
    for i, tw in enumerate(HYBRID_TRAIL_COMPARE_GRID):
      act, dist = tw["trail_activate_r"], tw["trail_distance_r"]
      label = f"act={act}/dist={dist}"
      print(f"\n--- {label} ---")
      r = run_walk_forward(**common, trail_hybrid=(act, dist))
      trail_rows.append(_pack(r, label))
    print("\n--- auto (miner) ---")
    r = run_walk_forward(**common)
    trail_rows.append(_pack(r, "auto (miner)"))
    _print_table("TRAIL HYBRID", trail_rows)
    out_data["trail_hybrid"] = trail_rows
    out_data["trail_winner"] = max(trail_rows, key=lambda x: x["total_r"])["label"]

  args.out.parent.mkdir(parents=True, exist_ok=True)
  with open(args.out, "w", encoding="utf-8") as f:
    json.dump(out_data, f, indent=2, ensure_ascii=False)
  print(f"\nĐã lưu: {args.out}")


if __name__ == "__main__":
  main()
