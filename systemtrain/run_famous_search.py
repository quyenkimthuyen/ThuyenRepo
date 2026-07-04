#!/usr/bin/env python3
"""Tìm kiếm chiến lược nổi tiếng — backtest cùng pipeline Wyckoff/RSI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.rsi_div_engine import RsiDivEngine
from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.backtest.wyckoff_engine import WyckoffEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.famous import FAMOUS_STRATEGIES, FamousConfig
from systemtrain.strategy.rsi_divergence import RsiDivConfig
from systemtrain.strategy.wyckoff import WyckoffConfig


def _load_yaml(path: Path, key: str) -> dict:
    raw = yaml.safe_load(path.read_text()) or {}
    return raw.get(key, raw)


def _backtest(engine, train_df, oos_df) -> tuple[dict, dict]:
    return engine.run(train_df).metrics or {}, engine.run(oos_df).metrics or {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equity", type=float, default=1000.0)
    args = parser.parse_args()

    config = Config.load()
    df = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
    train_df, oos_df = split_train_oos(df, 1, 2)
    train_df = prepare_dataframe(train_df, "4h")
    oos_df = prepare_dataframe(oos_df, "4h")
    bt = config.backtest
    pip = config.pip_size
    risk = RiskConfig(0.02, 2.0, 0.30, 10)

    results: list[dict] = []

    # Production baselines
    w_raw = _load_yaml(Path("config/wyckoff.yaml"), "wyckoff")
    w_raw.pop("preset", None)
    wcfg = WyckoffConfig.from_dict(w_raw)
    rcfg = RsiDivConfig.from_dict(_load_yaml(Path("config/rsi_divergence.yaml"), "rsi_divergence"))

    baselines = [
        ("Wyckoff", WyckoffEngine(risk, wcfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("RSI Divergence", RsiDivEngine(risk, rcfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
    ]
    for name, engine in baselines:
        tr, oo = _backtest(engine, train_df, oos_df)
        results.append({"name": name, "category": "production", "train": tr, "oos": oo})

    # Famous strategies
    for sid, (detect_fn, fcfg) in FAMOUS_STRATEGIES.items():
        engine = SignalEngine(risk, detect_fn, fcfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)
        tr, oo = _backtest(engine, train_df, oos_df)
        results.append({
            "name": sid.replace("_", " ").title(),
            "id": sid,
            "category": "famous",
            "train": tr,
            "oos": oo,
        })

    results.sort(key=lambda x: x["oos"].get("total_return", -999), reverse=True)

    print("=" * 82)
    print("  CHIẾN LƯỢC NỔI TIẾNG vs PRODUCTION — EURUSD 1H | OOS 2 năm blind")
    print("=" * 82)
    print(f"  {'Chiến lược':<22} {'Cat':<10} {'OOS':>3} {'WR':>6} {'PF':>5} {'RR':>5} {'Return':>7} {'$1000':>8}")
    print("  " + "-" * 78)
    for r in results:
        oo = r["oos"]
        end = args.equity * (1 + oo.get("total_return", 0))
        cat = r.get("category", "")[:10]
        # Chất lượng: WR≥50%, PF≥1.5, ret≥12%, 5-30 lệnh
        quality = (
            oo.get("total_return", 0) >= 0.12
            and oo.get("trade_count", 0) >= 5
            and oo.get("trade_count", 0) <= 30
            and oo.get("win_rate", 0) >= 0.45
            and oo.get("profit_factor", 0) >= 1.5
        )
        marker = " ★" if quality else ""
        print(
            f"  {r['name']:<22} {cat:<10} {oo.get('trade_count', 0):>3} "
            f"{oo.get('win_rate', 0):>5.1%} {oo.get('profit_factor', 0):>5.2f} "
            f"{oo.get('realized_rr', 0):>5.2f} {oo.get('total_return', 0):>+6.1%} ${end:>7.2f}{marker}"
        )

    winners = [r for r in results if r["oos"].get("total_return", 0) >= 0.12 and r["oos"].get("trade_count", 0) >= 5]
    print("\n  ★ = Chất lượng ngang production (WR≥45%, PF≥1.5, 5-30 lệnh, OOS≥+12%)")
    print("=" * 82)

    Path("output/famous_strategies_report.json").write_text(
        json.dumps(results, indent=2, default=str)
    )
    print("Saved: output/famous_strategies_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
