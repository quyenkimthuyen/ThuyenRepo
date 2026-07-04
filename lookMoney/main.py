#!/usr/bin/env python3
"""lookMoney CLI — EUR/USD H1 backtest (London + New York)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from lookmoney.backtest.engine import run_backtest
from lookmoney.backtest.split import TemporalSplit
from lookmoney.data.fetcher import fetch_eurusd_h1, load_csv, resample_ohlcv, save_csv
from lookmoney.live.runner import PaperRunner


def load_config(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def _load_bars(args: argparse.Namespace, config: dict | None = None):
    cache = Path(args.cache)
    tf = (config or {}).get("timeframe", "H1").upper()

    if args.csv:
        df = load_csv(args.csv)
        print(f"Loaded {len(df)} bars from {args.csv}")
    elif cache.exists() and not args.refresh:
        df = load_csv(cache)
        print(f"Loaded {len(df)} bars from cache ({cache})")
    else:
        period = args.period
        print(f"Fetching EUR/USD H1 from Yahoo Finance (period={period})...")
        df = fetch_eurusd_h1(period=period)
        save_csv(df, cache)
        print(f"Saved {len(df)} bars to {cache}")

    if tf == "H4":
        df = resample_ohlcv(df, "4h")
        print(f"Resampled to H4: {len(df)} bars")

    if args.start:
        df = df[df.index >= args.start]
    if args.end:
        df = df[df.index <= args.end]
    return df


def _run_phase(
    label: str,
    df,
    config: dict,
    *,
    trade_start=None,
    trade_end=None,
    causal: bool = False,
    output: Path | None = None,
) -> tuple:
    print(f"\n{'=' * 60}")
    print(f"=== {label} ===")
    if trade_start is not None and trade_end is not None:
        print(f"Trade window: {trade_start} → {trade_end}")
    if causal:
        print("Signal mode: causal (indicators use past bars only; OOS window truncated)")
    print(f"Bars in simulation: {len(df)} ({df.index.min()} → {df.index.max()})\n")

    trades, equity, metrics = run_backtest(
        df,
        config,
        trade_start=trade_start,
        trade_end=trade_end,
        causal=causal,
    )
    print(metrics.summary())

    if output:
        output.mkdir(parents=True, exist_ok=True)
        trades.to_csv(output / "trades.csv")
        equity.to_csv(output / "equity.csv")
        print(f"\nWrote {output / 'trades.csv'} and {output / 'equity.csv'}")

    return trades, equity, metrics


def cmd_backtest(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    df = _load_bars(args, config)

    print(f"Dataset: {df.index.min()} → {df.index.max()} ({len(df)} bars)")
    print(f"Timeframe: {config.get('timeframe', 'H1')} | Sessions: London 07-16 UTC, New York 13-21 UTC")

    if args.phase == "full":
        _run_phase("Full backtest", df, config, output=Path(args.output) if args.output else None)
        return 0

    split = TemporalSplit.from_config(df, config).clip_to_data(df)
    print(f"\n{split.summary()}")

    if args.phase == "develop":
        develop_df = split.develop_df(df)
        _run_phase(
            "Develop (year 1 — build & tune strategy)",
            develop_df,
            config,
            trade_start=split.develop_start,
            trade_end=min(split.develop_end, df.index[-1]),
            output=Path(args.output) if args.output else None,
        )
        return 0

    if args.phase == "oos":
        oos_df = split.oos_df(df, include_warmup=True)
        _run_phase(
            "OOS (years 2–3 — blind test, frozen params)",
            oos_df,
            config,
            trade_start=split.develop_end,
            trade_end=split.oos_end,
            causal=True,
            output=Path(args.output) if args.output else None,
        )
        return 0

    return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Run develop then OOS with the 1y + 2y split."""
    config = load_config(Path(args.config))
    df = _load_bars(args, config)

    split = TemporalSplit.from_config(df, config).clip_to_data(df)
    print("Fair validation protocol")
    print(split.summary())
    print("\nRule: tune strategy only on Develop; OOS uses frozen config + causal signals.")

    out_root = Path(args.output) if args.output else None

    _run_phase(
        "Develop (year 1 — build & tune strategy)",
        split.develop_df(df),
        config,
        trade_start=split.develop_start,
        trade_end=min(split.develop_end, df.index[-1]),
        output=out_root / "develop" if out_root else None,
    )
    _run_phase(
        "OOS (years 2–3 — blind test, frozen params)",
        split.oos_df(df, include_warmup=True),
        config,
        trade_start=split.develop_end,
        trade_end=split.oos_end,
        causal=True,
        output=out_root / "oos" if out_root else None,
    )

    print(f"\n{'=' * 60}")
    print("Done. Compare OOS metrics to Develop — OOS is the honest score.")
    return 0


