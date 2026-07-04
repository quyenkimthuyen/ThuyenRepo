#!/usr/bin/env python3
"""Try all mining/selection configs, pick winner by blind OOS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from systemtrain.config import Config
from systemtrain.experiments.benchmark import run_all_experiments


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark all strategy configs")
    parser.add_argument("--trials", type=int, default=100, help="Mining trials per mode")
    parser.add_argument("--quick", action="store_true", help="Smaller config matrix")
    parser.add_argument("--apply", action="store_true", help="Write winner to config/default.yaml")
    args = parser.parse_args()

    config = Config.load()
    results, winner = run_all_experiments(config, trials=args.trials, quick_specs=args.quick)

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)

    ranked = sorted(results, key=lambda r: r.score, reverse=True)
    report = {
        "winner": None,
        "rankings": [],
    }
    for rank, r in enumerate(ranked[:15], 1):
        o = r.oos_metrics
        entry = {
            "rank": rank,
            "name": r.spec.name,
            "mine_mode": r.spec.mine_mode,
            "portfolio_n": r.spec.portfolio_n,
            "filter_mode": r.spec.filter_mode,
            "select_mode": r.spec.select_mode,
            "oos_return": o.get("total_return", 0),
            "oos_pf": o.get("profit_factor", 0),
            "oos_wr": o.get("win_rate", 0),
            "oos_trades": o.get("trade_count", 0),
            "oos_dd": o.get("max_drawdown", 0),
            "score": r.score,
        }
        report["rankings"].append(entry)

    if winner:
        w = winner.spec
        wo = winner.oos_metrics
        report["winner"] = {
            "name": w.name,
            "mine_mode": w.mine_mode,
            "portfolio_n": w.portfolio_n,
            "filter_mode": w.filter_mode,
            "select_mode": w.select_mode,
            "oos_return": wo.get("total_return", 0),
            "oos_pf": wo.get("profit_factor", 0),
            "oos_wr": wo.get("win_rate", 0),
            "oos_trades": wo.get("trade_count", 0),
            "score": winner.score,
        }

    report_path = out_dir / "experiment_report.json"
    with report_path.open("w") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 72)
    print("  TOP 5 (blind OOS)")
    print("=" * 72)
    for entry in report["rankings"][:5]:
        print(
            f"  #{entry['rank']} {entry['name']:35s} "
            f"ret={entry['oos_return']:+6.1%} PF={entry['oos_pf']:.2f} "
            f"WR={entry['oos_wr']:.1%} trades={entry['oos_trades']} score={entry['score']:.1f}"
        )

    if winner:
        w = report["winner"]
        print("\n" + "=" * 72)
        print(f"  WINNER: {w['name']}")
        print(f"  OOS return={w['oos_return']:+.1%}  PF={w['oos_pf']:.2f}  WR={w['oos_wr']:.1%}")
        print(f"  Config: mine={w['mine_mode']} portfolio={w['portfolio_n']} "
              f"filter={w['filter_mode']} select={w['select_mode']}")
        print("=" * 72)

        if args.apply:
            _apply_winner(config, winner.spec)
            print("\nApplied winner to config/default.yaml")

    print(f"\nFull report: {report_path}")
    return 0


def _apply_winner(config: Config, spec) -> None:
    import yaml
    path = Path(__file__).resolve().parent / "config" / "default.yaml"
    with path.open() as f:
        raw = yaml.safe_load(f)
    raw["optimize"]["quarterly_remine"] = spec.mine_mode == "quarterly"
    raw["optimize"]["portfolio_mode"] = spec.portfolio_n > 1
    raw["optimize"]["top_k"] = spec.portfolio_n
    raw["optimize"]["filter_mode"] = spec.filter_mode
    raw["optimize"]["select_mode"] = spec.select_mode
    raw["optimize"]["best_mode"] = spec.name
    with path.open("w") as f:
        yaml.dump(raw, f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    sys.exit(main())
