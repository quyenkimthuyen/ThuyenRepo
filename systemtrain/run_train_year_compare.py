#!/usr/bin/env python3
"""
Train 1 trong 3 năm, test 2 năm còn lại (không overlap).
Ví dụ: train 2025-2026 → test 2023-2024 + 2024-2025 (data quá khứ, chưa thấy khi train).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.timeframes import htf_for_entry, to_entry_timeframe
from systemtrain.optimize.backtest_mine import BacktestMiner
from systemtrain.orchestrator.pipeline import TrainingPipeline


def annual_slices(df: pd.DataFrame) -> list[tuple[int, pd.Timestamp, pd.Timestamp, pd.DataFrame]]:
    """Split into 3 non-overlapping 1-year chunks."""
    start = df.index.min()
    chunks = []
    for i in range(3):
        t0 = start + pd.DateOffset(years=i)
        t1 = start + pd.DateOffset(years=i + 1)
        chunk = df.loc[(df.index >= t0) & (df.index < t1)].copy()
        label = i + 1
        year_label = f"{t0.year}-{t1.year}"
        chunks.append((label, t0, t1, chunk))
    return chunks


def run_case(
    train_year: int,
    chunks: list,
    engine: BacktestEngine,
    engine_eq: BacktestEngine,
    config: Config,
    htf: str,
    trials: int,
) -> dict:
    train_chunk = next(c for c in chunks if c[0] == train_year)
    test_chunks = [c for c in chunks if c[0] != train_year]

    _, t0, t1, train_raw = train_chunk
    train_df = prepare_dataframe(train_raw, htf)

    test_parts = [prepare_dataframe(c[3], htf) for c in sorted(test_chunks, key=lambda x: x[0])]
    oos_df = pd.concat(test_parts).sort_index()

    ga = BacktestMiner(
        engine=engine, train_df=train_df, fitness_cfg=config.fitness,
        wf_cfg=config.walk_forward, top_k=4, random_trials=trials, seed=42,
    ).run()

    if not ga.best_candidates:
        return {"train_year": train_year, "error": "no candidates"}

    gene = ga.best_candidates[0].gene
    train_m = compute_metrics(engine_eq.run(train_df, gene))
    oos_m = compute_metrics(engine_eq.run(oos_df, gene))

    test_desc = " + ".join(
        f"Năm{c[0]}({c[1].date()}→{c[2].date()})" for c in sorted(test_chunks, key=lambda x: x[0])
    )

    return {
        "train_year": train_year,
        "train_period": f"{t0.date()} → {t1.date()}",
        "test_period": f"{oos_df.index.min().date()} → {oos_df.index.max().date()}",
        "test_years": test_desc,
        "train_bars": len(train_df),
        "test_bars": len(oos_df),
        "train": train_m,
        "oos": oos_m,
        "equity_end": 1000 * (1 + oos_m["total_return"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--trials", type=int, default=80)
    args = parser.parse_args()

    config = Config.load()
    df = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
    htf = htf_for_entry("1h")
    chunks = annual_slices(df)

    risk = RiskConfig(0.02, 2.0, 0.30, 10)
    bt = config.backtest
    engine = BacktestEngine(risk, 10000, 0.5, 0.3, config.pip_size)
    engine_eq = BacktestEngine(risk, args.equity, 0.5, 0.3, config.pip_size)

    print("=" * 78)
    print("  1 NĂM TRAIN → 2 NĂM TEST (không overlap, test không nằm trong train)")
    print("  EURUSD 1H + 4H | ${:.0f}".format(args.equity))
    print("=" * 78)
    for label, t0, t1, _ in chunks:
        print(f"  Năm {label}: {t0.date()} → {t1.date()}")
    print()

    results = []
    for yr in (1, 2, 3):
        print(f"--- Train Năm {yr} | Test 2 năm còn lại ---")
        r = run_case(yr, chunks, engine, engine_eq, config, htf, args.trials)
        results.append(r)
        if "error" in r:
            print(f"  {r['error']}\n")
            continue
        t, o = r["train"], r["oos"]
        print(f"  Train: {r['train_period']} | WR={t['win_rate']:.1%} PF={t['profit_factor']:.2f} ({t['trade_count']} lệnh)")
        print(f"  Test : {r['test_years']}")
        print(f"         {r['test_period']}")
        print(f"         WR={o['win_rate']:.1%} PF={o['profit_factor']:.2f} ret={o['total_return']:+.1%} ({o['trade_count']} lệnh)")
        print(f"         ${args.equity:.0f} → ${r['equity_end']:.2f}\n")

    ranked = sorted([r for r in results if "oos" in r], key=lambda x: x["oos"]["total_return"], reverse=True)
    print("=" * 78)
    print("  XẾP HẠNG (2 năm test)")
    print("=" * 78)
    print(f"{'Train':>6} {'Test WR':>8} {'PF':>6} {'Return':>9} {'$End':>9} {'Lệnh':>6}")
    print("-" * 78)
    for r in ranked:
        o = r["oos"]
        print(f"{'Năm '+str(r['train_year']):>6} {o['win_rate']:7.1%} {o['profit_factor']:6.2f} "
              f"{o['total_return']:+8.1%} ${r['equity_end']:8.2f} {o['trade_count']:6d}")
    if ranked:
        w = ranked[0]
        print("=" * 78)
        print(f"  TỐT NHẤT: Train Năm {w['train_year']} → Test {w['test_years']}")
        print(f"  Return: {w['oos']['total_return']:+.1%} (${w['equity_end']:.2f})")
        print("=" * 78)

    Path("output/train_year_reverse_report.json").write_text(
        json.dumps(results, indent=2, default=str)
    )
    print("\nSaved: output/train_year_reverse_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
