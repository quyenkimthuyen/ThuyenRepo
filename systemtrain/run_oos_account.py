#!/usr/bin/env python3
"""Re-run saved strategies on blind OOS period with custom account size."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics, trades_to_dataframe
from systemtrain.backtest.risk import RiskConfig
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.dsl import StrategyGene
from systemtrain.validate.registry import StrategyRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description="OOS backtest with custom account")
    parser.add_argument("--equity", type=float, default=1000.0, help="Starting balance USD")
    parser.add_argument("--save", action="store_true", help="Save report JSON")
    args = parser.parse_args()

    config = Config.load()
    pipeline = TrainingPipeline(config)
    df = pipeline.load_data()
    _, oos_df = split_train_oos(
        df, config.data.get("train_years", 1), config.data.get("oos_years", 2)
    )
    htf = getattr(config, "htf_timeframe", "4h")
    oos_df = prepare_dataframe(oos_df, htf_rule=htf)

    risk = RiskConfig(
        sl_pct=config.risk.get("sl_pct", 0.02),
        min_rr=config.risk.get("min_rr", 2.0),
        max_drawdown=config.risk.get("max_drawdown", 0.30),
        max_consecutive_losses=config.risk.get("max_consecutive_losses", 10),
        max_concurrent_positions=config.risk.get("max_concurrent_positions", 1),
    )
    bt = config.backtest
    engine = BacktestEngine(
        risk_config=risk,
        initial_equity=args.equity,
        spread_pips=bt.get("spread_pips", 0.5),
        slippage_pips=bt.get("slippage_pips", 0.3),
        pip_size=config.pip_size,
    )

    registry = StrategyRegistry(Path("output/strategies.db"))
    strategies = registry.list_strategies()
    if not strategies:
        print("Không có strategy trong registry. Chạy: python run_test.py --full")
        return 1

    print("=" * 70)
    print(f"  BÁO CÁO OOS 2 NĂM — TÀI KHOẢN ${args.equity:,.0f}")
    print("=" * 70)
    print(f"  Cặp      : {config.symbol}")
    print(f"  Entry    : {config.timeframe} | Filter: {htf}")
    print(f"  Spread   : {bt.get('spread_pips', 0.5)} pip ECN")
    print(f"  Risk     : SL {config.risk.get('sl_pct', 0.02):.0%}/lệnh | RR≥{config.risk.get('min_rr', 2)}")
    print(f"  OOS      : {oos_df.index.min().date()} → {oos_df.index.max().date()}")
    print(f"  Bars     : {len(oos_df):,}")
    print(f"  Strategies: {len(strategies)}")
    print("=" * 70)

    reports = []
    for row in strategies:
        rank = row.get("rank_order", 0)
        gene = StrategyGene.from_dict(json.loads(row["gene_json"]))
        result = engine.run(oos_df, gene)
        m = compute_metrics(result)
        start = args.equity
        end = start * (1 + m["total_return"])
        profit = end - start
        max_dd_usd = m["max_drawdown"] * start

        print(f"\n[Strategy #{rank}]")
        print(f"  Lệnh          : {m['trade_count']}")
        print(f"  Win rate      : {m['win_rate']:.1%}")
        print(f"  Profit factor : {m['profit_factor']:.2f}")
        print(f"  RR thực tế    : {m['realized_rr']:.2f}")
        print(f"  ---")
        print(f"  Vốn ban đầu   : ${start:,.2f}")
        print(f"  Vốn cuối      : ${end:,.2f}")
        print(f"  Lãi/lỗ        : ${profit:+,.2f} ({m['total_return']:+.1%})")
        print(f"  Max drawdown  : ${max_dd_usd:,.2f} ({m['max_drawdown']:.1%})")
        print(f"  TB thắng/lệnh : ${m['avg_win']:,.2f}")
        print(f"  TB thua/lệnh  : ${m['avg_loss']:,.2f}")
        print(f"  Expectancy    : ${m['expectancy']:,.2f}/lệnh")
        if m.get("halted"):
            print(f"  ⚠ Dừng sớm    : {m.get('halt_reason', '')}")

        reports.append({
            "rank": rank,
            "account_start": start,
            "account_end": round(end, 2),
            "profit_usd": round(profit, 2),
            "metrics": m,
            "oos_period": {
                "start": str(oos_df.index.min()),
                "end": str(oos_df.index.max()),
            },
        })

    print("\n" + "=" * 70)
    if len(reports) == 1:
        r = reports[0]
        print(f"  TÓM TẮT: ${r['account_start']:,.0f} → ${r['account_end']:,.2f} "
              f"({r['profit_usd']:+,.2f}) trong 2 năm OOS")
    print("=" * 70 + "\n")

    if args.save:
        out = Path("output/oos_account_report.json")
        with out.open("w") as f:
            json.dump({"equity": args.equity, "strategies": reports}, f, indent=2, default=str)
        print(f"Saved: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
