#!/usr/bin/env python3
"""Compare strategy effectiveness across 15M / 30M / 1H / 4H entry timeframes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import htf_for_entry, to_entry_timeframe
from systemtrain.optimize.backtest_mine import BacktestMiner
from systemtrain.orchestrator.pipeline import TrainingPipeline


TIMEFRAMES = ["15m", "30m", "1h", "4h"]


def run_timeframe(
    entry_tf: str,
    config: Config,
    equity: float = 1000.0,
    trials: int = 80,
) -> dict:
    pipe = TrainingPipeline(config)
    df = pipe.load_data()
    df = to_entry_timeframe(df, entry_tf)
    train_df, oos_df = split_train_oos(
        df, config.data.get("train_years", 1), config.data.get("oos_years", 2)
    )
    htf = htf_for_entry(entry_tf)
    train_df = prepare_dataframe(train_df, htf_rule=htf)
    oos_df = prepare_dataframe(oos_df, htf_rule=htf)

    risk = RiskConfig(
        sl_pct=config.risk.get("sl_pct", 0.02),
        min_rr=config.risk.get("min_rr", 2.0),
        max_drawdown=config.risk.get("max_drawdown", 0.30),
        max_consecutive_losses=config.risk.get("max_consecutive_losses", 10),
    )
    bt = config.backtest
    engine = BacktestEngine(
        risk, bt.get("initial_equity", 10000),
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )
    engine_eq = BacktestEngine(
        risk, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )

    ga = BacktestMiner(
        engine=engine, train_df=train_df, fitness_cfg=config.fitness,
        wf_cfg=config.walk_forward, top_k=4, random_trials=trials, seed=42,
    ).run()

    if not ga.best_candidates:
        return {"entry_tf": entry_tf, "htf": htf, "error": "no candidates"}

    gene = ga.best_candidates[0].gene
    train_m = compute_metrics(engine_eq.run(train_df, gene))
    oos_m = compute_metrics(engine_eq.run(oos_df, gene))

    return {
        "entry_tf": entry_tf,
        "htf_filter": htf,
        "train_bars": len(train_df),
        "oos_bars": len(oos_df),
        "train_period": f"{train_df.index.min().date()} -> {train_df.index.max().date()}",
        "oos_period": f"{oos_df.index.min().date()} -> {oos_df.index.max().date()}",
        "train": train_m,
        "oos": oos_m,
        "equity_start": equity,
        "equity_end": round(equity * (1 + oos_m["total_return"]), 2),
        "wf": ga.best_candidates[0].wf_summary,
        "setup": gene.learned_setup,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare EURUSD timeframes")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--trials", type=int, default=80)
    parser.add_argument("--tf", nargs="*", default=None, help="Subset e.g. --tf 1h 4h")
    args = parser.parse_args()

    config = Config.load()
    tfs = args.tf or TIMEFRAMES
    results = []

    print(f"So sánh timeframe EURUSD | train 1yr + OOS 2yr | ${args.equity:.0f} | trials={args.trials}\n")

    for tf in tfs:
        print(f"--- {tf.upper()} (HTF {htf_for_entry(tf)}) ---")
        r = run_timeframe(tf, config, args.equity, args.trials)
        results.append(r)
        if "error" in r:
            print(f"  Lỗi: {r['error']}\n")
            continue
        t, o = r["train"], r["oos"]
        print(f"  Train: WR={t['win_rate']:.1%} PF={t['profit_factor']:.2f} ret={t['total_return']:+.1%} ({t['trade_count']} lệnh)")
        print(f"  OOS:   WR={o['win_rate']:.1%} PF={o['profit_factor']:.2f} ret={o['total_return']:+.1%} ({o['trade_count']} lệnh)")
        print(f"  ${args.equity:.0f} -> ${r['equity_end']:.2f}\n")

    ranked = sorted(
        [r for r in results if "oos" in r],
        key=lambda x: x["oos"]["total_return"],
        reverse=True,
    )

    print("=" * 72)
    print(f"  BẢNG XẾP HẠNG OOS (${args.equity:.0f})")
    print("=" * 72)
    print(f"{'TF':>5} {'HTF':>5} {'OOS WR':>8} {'PF':>6} {'Return':>9} {'$End':>9} {'Lệnh':>6}")
    print("-" * 72)
    for r in ranked:
        o = r["oos"]
        print(
            f"{r['entry_tf']:>5} {r['htf_filter']:>5} {o['win_rate']:7.1%} "
            f"{o['profit_factor']:6.2f} {o['total_return']:+8.1%} ${r['equity_end']:8.2f} {o['trade_count']:6d}"
        )
    if ranked:
        w = ranked[0]
        print("=" * 72)
        print(f"  TỐT NHẤT: {w['entry_tf'].upper()} + filter {w['htf_filter']} "
              f"→ {w['oos']['total_return']:+.1%} (${w['equity_end']:.2f})")
        print("=" * 72)

    out = Path("output/timeframe_compare_report.json")
    out.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
