#!/usr/bin/env python3
"""Re-mine rolling: tối ưu năm trước → lưu param cho năm trade hiện tại."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from systemtrain.config import Config
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.orchestrator.rolling_production import (
    ACTIVE_PATH,
    backtest_trade_year,
    current_trade_year,
    ensure_active_state,
    optimize_for_trade_year,
    save_active_state,
    save_state_for_year,
    train_year_for,
)
from systemtrain.optimize.rolling_year import MIN_TRADES_PER_YEAR, MIN_WIN_RATE


def main() -> int:
    parser = argparse.ArgumentParser(description="Rolling re-mine — optimize prior year for current trade year")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--trade-year", type=int, default=None, help="Năm trade (default: năm hiện tại)")
    parser.add_argument("--all", action="store_true", help="Re-mine tất cả folds 2021→2026 và lưu history")
    args = parser.parse_args()

    config = Config.load()
    df_1h = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")

    if args.all:
        from systemtrain.optimize.rolling_year import ROLLING_FOLDS

        print("=" * 72)
        print("  ROLLING RE-MINE — Tất cả folds")
        print("=" * 72)
        for train_y, trade_y in ROLLING_FOLDS:
            state = optimize_for_trade_year(trade_y, config, args.equity, df_1h)
            save_state_for_year(state, trade_y, set_active=(trade_y == current_trade_year()))
            bt = backtest_trade_year(state, config, args.equity, df_1h)
            print(f"\n  Train {train_y} → Trade {trade_y} | Tổng {bt['combined_return']:+.1%}")
            for sname, m in bt["strategies"].items():
                tr = state["strategies"][sname]["train"]
                ok = "✓" if tr.get("constraints_met") else "✗"
                print(
                    f"    {sname:<16} train {tr.get('trade_count', 0):2}t WR{tr.get('win_rate', 0):.0%} {ok} | "
                    f"trade {m['trade_count']:2}t WR{m['win_rate']:.0%} {m['total_return']:+.1%}"
                )
        print(f"\n  Active: {ACTIVE_PATH}")
        return 0

    trade_year = args.trade_year or current_trade_year()
    train_y = train_year_for(trade_year)

    print("=" * 72)
    print(f"  ROLLING RE-MINE — Train {train_y} → Trade {trade_year}")
    print("=" * 72)

    state = optimize_for_trade_year(trade_year, config, args.equity, df_1h)
    save_state_for_year(state, trade_year, set_active=True)

    print(f"  Ràng buộc: >{MIN_TRADES_PER_YEAR - 1} lệnh/năm, WR >{MIN_WIN_RATE:.0%} (trên năm train)")
    for sname, data in state["strategies"].items():
        tr = data["train"]
        ok = "ĐẠT" if tr.get("constraints_met") else "CHƯA ĐẠT (best-effort)"
        print(f"\n  {sname} — {ok}")
        print(f"    Train {train_y}: {tr.get('trade_count', 0)}t WR{tr.get('win_rate', 0):.0%} {tr.get('total_return', 0):+.1%}")
        print(f"    Params: {data['params']}")

    bt = backtest_trade_year(state, config, args.equity, df_1h)
    print(f"\n  YTD trade {trade_year}: tổng {bt['combined_return']:+.1%}")
    for sname, m in bt["strategies"].items():
        print(f"    {sname:<16} {m['trade_count']:2}t WR{m['win_rate']:.0%} {m['total_return']:+.1%}")

    print(f"\n  Saved: {ACTIVE_PATH}")
    print(f"  History: config/rolling/history/{trade_year}.yaml")
    Path("output/rolling_remine_report.json").write_text(json.dumps({"state": state, "trade": bt}, indent=2, default=str))
    print("  Saved: output/rolling_remine_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
