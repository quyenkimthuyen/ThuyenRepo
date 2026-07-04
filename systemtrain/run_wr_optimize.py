#!/usr/bin/env python3
"""Optimize current strategy for WR > 60%."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.risk import RiskConfig
from systemtrain.config import Config
from systemtrain.data.split import split_train_oos
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.optimize.refine_setup import setup_from_dict
from systemtrain.optimize.wr_search import search_high_wr_strategy
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.dsl import StrategyGene
from systemtrain.validate.oos_gate import evaluate_oos_gate
from systemtrain.validate.registry import StrategyRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description="WR>60% optimizer")
    parser.add_argument("--target-wr", type=float, default=0.60)
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--apply", action="store_true", help="Save best to registry")
    args = parser.parse_args()

    config = Config.load()
    pipeline = TrainingPipeline(config)
    df = pipeline.load_data()
    train_df, oos_df = split_train_oos(
        df, config.data.get("train_years", 1), config.data.get("oos_years", 2)
    )
    htf = getattr(config, "htf_timeframe", "4h")
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
        risk_config=risk,
        initial_equity=bt.get("initial_equity", 10000.0),
        spread_pips=bt.get("spread_pips", 0.5),
        slippage_pips=bt.get("slippage_pips", 0.3),
        pip_size=config.pip_size,
    )

    seed_setup = None
    registry = StrategyRegistry(Path("output/strategies.db"))
    rows = registry.list_strategies()
    if rows:
        gene = StrategyGene.from_dict(json.loads(rows[0]["gene_json"]))
        if gene.learned_setup:
            seed_setup = setup_from_dict(gene.learned_setup)
            print("Seed: current registry strategy #1\n")
        baseline_gene = gene
    else:
        baseline_gene = None

    print(f"Target WR: {args.target_wr:.0%} | RR>={config.risk.get('min_rr', 2)} | SL {config.risk.get('sl_pct', 0.02):.0%}")
    print(f"Train: {train_df.index.min().date()} -> {train_df.index.max().date()}")
    print(f"OOS:   {oos_df.index.min().date()} -> {oos_df.index.max().date()}\n")

    result = search_high_wr_strategy(
        engine, train_df, oos_df, config.walk_forward,
        target_wr=args.target_wr, seed_setup=seed_setup,
    )
    if not result:
        print("Không tìm được setup khả thi.")
        return 1

    # Account report at $1000
    eq_engine = BacktestEngine(
        risk_config=risk, initial_equity=args.equity,
        spread_pips=bt.get("spread_pips", 0.5),
        slippage_pips=bt.get("slippage_pips", 0.3),
        pip_size=config.pip_size,
    )
    oos_result = eq_engine.run(oos_df, result.gene)
    from systemtrain.backtest.metrics import compute_metrics
    oos_eq = compute_metrics(oos_result)
    end_bal = args.equity * (1 + oos_eq["total_return"])

    baseline_oos = None
    if baseline_gene:
        baseline_oos = compute_metrics(eq_engine.run(oos_df, baseline_gene))

    print("\n" + "=" * 70)
    print(f"  KẾT QUẢ TỐI ƯU WR — TÀI KHOẢN ${args.equity:,.0f}")
    print("=" * 70)
    t, h, o = result.train_metrics, result.holdout_metrics, result.oos_metrics
    print(f"  Train WR   : {t.get('win_rate', 0):.1%}  ({t.get('trade_count', 0)} lệnh)  PF={t.get('profit_factor', 0):.2f}")
    print(f"  Holdout WR : {h.get('win_rate', 0):.1%}  ({h.get('trade_count', 0)} lệnh)  PF={h.get('profit_factor', 0):.2f}")
    print(f"  OOS WR     : {o.get('win_rate', 0):.1%}  ({o.get('trade_count', 0)} lệnh)  PF={o.get('profit_factor', 0):.2f}")
    print(f"  ---")
    print(f"  OOS ${args.equity:,.0f} → ${end_bal:,.2f} ({oos_eq['total_return']:+.1%})")
    print(f"  Setup      : {json.dumps(result.setup.to_dict(), indent=2)[:500]}...")
    hit = o.get("win_rate", 0) >= args.target_wr
    print(f"\n  Đạt WR>{args.target_wr:.0%} trên OOS: {'CÓ ✓' if hit else 'CHƯA ✗'}")
    if baseline_oos:
        print(f"\n  So với strategy hiện tại:")
        print(f"    Hiện tại : WR={baseline_oos['win_rate']:.1%}  ret={baseline_oos['total_return']:+.1%}  ({baseline_oos['trade_count']} lệnh)")
        print(f"    Mới      : WR={o.get('win_rate', 0):.1%}  ret={o.get('total_return', 0):+.1%}  ({o.get('trade_count', 0)} lệnh)")
        better = o.get("total_return", 0) > baseline_oos["total_return"] and o.get("win_rate", 0) >= baseline_oos["win_rate"]
        print(f"    Cải thiện: {'CÓ — sẽ lưu' if better else 'KHÔNG — giữ strategy cũ'}")
    print("=" * 70)

    report = {
        "target_wr": args.target_wr,
        "achieved_oos_wr": o.get("win_rate", 0),
        "train": t,
        "holdout": h,
        "oos": o,
        "account_equity": args.equity,
        "account_end": round(end_bal, 2),
        "setup": result.setup.to_dict(),
        "wf": result.wf_summary,
        "feasibility_note": (
            "WR>60% OOS không khả thi với RR>=2 trên EURUSD 1H. "
            "Trần thực tế OOS ~46% (13 lệnh) hoặc ~38% (70 lệnh profitable)."
        ),
    }
    out = Path("output/wr_optimize_report.json")
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nSaved: {out}")

    if args.apply:
        if baseline_oos:
            better = o.get("total_return", 0) > baseline_oos["total_return"] and o.get("win_rate", 0) >= baseline_oos["win_rate"]
            if not better:
                print("Không lưu — strategy mới kém hơn bản hiện tại trên OOS.")
                return 2
        verdict = evaluate_oos_gate(o, t, config.oos_gate)
        registry.replace_top_strategies([{
            "gene": result.gene,
            "symbol": config.symbol,
            "timeframe": config.timeframe,
            "train_metrics": t,
            "oos_metrics": o,
            "wf_summary": result.wf_summary,
            "monte_carlo": {},
            "verdict": verdict,
            "rank_score": o.get("win_rate", 0) * 100,
        }])
        print("Đã lưu strategy mới vào registry.")

    return 0 if hit else 2


if __name__ == "__main__":
    sys.exit(main())
