#!/usr/bin/env python3
"""Production — rolling param (re-mine 1 năm trước) hoặc config cố định."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from systemtrain.config import Config
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.orchestrator.rolling_production import (
    ACTIVE_PATH,
    backtest_trade_year,
    current_trade_year,
    ensure_active_state,
    load_active_state,
    state_from_fixed,
    train_year_for,
)
from systemtrain.optimize.rolling_year import metrics_in_window, slice_year

MIN_OOS_WR = 0.60


def _print_row(name: str, period: str, m: dict, equity: float) -> None:
    end = equity * (1 + m.get("total_return", 0))
    print(
        f"  {name:<16} {period:<12} {m.get('trade_count', 0):>3} lệnh | "
        f"WR {m.get('win_rate', 0):>5.1%} | PF {m.get('profit_factor', 0):>5.2f} | "
        f"RR {m.get('realized_rr', 0):>4.2f} | {m.get('total_return', 0):>+6.1%} | ${end:.2f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Production backtest with rolling yearly params")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--trade-year", type=int, default=None, help="Năm trade (default: năm hiện tại)")
    parser.add_argument("--remine", action="store_true", help="Re-optimize trên năm trước rồi lưu")
    parser.add_argument("--static", action="store_true", help="Dùng config yaml cố định, không rolling")
    args = parser.parse_args()

    config = Config.load()
    df_1h = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
    trade_year = args.trade_year or current_trade_year()
    train_y = train_year_for(trade_year)

    if args.static:
        state = state_from_fixed(trade_year, args.equity)
        mode = "static"
    else:
        state = ensure_active_state(trade_year, force_remine=args.remine, equity=args.equity)
        mode = "rolling"

    trade_result = backtest_trade_year(state, config, args.equity, df_1h)
    train_df, train_s, train_e = slice_year(df_1h, train_y)

    from systemtrain.orchestrator.rolling_production import build_engines_from_state

    print("=" * 78)
    print("  PRODUCTION — Wyckoff + RSI + EMA + Pin Bar | EURUSD 1H")
    print("=" * 78)
    print(f"  Mode       : {mode}")
    print(f"  Train year : {train_y} (optimize)")
    print(f"  Trade year : {trade_year}")
    if state.get("optimized_at"):
        print(f"  Optimized  : {state['optimized_at'][:19]}")
    print(f"  Config     : {ACTIVE_PATH if not args.static else 'config/*.yaml (fixed)'}")
    print(f"  Vốn        : ${args.equity:,.0f} | SL 2%/lệnh")
    print("=" * 78)
    print(f"  {'Chiến lược':<16} {'Giai đoạn':<12} {'':>3}   {'WR':>7}   {'PF':>5}   {'RR':>4}   {'Return':>7}")
    print("  " + "-" * 74)

    report: dict = {
        "mode": mode,
        "trade_year": trade_year,
        "train_year": train_y,
        "state": state,
        "strategies": {},
    }
    active_returns: list[float] = []

    for sname, engine in build_engines_from_state(state, config, args.equity):
        tr = metrics_in_window(engine.run(train_df), train_s, train_e, args.equity)
        td = trade_result["strategies"][sname]
        params = state["strategies"][sname]["params"]
        _print_row(sname, f"Train {train_y}", tr, args.equity)
        _print_row(sname, f"Trade {trade_year}", td, args.equity)
        print(f"  {'':16} {'':12}  params: {params}")
        report["strategies"][sname] = {"train": tr, "trade": td, "params": params}
        if td.get("win_rate", 0) > MIN_OOS_WR or td.get("trade_count", 0) == 0:
            active_returns.append(td.get("total_return", 0))

    combined = trade_result["combined_return"]
    print("\n  " + "-" * 74)
    print(f"  Tổng trade {trade_year} : {combined:+.1%} → ${args.equity * (1 + combined):.2f}")
    print("=" * 78)
    print("\n  Lịch re-mine: đầu mỗi năm chạy  python3 run_rolling_remine.py")
    print("  Hoặc:           python3 run_production.py --remine")
    print("=" * 78)

    Path("output").mkdir(exist_ok=True)
    Path("output/production_report.json").write_text(json.dumps(report, indent=2, default=str))
    print("Saved: output/production_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
