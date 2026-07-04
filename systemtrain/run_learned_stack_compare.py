#!/usr/bin/env python3
"""So sánh learned strategy: filter 4H strict vs stack."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.learn.features import (
    HTF_LONG_FILTERS,
    HTF_SHORT_FILTERS,
    HTF_STACK_LONG_FILTERS,
    HTF_STACK_SHORT_FILTERS,
)
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.dsl import StrategyGene
from systemtrain.validate.registry import StrategyRegistry

FILTER_MODES = {
    "strict": (HTF_LONG_FILTERS, HTF_SHORT_FILTERS),
    "stack": (HTF_STACK_LONG_FILTERS, HTF_STACK_SHORT_FILTERS),
}


def _apply_htf_mode(gene: StrategyGene, mode: str) -> StrategyGene:
    g = copy.deepcopy(gene)
    if not g.learned_setup:
        return g
    long_f, short_f = FILTER_MODES[mode]
    g.learned_setup["htf_long_filter"] = [list(x) for x in long_f]
    g.learned_setup["htf_short_filter"] = [list(x) for x in short_f]
    return g


def _run_backtest(engine: BacktestEngine, df, gene: StrategyGene) -> dict:
    result = engine.run(df, gene)
    return compute_metrics(result)


def _print_row(label: str, m: dict, equity: float) -> None:
    end = equity * (1 + m.get("total_return", 0))
    profit = end - equity
    print(
        f"  {label:<14} {m.get('trade_count', 0):>4} lệnh | "
        f"WR {m.get('win_rate', 0):>5.1%} | PF {m.get('profit_factor', 0):>4.2f} | "
        f"RR {m.get('realized_rr', 0):>4.2f} | "
        f"{m.get('total_return', 0):>+6.1%} (${profit:>+7.2f}) | "
        f"DD {m.get('max_drawdown', 0):>5.1%}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    config = Config.load()
    df = to_entry_timeframe(TrainingPipeline(config).load_data(), config.timeframe or "1h")
    train_df, oos_df = split_train_oos(
        df, config.data.get("train_years", 1), config.data.get("oos_years", 2)
    )
    htf = getattr(config, "htf_timeframe", "4h")
    train_df = prepare_dataframe(train_df, htf)
    oos_df = prepare_dataframe(oos_df, htf)

    registry = StrategyRegistry(Path("output/strategies.db"))
    strategies = registry.list_strategies()
    if not strategies:
        print("Không có strategy. Chạy: python run_test.py --full")
        return 1

    row = strategies[0]
    base_gene = StrategyGene.from_dict(json.loads(row["gene_json"]))
    bt = config.backtest
    risk = RiskConfig(
        sl_pct=config.risk.get("sl_pct", 0.02),
        min_rr=config.risk.get("min_rr", 2.0),
        max_drawdown=config.risk.get("max_drawdown", 0.30),
        max_consecutive_losses=config.risk.get("max_consecutive_losses", 10),
    )
    engine = BacktestEngine(
        risk_config=risk,
        initial_equity=args.equity,
        spread_pips=bt.get("spread_pips", 0.5),
        slippage_pips=bt.get("slippage_pips", 0.3),
        pip_size=config.pip_size,
    )

    print("=" * 78)
    print("  LEARNED STRATEGY — SO SÁNH FILTER 4H")
    print("=" * 78)
    print(f"  Entry: {config.timeframe} | HTF: {htf} | RR≥{risk.min_rr} | SL {risk.sl_pct:.0%}")
    ls = base_gene.learned_setup or {}
    rules = ls.get("long_rules", []) + ls.get("short_rules", [])
    if rules:
        r0 = rules[0]
        print(f"  Setup: {r0.get('feature')} {r0.get('op')} {r0.get('threshold')} (Monday filter)")
    print()
    print("  strict — long khi 4H close > EMA50, short khi < EMA50")
    print("  stack  — long khi EMA21>EMA50 & close>EMA21, short ngược lại")
    print("=" * 78)

    report = {"equity": args.equity, "modes": {}}
    for mode in ("strict", "stack"):
        gene = _apply_htf_mode(base_gene, mode)
        train_m = _run_backtest(engine, train_df, gene)
        oos_m = _run_backtest(engine, oos_df, gene)
        print(f"\n  [{mode.upper()}]")
        _print_row("Train 1 năm", train_m, args.equity)
        _print_row("OOS 2 năm", oos_m, args.equity)
        report["modes"][mode] = {"train": train_m, "oos": oos_m}

    strict_oos = report["modes"]["strict"]["oos"]
    stack_oos = report["modes"]["stack"]["oos"]
    d_ret = stack_oos["total_return"] - strict_oos["total_return"]
    d_trades = stack_oos["trade_count"] - strict_oos["trade_count"]
    print("\n" + "=" * 78)
    print("  DELTA (stack − strict) trên OOS:")
    print(f"    Return : {d_ret:+.1%}")
    print(f"    Lệnh   : {d_trades:+d}")
    print(f"    WR     : {stack_oos['win_rate'] - strict_oos['win_rate']:+.1%}")
    print(f"    PF     : {stack_oos['profit_factor'] - strict_oos['profit_factor']:+.2f}")
    print("=" * 78)

    if args.save:
        out = Path("output/learned_stack_compare.json")
        out.write_text(json.dumps(report, indent=2, default=str))
        print(f"\nSaved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
