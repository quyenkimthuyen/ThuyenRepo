#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time

from systemtrain.live.signal_runner import run_paper_once
from systemtrain.orchestrator.rolling_production import current_trade_year
from systemtrain.ui.meta import STRATEGY_ORDER


def main() -> int:
    parser = argparse.ArgumentParser(description="Run live paper trading for SystemTrain.")
    parser.add_argument("--trade-year", type=int, default=current_trade_year())
    parser.add_argument("--strategy", action="append", choices=STRATEGY_ORDER, help="Strategy to run. Repeat for multiple.")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--refresh-data", action="store_true", help="Refresh recent Dukascopy data before evaluating.")
    parser.add_argument("--warmup-days", type=int, default=90)
    parser.add_argument("--loop", action="store_true", help="Run repeatedly.")
    parser.add_argument("--interval-minutes", type=float, default=15.0)
    args = parser.parse_args()

    strategies = args.strategy or STRATEGY_ORDER
    while True:
        result = run_paper_once(
            trade_year=args.trade_year,
            strategies=strategies,
            equity=args.equity,
            refresh_data=args.refresh_data,
            warmup_days=args.warmup_days,
        )
        print(
            f"latest_bar={result['latest_bar']} bars={result['bars']} "
            f"events={len(result['events'])}"
        )
        if not args.loop:
            return 0
        time.sleep(max(1.0, args.interval_minutes * 60.0))


if __name__ == "__main__":
    raise SystemExit(main())

