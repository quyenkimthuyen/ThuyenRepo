#!/usr/bin/env python3
"""Generate backtest report for BestTrade Pin Bar Elite."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from besttrade.reporting import build_report, format_text_report, save_report


def main() -> int:
    parser = argparse.ArgumentParser(description="BestTrade — backtest report")
    parser.add_argument("--from-year", type=int, default=2023)
    parser.add_argument("--to-year", type=int, default=2026)
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--risk", type=float, default=2.0, help="Risk % per trade")
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-save", action="store_true", help="Print only, don't write files")
    args = parser.parse_args()

    years = list(range(args.from_year, args.to_year + 1))
    sl_pct = args.risk / 100.0

    report = build_report(years, args.equity, sl_pct, args.rr)
    print(format_text_report(report))

    if not args.no_save:
        paths = save_report(report, args.output_dir)
        print()
        print("Đã lưu:")
        for kind, path in paths.items():
            print(f"  {kind}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
