#!/usr/bin/env python3
"""Run strategy pipeline test and print detailed report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from systemtrain.config import Config
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.reporting import print_strategy_report, summary_dict


def run_test(quick: bool = True, csv_path: str | None = None, regenerate: bool = False) -> int:
    config = Config.load()
    pipeline = TrainingPipeline(config)

    print("Running strategy pipeline test...")
    print(f"  Symbol   : {config.symbol}")
    print(f"  Timeframe: {config.timeframe}")
    print(f"  Mode     : {'quick' if quick else 'full'}")
    print(f"  Risk     : SL={config.risk.get('sl_pct', 0.02):.0%}  RR>={config.risk.get('min_rr', 2)}")
    print()

    result = pipeline.run(csv_path=csv_path, force_regenerate=regenerate, quick=quick)
    results = result.validated_strategies

    print_strategy_report(
        results,
        title=f"EURUSD {config.timeframe} + {getattr(config, 'htf_timeframe', '4h')} filter ({'quick' if quick else 'full'})",
    )

    summary = summary_dict(results)
    print(f"\nAGGREGATE:")
    print(f"  Strategies kept       : {summary['total']}")
    print(f"  Passed (gate off)     : {summary['passed']}")

    if result.portfolio_oos:
        po = result.portfolio_oos.get("oos_metrics", {})
        print(f"\n  PORTFOLIO OOS (3 strategies combined):")
        print(f"    WR     : {po.get('win_rate', 0):.1%}")
        print(f"    PF     : {po.get('profit_factor', 0):.2f}")
        print(f"    DD     : {po.get('max_drawdown', 0):.1%}")
        print(f"    Trades : {po.get('trade_count', 0)}")
        print(f"    Return : {po.get('total_return', 0):.1%}")
    print(f"  Train period         : {result.train_df.index.min()} -> {result.train_df.index.max()}")
    print(f"  OOS period           : {result.oos_df.index.min()} -> {result.oos_df.index.max()}")
    print(f"  Report saved         : {result.output_dir / 'run_report.json'}")

    report_path = result.output_dir / "test_report.json"
    with report_path.open("w") as f:
        json.dump(
            {
                "summary": summary,
                "strategies": results,
                "train_bars": len(result.train_df),
                "oos_bars": len(result.oos_df),
            },
            f,
            indent=2,
            default=str,
        )
    print(f"  Test report saved    : {report_path}")

    subprocess.run([sys.executable, "analyze_run.py"], cwd=Path(__file__).resolve().parent, check=False)

    return 0 if summary["total"] > 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run strategy test with detailed report")
    parser.add_argument("--full", action="store_true", help="Full GA (slower)")
    parser.add_argument("--csv", type=str, default=None)
    parser.add_argument("--regenerate-data", action="store_true")
    args = parser.parse_args()
    return run_test(quick=not args.full, csv_path=args.csv, regenerate=args.regenerate_data)


if __name__ == "__main__":
    sys.exit(main())
