#!/usr/bin/env python3
"""CLI for EURUSD 15m strategy training system."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from systemtrain.config import Config
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.reporting import print_strategy_report, summary_dict
from systemtrain.validate.registry import StrategyRegistry


def cmd_download(args: argparse.Namespace) -> int:
    from pathlib import Path
    from systemtrain.data.ingest import download_eurusd_15m_dukascopy, save_csv, save_parquet
    from systemtrain.data.quality import check_quality

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    def progress(start, end, done, total):
        print(f"  [{done}/{total}] {start.date()} -> {end.date()} ...", flush=True)

    print(f"Downloading EURUSD 15m — last {args.years} years from Dukascopy (UTC)...")
    df = download_eurusd_15m_dukascopy(years=args.years, on_progress=progress)
    parquet_path = save_parquet(df, out_dir / "eurusd_15m.parquet")
    csv_path = save_csv(df, out_dir / "eurusd_15m.csv")
    quality = check_quality(df)
    print(f"\nDone. Bars={len(df):,} | {df.index.min()} -> {df.index.max()}")
    print(f"  Parquet: {parquet_path}")
    print(f"  CSV: {csv_path}")
    print(f"  Quality: {'OK' if quality['ok'] else quality['issues']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = Config.load(args.config) if args.config else Config.load()
    pipeline = TrainingPipeline(config)
    result = pipeline.run(
        csv_path=args.csv,
        force_regenerate=args.regenerate_data,
        quick=args.quick,
    )
    passed = [s for s in result.validated_strategies if s.get("passed")]
    print(f"\n=== Pipeline Complete ===")
    print(f"Symbol: {config.symbol} | Timeframe: {config.timeframe}")
    print(f"Train bars: {len(result.train_df)} | OOS bars: {len(result.oos_df)}")
    print(f"Candidates evaluated: {len(result.validated_strategies)}")
    print(f"Strategies PASSED OOS gate: {len(passed)}")
    print(f"Report: {result.output_dir / 'run_report.json'}")
    print(f"Registry DB: {result.output_dir / 'strategies.db'}")
    if passed:
        print("\n--- Passed Strategies ---")
        for s in passed:
            oos = s["oos_metrics"]
            print(
                f"  ID={s['id'][:8]}... "
                f"WR={oos['win_rate']:.1%} PF={oos['profit_factor']:.2f} "
                f"DD={oos['max_drawdown']:.1%} trades={oos['trade_count']}"
            )
    print_strategy_report(result.validated_strategies, title="Detailed Report")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    from run_test import run_test
    return run_test(quick=not args.full, csv_path=args.csv, regenerate=args.regenerate_data)


def cmd_list(args: argparse.Namespace) -> int:
    db = Path(args.output_dir) / "strategies.db"
    if not db.exists():
        print(f"No registry found at {db}")
        return 1
    registry = StrategyRegistry(db)
    rows = registry.list_strategies(passed_only=args.passed_only)
    print(json.dumps(rows, indent=2, default=str))
    return 0


def cmd_backtest_oos(args: argparse.Namespace) -> int:
    """Re-run blind OOS for a saved strategy (verification only)."""
    from systemtrain.backtest.engine import BacktestEngine
    from systemtrain.backtest.metrics import compute_metrics
    from systemtrain.backtest.risk import RiskConfig
    from systemtrain.data.ingest import ensure_data
    from systemtrain.data.split import split_train_oos
    from systemtrain.strategy.dsl import StrategyGene

    config = Config.load(args.config) if args.config else Config.load()
    db = Path(args.output_dir) / "strategies.db"
    registry = StrategyRegistry(db)
    rows = registry.list_strategies()
    row = next((r for r in rows if r["id"].startswith(args.strategy_id)), None)
    if not row:
        print(f"Strategy not found: {args.strategy_id}")
        return 1

    gene = StrategyGene.from_dict(json.loads(row["gene_json"]))
    df = ensure_data(config.data.get("data_dir", "data/store"))
    _, oos_df = split_train_oos(df, config.data.get("train_years", 1), config.data.get("oos_years", 2))
    from systemtrain.data.prepared import prepare_dataframe
    oos_df = prepare_dataframe(oos_df)

    risk = RiskConfig(
        sl_pct=config.risk.get("sl_pct", 0.02),
        min_rr=config.risk.get("min_rr", 2.0),
        max_drawdown=config.risk.get("max_drawdown", 0.25),
        max_consecutive_losses=config.risk.get("max_consecutive_losses", 8),
        max_concurrent_positions=config.risk.get("max_concurrent_positions", 1),
    )
    engine = BacktestEngine(
        risk_config=risk,
        initial_equity=config.backtest.get("initial_equity", 10000),
        spread_pips=config.backtest.get("spread_pips", 1.5),
        slippage_pips=config.backtest.get("slippage_pips", 0.5),
        pip_size=config.pip_size,
    )
    result = engine.run(oos_df, gene)
    metrics = compute_metrics(result)
    print(json.dumps(metrics, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="EURUSD 15m Strategy Training System")
    sub = parser.add_subparsers(dest="command", required=True)

    dl_p = sub.add_parser("download", help="Download EURUSD 15m from Dukascopy")
    dl_p.add_argument("--years", type=int, default=3)
    dl_p.add_argument("--output-dir", default="data/store")
    dl_p.set_defaults(func=cmd_download)

    run_p = sub.add_parser("run", help="Run full training + OOS validation pipeline")
    run_p.add_argument("--config", type=str, default=None)
    run_p.add_argument("--csv", type=str, default=None, help="Path to EURUSD 15m CSV")
    run_p.add_argument("--regenerate-data", action="store_true")
    run_p.add_argument("--quick", action="store_true", help="Smaller GA for testing")
    run_p.set_defaults(func=cmd_run)

    test_p = sub.add_parser("test", help="Run pipeline test with detailed strategy report")
    test_p.add_argument("--full", action="store_true")
    test_p.add_argument("--csv", type=str, default=None)
    test_p.add_argument("--regenerate-data", action="store_true")
    test_p.set_defaults(func=cmd_test)

    list_p = sub.add_parser("list", help="List strategies in registry")
    list_p.add_argument("--output-dir", default="output")
    list_p.add_argument("--passed-only", action="store_true")
    list_p.set_defaults(func=cmd_list)

    bt_p = sub.add_parser("backtest-oos", help="Re-run OOS backtest for saved strategy")
    bt_p.add_argument("strategy_id", help="Strategy ID prefix")
    bt_p.add_argument("--config", default=None)
    bt_p.add_argument("--output-dir", default="output")
    bt_p.set_defaults(func=cmd_backtest_oos)

    wy_p = sub.add_parser("wyckoff", help="Backtest Wyckoff failed break (1H, RR=3)")
    wy_p.add_argument("--equity", type=float, default=1000.0)
    wy_p.add_argument("--rr", type=float, default=3.0)
    wy_p.add_argument("--days", type=int, default=3)
    wy_p.set_defaults(func=lambda a: __import__("subprocess").call(
        [sys.executable, "run_wyckoff_test.py", "--equity", str(a.equity), "--rr", str(a.rr), "--days", str(a.days)]
    ))

    rsi_p = sub.add_parser("rsi-div", help="Backtest RSI divergence (1H)")
    rsi_p.add_argument("--equity", type=float, default=1000.0)
    rsi_p.set_defaults(func=lambda a: __import__("subprocess").call(
        [sys.executable, "run_rsi_div_test.py", "--equity", str(a.equity)]
    ))

    prod_p = sub.add_parser("production", help="Backtest Wyckoff + RSI Divergence")
    prod_p.add_argument("--equity", type=float, default=1000.0)
    prod_p.set_defaults(func=lambda a: __import__("subprocess").call(
        [sys.executable, "run_production.py", "--equity", str(a.equity)]
    ))

    app_p = sub.add_parser("app", help="Launch Streamlit dashboard")
    app_p.set_defaults(func=lambda a: __import__("subprocess").call(
        [sys.executable, "-m", "streamlit", "run", "run_app.py", "--server.headless", "true"]
    ))

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
