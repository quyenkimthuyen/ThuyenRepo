#!/usr/bin/env python3
"""Chạy walk-forward validation: optimize T+1 → backtest OOS T+2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.research.validation import get_latest_validation, run_walk_forward_validation  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward validation")
    parser.add_argument("--fold", default="fold_a")
    parser.add_argument("--skip-optimize", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--show-last", action="store_true")
    args = parser.parse_args()

    if args.show_last:
        r = get_latest_validation(args.fold)
        print(json.dumps(r, indent=2, default=str))
        return

    result = run_walk_forward_validation(
        args.fold,
        skip_optimize=args.skip_optimize,
        save_strategy=not args.no_save,
    )

    print("=" * 60)
    print(f"FOLD: {args.fold} — {result['verdict']}")
    print("=" * 60)
    for key in ("in_sample", "out_of_sample"):
        p = result[key]
        print(f"\n{p['label']} ({p['period']})")
        print(f"  Trades: {p['trades']} | WR: {p['win_rate']:.1%} | PF: {p['profit_factor']}")
        print(f"  Expectancy: {p['expectancy_pips']} pips | Total: {p['total_pips']} pips")
        print(f"  Max DD: {p['max_drawdown_pips']} pips | PASS: {p['pass']}")
    if result.get("best_params"):
        print(f"\nBest params: {json.dumps(result['best_params'])}")
    if result.get("warnings"):
        print("\nWarnings:")
        for w in result["warnings"]:
            print(f"  - {w}")
    print(f"\nReport: {result['report_path']}")
    print(f"OOS detail: {result['final_report_path']}")


if __name__ == "__main__":
    main()
