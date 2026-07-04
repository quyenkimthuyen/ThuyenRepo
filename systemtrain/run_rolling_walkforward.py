#!/usr/bin/env python3
"""Rolling walk-forward: tối ưu 1 năm → trade năm sau (2021→2022 … 2025→2026)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from systemtrain.config import Config
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.optimize.rolling_year import (
    ROLLING_FOLDS,
    build_ema_engine,
    build_rsi_engine,
    build_wyckoff_engine,
    fixed_params,
    metrics_in_window,
    optimize_ema_year,
    optimize_rsi_year,
    optimize_wyckoff_year,
    slice_year,
    year_bounds,
)
from systemtrain.orchestrator.pipeline import TrainingPipeline

STRATEGIES = [
    ("Wyckoff", optimize_wyckoff_year, build_wyckoff_engine),
    ("RSI Divergence", optimize_rsi_year, build_rsi_engine),
    ("EMA 50/200", optimize_ema_year, build_ema_engine),
]


def _print_metrics(name: str, m: dict) -> str:
    return (
        f"{name:<16} {m.get('trade_count', 0):3} lệnh | "
        f"WR {m.get('win_rate', 0):5.1%} | PF {m.get('profit_factor', 0):5.2f} | "
        f"{m.get('total_return', 0):+6.1%}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Rolling 1Y optimize → next year trade")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--fixed", action="store_true", help="Dùng config cố định, không optimize")
    args = parser.parse_args()

    config = Config.load()
    df_1h = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")

    print("=" * 82)
    print("  ROLLING WALK-FORWARD — Tối ưu 1 năm → Trade năm sau")
    print("=" * 82)
    print(f"  Data: {df_1h.index.min().date()} → {df_1h.index.max().date()}")
    print(f"  Vốn: ${args.equity:,.0f} | SL 2%/lệnh | Chiến lược: Wyckoff + RSI + EMA")
    print(f"  Mode: {'config cố định' if args.fixed else 'grid-search trên năm train'}")
    print("=" * 82)

    report: dict = {"equity": args.equity, "fixed": args.fixed, "folds": []}
    yearly_trade: dict[int, dict] = {}
    fixed = fixed_params()

    for train_y, trade_y in ROLLING_FOLDS:
        train_df, train_s, train_e = slice_year(df_1h, train_y)
        trade_df, trade_s, trade_e = slice_year(df_1h, trade_y)
        t_start, t_end = year_bounds(trade_y)

        print(f"\n  ▶ Train {train_y} ({train_s.date()} → {train_e.date()}) → Trade {trade_y}")
        print("  " + "-" * 78)

        fold = {"train_year": train_y, "trade_year": trade_y, "strategies": {}}
        fold_ret = 0.0

        for sname, opt_fn, build_fn in STRATEGIES:
            if args.fixed:
                params = fixed[sname]
                train_m = metrics_in_window(
                    build_fn(params, config, args.equity).run(train_df), train_s, train_e, args.equity,
                )
            else:
                params, train_m = opt_fn(train_df, train_s, train_e, config, args.equity)

            engine = build_fn(params, config, args.equity)
            trade_m = metrics_in_window(engine.run(trade_df), trade_s, trade_e, args.equity)
            fold_ret += trade_m.get("total_return", 0)

            print(f"    {_print_metrics(sname, trade_m)}")
            if not args.fixed:
                print(f"      train {train_y}: {train_m.get('trade_count',0)}t WR{train_m.get('win_rate',0):.0%} "
                      f"{train_m.get('total_return',0):+.1%} | params: {params}")

            fold["strategies"][sname] = {
                "params": params,
                "train": train_m,
                "trade": trade_m,
            }

        fold["combined_trade_return"] = fold_ret
        report["folds"].append(fold)
        yearly_trade[trade_y] = {"return": fold_ret, "fold": fold}
        print(f"    {'Tổng 3 CL':<16} {fold_ret:+6.1%}")

    # Bảng tổng hợp theo năm trade
    print("\n" + "=" * 82)
    print("  BÁO CÁO THEO NĂM TRADE (sau rolling optimize)")
    print("=" * 82)
    print(f"  {'Năm':<6} {'Wyckoff':>10} {'RSI':>10} {'EMA':>10} {'Tổng':>10} {'Lệnh':>6}")
    print("  " + "-" * 56)

    cum_ret = 0.0
    for train_y, trade_y in ROLLING_FOLDS:
        fold = next(f for f in report["folds"] if f["trade_year"] == trade_y)
        ws = fold["strategies"]["Wyckoff"]["trade"]
        rs = fold["strategies"]["RSI Divergence"]["trade"]
        es = fold["strategies"]["EMA 50/200"]["trade"]
        total = fold["combined_trade_return"]
        cum_ret += total
        n = ws.get("trade_count", 0) + rs.get("trade_count", 0) + es.get("trade_count", 0)
        print(
            f"  {trade_y:<6} {ws.get('total_return',0):+9.1%} {rs.get('total_return',0):+9.1%} "
            f"{es.get('total_return',0):+9.1%} {total:+9.1%} {n:6}"
        )

    print("  " + "-" * 56)
    print(f"  Cộng dồn (độc lập) : {cum_ret:+.1%} → ${args.equity * (1 + cum_ret):.2f}")
    print("=" * 82)

    out = Path("output/rolling_walkforward_report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
