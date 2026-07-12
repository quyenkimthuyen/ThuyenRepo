#!/usr/bin/env python3
"""CLI backtest for BestTrade Pin Bar Elite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from besttrade.engine import load_strategy_config, run_multi_year, run_year_backtest


def main() -> int:
    parser = argparse.ArgumentParser(description="BestTrade — Pin Bar Elite backtest")
    parser.add_argument("--year", type=int, nargs="+", default=[2023, 2024, 2025])
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--risk", type=float, default=2.0, help="Risk % per trade")
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = load_strategy_config()
    sl_pct = args.risk / 100.0
    results = run_multi_year(args.year, cfg["params"], args.equity, sl_pct, args.rr)

    if args.json:
        out = {
            str(r.year): r.metrics for r in results
        }
        print(json.dumps(out, indent=2))
        return 0

    print("=" * 60)
    print("  BestTrade — Pin Bar Elite Backtest")
    print(f"  Equity: ${args.equity:,.0f} | Risk: {args.risk}% | RR: {args.rr}")
    print("=" * 60)
    for r in results:
        m = r.metrics
        print(
            f"  {r.year}: {m.get('trade_count', 0):3d} trades | "
            f"WR {m.get('win_rate', 0):.0%} | PF {m.get('profit_factor', 0):.2f} | "
            f"Return {m.get('total_return', 0):+.1%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
