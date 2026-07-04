#!/usr/bin/env python3
"""Backtest Wyckoff H1 + filter 4H — optimize, báo cáo lợi nhuận & RR."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.wyckoff_engine import WyckoffEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.optimize.wyckoff_optimize import optimize_wyckoff
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.wyckoff import WyckoffConfig, detect_wyckoff_signals

RR_SWEEP = [1.5, 2.0, 2.5, 3.0]


def _print_metrics(label: str, m: dict, equity: float, target_rr: float) -> None:
    end = equity * (1 + m.get("total_return", 0))
    profit = end - equity
    max_dd = m.get("max_drawdown", 0) * equity
    print(f"  [{label}]")
    print(f"    Lệnh     : {m.get('trade_count', 0)}")
    print(f"    WR       : {m.get('win_rate', 0):.1%}")
    print(f"    PF       : {m.get('profit_factor', 0):.2f}")
    print(f"    RR target: {target_rr:.2f} | RR thực tế: {m.get('realized_rr', 0):.2f}")
    print(f"    Avg win  : ${m.get('avg_win', 0):.2f} | Avg loss: ${m.get('avg_loss', 0):.2f}")
    print(f"    Lợi nhuận: {m.get('total_return', 0):+.1%} (${profit:+.2f})")
    print(f"    Tài khoản: ${equity:.0f} → ${end:.2f}")
    print(f"    Max DD   : {m.get('max_drawdown', 0):.1%} (${max_dd:.2f})")
    print()


def _run_period(engine: WyckoffEngine, data, wcfg: WyckoffConfig, label: str, equity: float) -> dict:
    r = engine.run(data)
    m = r.metrics
    sigs = detect_wyckoff_signals(data, wcfg)
    print(f"  {label}  {data.index.min().date()} → {data.index.max().date()}")
    print(f"    Tín hiệu H1: {len(sigs)}")
    _print_metrics(label, m, equity, wcfg.rr)
    if r.halted:
        print(f"    ⚠ {r.halt_reason}\n")
    return m


def _rr_sweep(oos_df, base_cfg: WyckoffConfig, equity: float, bt: dict, pip: float) -> list[dict]:
    rows = []
    print("  ── RR SWEEP (OOS 2 năm blind) ──")
    print(f"  {'RR':>5} {'Lệnh':>5} {'WR':>7} {'PF':>6} {'RR thực':>8} {'Return':>8} {'Lợi nhuận':>10}")
    print("  " + "-" * 58)
    for rr in RR_SWEEP:
        wcfg = WyckoffConfig(**{**base_cfg.to_dict(), "rr": rr})
        engine = WyckoffEngine(
            RiskConfig(0.02, rr, 0.30, 10), wcfg, equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
        )
        m = engine.run(oos_df).metrics
        profit = equity * m.get("total_return", 0)
        print(
            f"  {rr:>5.1f} {m.get('trade_count', 0):>5} "
            f"{m.get('win_rate', 0):>6.1%} {m.get('profit_factor', 0):>6.2f} "
            f"{m.get('realized_rr', 0):>8.2f} {m.get('total_return', 0):>+7.1%} "
            f"${profit:>+9.2f}"
        )
        rows.append({"rr": rr, **m})
    print()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--preset", choices=["quality", "high_wr", "balanced"], default="quality",
                        help="quality=WR cao | high_wr=thêm lệnh giữ WR~50% | balanced=nhiều lệnh")
    parser.add_argument("--optimize", action="store_true", default=False)
    parser.add_argument("--no-optimize", action="store_false", dest="optimize")
    args = parser.parse_args()

    config = Config.load()
    df = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
    train_df, oos_df = split_train_oos(df, 1, 2)
    train_df = prepare_dataframe(train_df, "4h")
    oos_df = prepare_dataframe(oos_df, "4h")
    bt = config.backtest

    print("=" * 70)
    print("  WYCKOFF H1 + QUAN SÁT 4H — Failed Break")
    print("=" * 70)
    print(f"  Entry: 1H | Filter: 4H (chỉ trade theo chiều xu hướng 4H)")
    print(f"  Risk: SL 2%/lệnh | Spread {bt.get('spread_pips', 0.5)} pip")
    print("=" * 70)

    if args.optimize:
        print("\n  Đang tối ưu (grid search trên train)...\n")
        wcfg, ranked = optimize_wyckoff(args.equity)
        if ranked:
            top = ranked[0]
            print(
                f"  Best: days={top['consolidation_days']} wick={top['min_wick_range_ratio']} "
                f"RR={top['rr']} 4H={top['htf_mode']} ADX<{top['max_adx']}"
            )
            print(
                f"  Train: {top['train_trades']} lệnh WR={top['train_wr']:.1%} "
                f"ret={top['train_ret']:+.1%} RR={top['train_rr']:.2f}"
            )
            print(
                f"  OOS  : {top['oos_trades']} lệnh WR={top['oos_wr']:.1%} "
                f"ret={top['oos_ret']:+.1%} PF={top['oos_pf']:.2f} RR={top['oos_rr']:.2f}\n"
            )
        Path("output/wyckoff_optimize.json").write_text(json.dumps(ranked[:15], indent=2))
    else:
        wcfg = WyckoffConfig.preset(args.preset)

    print(f"  Preset: {args.preset} | Filter 4H: {wcfg.htf_mode}", end="")
    if wcfg.htf_mode == "trend_adx":
        print(f" (ADX≥{wcfg.min_htf_adx:.0f})")
    elif wcfg.htf_mode == "stack":
        print(" (EMA21/50 stack)")
    else:
        print()

    engine = WyckoffEngine(
        RiskConfig(0.02, wcfg.rr, 0.30, 10), wcfg, args.equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )

    train_m = _run_period(engine, train_df, wcfg, "TRAIN 1 năm", args.equity)
    oos_m = _run_period(engine, oos_df, wcfg, "OOS 2 năm blind", args.equity)
    rr_rows = _rr_sweep(oos_df, wcfg, args.equity, bt, config.pip_size)

    best_rr = max(rr_rows, key=lambda r: r.get("total_return", -999)) if rr_rows else {}
    report = {
        "config": wcfg.to_dict(),
        "train": train_m,
        "oos": oos_m,
        "rr_sweep_oos": rr_rows,
        "best_rr_oos": best_rr,
    }
    Path("output/wyckoff_report.json").write_text(json.dumps(report, indent=2, default=str))
    Path("config/wyckoff.yaml").write_text(
        "wyckoff:\n" + "\n".join(f"  {k}: {v}" for k, v in wcfg.to_dict().items()) + "\n"
    )
    if best_rr:
        print(f"  RR tốt nhất OOS: {best_rr.get('rr')} → {best_rr.get('total_return', 0):+.1%}")
    print("  Saved: output/wyckoff_report.json, config/wyckoff.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
