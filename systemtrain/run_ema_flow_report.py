#!/usr/bin/env python3
"""EMA Flow — train 2024 optimize, test 2025 & 2026 (không đổi 4 CL production)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from systemtrain.config import Config
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.optimize.rolling_year import (
    _base_ema,
    build_ema_engine,
    build_ema_flow_engine,
    metrics_in_window,
    optimize_ema_flow_year,
    slice_year,
)
from systemtrain.orchestrator.pipeline import TrainingPipeline


def _fmt(m: dict) -> str:
    return (
        f"{m.get('trade_count', 0):3} lệnh | WR {m.get('win_rate', 0):5.1%} | "
        f"PF {m.get('profit_factor', 0):5.2f} | RR {m.get('realized_rr', 0):4.2f} | "
        f"{m.get('total_return', 0):+6.1%}"
    )


def _run_year(engine_builder, params: dict, config: Config, df_1h, year: int, equity: float) -> dict:
    df, s, e = slice_year(df_1h, year)
    engine = engine_builder(params, config, equity)
    return metrics_in_window(engine.run(df), s, e, equity)


def main() -> int:
    parser = argparse.ArgumentParser(description="EMA Flow walk-forward: train 2024 → test 2025/2026")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--train-year", type=int, default=2024)
    args = parser.parse_args()

    config = Config.load()
    df_1h = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
    train_y = args.train_year
    test_years = [train_y + 1, train_y + 2]

    train_df, train_s, train_e = slice_year(df_1h, train_y)

    print("=" * 78)
    print(f"  EMA FLOW — Train {train_y} → Test {test_years[0]} & {test_years[1]}")
    print(f"  Mode flow: nới filter, tăng lệnh | 4 CL production giữ nguyên")
    print("=" * 78)

    flow_params, flow_train = optimize_ema_flow_year(train_df, train_s, train_e, config, args.equity)

    base = _base_ema().to_dict()
    elite_keys = ("min_htf_adx", "max_adx_1h", "pullback_atr", "max_ema_spread_atr", "htf_mode", "require_bounce")
    elite_params = {k: base[k] for k in elite_keys if k in base}

    report: dict = {
        "train_year": train_y,
        "test_years": test_years,
        "equity": args.equity,
        "constraints": {"min_win_rate": 0.50, "min_trades": 10},
        "ema_flow": {"params": flow_params, "train": flow_train, "test": {}},
        "ema_elite": {"params": {}, "train": {}, "test": {}},
    }

    print(f"\n  {'Chiến lược':<18} {'Giai đoạn':<12} Kết quả")
    print("  " + "-" * 68)

    for label, builder, params, train_m in (
        ("EMA Flow", build_ema_flow_engine, flow_params, flow_train),
    ):
        ok = "✓" if train_m.get("constraints_met") else "✗"
        hold = train_m.get("holdout", {})
        hold_s = f" | H2: {hold.get('trade_count', 0)}t WR{hold.get('win_rate', 0):.0%}" if hold else ""
        print(f"  {label:<18} Train {train_y:<6} {_fmt(train_m)} {ok}{hold_s}")
        for ty in test_years:
            m = _run_year(builder, params, config, df_1h, ty, args.equity)
            report["ema_flow"]["test"][str(ty)] = m
            wr_ok = "✓" if m.get("win_rate", 0) > 0.50 else "✗"
            print(f"  {label:<18} Trade {ty:<6} {_fmt(m)} WR{wr_ok}")

    elite_params = {k: base[k] for k in elite_keys if k in base}
    elite_train = _run_year(build_ema_engine, elite_params, config, df_1h, train_y, args.equity)
    print(f"\n  {'— so sánh —':<18}")
    print(f"  {'EMA 50/200 Elite':<18} Train {train_y:<6} {_fmt(elite_train)}")
    for ty in test_years:
        m = _run_year(build_ema_engine, elite_params, config, df_1h, ty, args.equity)
        report["ema_elite"]["test"][str(ty)] = m
        print(f"  {'EMA 50/200 Elite':<18} Trade {ty:<6} {_fmt(m)}")

    report["ema_elite"]["params"] = elite_params
    report["ema_elite"]["train"] = elite_train

    print("\n  Params EMA Flow:")
    print(f"    {flow_params}")
    print("  Params EMA Elite (production hiện tại):")
    print(f"    {elite_params}")

    out = Path("output/ema_flow_report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\n  Saved: {out}")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
