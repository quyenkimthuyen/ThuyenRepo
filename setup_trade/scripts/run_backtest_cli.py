#!/usr/bin/env python3
"""CLI backtest — chạy không cần UI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.data.loader import load_candles, slice_period  # noqa: E402
from backend.indicators import add_indicators  # noqa: E402
from backend.simulator.backtest import run_backtest  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Setup Trade backtest")
    parser.add_argument("--period", default="bt_2023", help="Period id from config/periods.json")
    parser.add_argument("--json", action="store_true", help="Output full JSON")
    args = parser.parse_args()

    df = add_indicators(slice_period(load_candles(), args.period))
    result = run_backtest(df, args.period)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    m = result["metrics"]
    print(f"Period: {args.period}")
    print(f"Trades: {m['trades']} | WR: {m['win_rate']:.1%} | PF: {m['profit_factor']}")
    print(f"Expectancy: {m['expectancy_pips']} pips | Total: {m['total_pips']} pips")
    print(f"Max DD: {m['max_drawdown_pips']} pips")
    print(f"PASS: {result['pass']}")
    if m.get("by_setup"):
        print("\nBy setup:")
        for sid, s in m["by_setup"].items():
            print(f"  {sid}: {s['trades']} trades, WR {s['win_rate']:.1%}, exp {s['expectancy_pips']} pips")


if __name__ == "__main__":
    main()
