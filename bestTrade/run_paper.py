#!/usr/bin/env python3
"""CLI paper trading loop for BestTrade."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from besttrade.params import load_forward_test, locked_risk
from besttrade.paper import run_paper_once
from besttrade.store import reset_paper


def main() -> int:
    parser = argparse.ArgumentParser(description="BestTrade paper trading — Pin Bar Elite")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--refresh", action="store_true", help="Refresh Dukascopy data")
    parser.add_argument("--sandbox", action="store_true", help="Use sandbox params (not for forward test)")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval-minutes", type=float, default=15.0)
    parser.add_argument("--reset", action="store_true", help="Reset paper state before run")
    args = parser.parse_args()

    if args.reset:
        reset_paper()
        print("Paper state reset.")

    risk = locked_risk()
    forward = load_forward_test()
    if forward and forward.get("status") == "active" and args.sandbox:
        print("WARNING: Forward test active — không nên dùng --sandbox")

    while True:
        result = run_paper_once(
            equity=args.equity,
            refresh_data=args.refresh,
            sandbox=args.sandbox,
            sl_pct=risk["sl_pct"],
            min_rr=risk["min_rr"],
        )
        state = result["state"]
        print(
            f"bar={result['latest_bar'][:19]} status={state.get('status')} "
            f"equity=${state.get('equity', 0):,.2f} events={len(result['events'])} "
            f"closed={len(state.get('closed_trades', []))}"
        )
        for ev in result["events"]:
            t = ev.get("trade", {})
            print(f"  {ev['event'].upper()}: {t.get('direction')} @ {t.get('entry_time', '')[:16]}")
        if not args.loop:
            return 0
        time.sleep(max(60.0, args.interval_minutes * 60.0))


if __name__ == "__main__":
    raise SystemExit(main())