def cmd_paper(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    source = "csv" if args.csv else "mt5"
    runner = PaperRunner(config, data_source=source)

    if args.reset:
        path = Path(config.get("paper", {}).get("state_path", "data/paper_state.json"))
        if path.exists():
            path.unlink()
            print(f"Reset paper state: {path}")
        else:
            print("No paper state to reset.")
        if not args.run:
            return 0
        runner = PaperRunner(config, data_source=source)

    if args.status:
        s = runner.status()
        print("=== Paper trade status ===")
        for k, v in s.items():
            print(f"  {k}: {v}")
        return 0

    result = runner.run_once(csv_fallback=args.csv, force=args.force)
    print("=== Paper trade run ===")
    for k, v in result.items():
        if k == "actions" and v:
            print("  actions:")
            for a in v:
                print(f"    - {a}")
        else:
            print(f"  {k}: {v}")
    return 0 if result.get("status") in ("ok", "skipped") else 1


def cmd_paper_loop(args: argparse.Namespace) -> int:
    import time

    config = load_config(Path(args.config))
    source = "csv" if args.csv else "mt5"
    runner = PaperRunner(config, data_source=source)
    print(f"Paper loop every {args.interval}s (Ctrl+C to stop). MT5 demo + local fills.")
    try:
        while True:
            result = runner.run_once(csv_fallback=args.csv, force=args.force)
            print(f"[{result.get('status')}] balance={result.get('balance', runner.session.balance)}")
            if result.get("actions"):
                for a in result["actions"]:
                    print(f"  {a}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="lookMoney EUR/USD H1 backtester")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Run historical backtest")
    bt.add_argument("--config", default="config/eur_usd.yaml")
    bt.add_argument("--cache", default="data/eurusd_h1.csv")
    bt.add_argument("--csv", help="Use local CSV instead of download")
    bt.add_argument("--period", default="1095d", help="Yahoo Finance lookback (3y for validate split)")
    bt.add_argument("--refresh", action="store_true", help="Re-download data")
    bt.add_argument("--start", help="Filter start (ISO date)")
    bt.add_argument("--end", help="Filter end (ISO date)")
    bt.add_argument(
        "--phase",
        choices=["full", "develop", "oos"],
        default="full",
        help="full=all data; develop=year 1 tune; oos=years 2-3 blind causal test",
    )
    bt.add_argument("--output", "-o", help="Output directory for trades/equity CSV")
    bt.set_defaults(func=cmd_backtest)

    val = sub.add_parser(
        "validate",
        help="Fair split: 1y develop + 2y OOS (causal, frozen params)",
    )
    val.add_argument("--config", default="config/eur_usd.yaml")
    val.add_argument("--cache", default="data/eurusd_h1.csv")
    val.add_argument("--csv", help="Use local CSV instead of download")
    val.add_argument("--period", default="1095d", help="Yahoo Finance lookback")
    val.add_argument("--refresh", action="store_true", help="Re-download data")
    val.add_argument("--start", help="Filter start (ISO date)")
    val.add_argument("--end", help="Filter end (ISO date)")
    val.add_argument("--output", "-o", default="results/validate", help="Output root directory")
    val.set_defaults(func=cmd_validate)

    paper = sub.add_parser("paper", help="Paper trade: MT5 H1 data + simulated P&L")
    paper.add_argument("--config", default="config/eur_usd.yaml")
    paper.add_argument("--csv", help="Use CSV instead of MT5 (dev/test)")
    paper.add_argument("--run", action="store_true", help="With --reset, run once after reset")
    paper.add_argument("--status", action="store_true", help="Show paper state only")
    paper.add_argument("--reset", action="store_true", help="Delete paper state (fresh start)")
    paper.add_argument("--force", action="store_true", help="Run even before min_minute_after_hour")
    paper.set_defaults(func=cmd_paper)

    loop = sub.add_parser("paper-loop", help="Paper trade loop (poll every hour)")
    loop.add_argument("--config", default="config/eur_usd.yaml")
    loop.add_argument("--csv", help="Use CSV instead of MT5")
    loop.add_argument("--interval", type=int, default=3600, help="Seconds between polls")
    loop.add_argument("--force", action="store_true")
    loop.set_defaults(func=cmd_paper_loop)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
