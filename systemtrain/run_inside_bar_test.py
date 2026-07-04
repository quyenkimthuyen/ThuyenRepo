#!/usr/bin/env python3
"""Backtest Inside Bar vs Wyckoff / RSI / Pin Bar Elite — cùng pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import fields
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
from systemtrain.strategy.famous import FAMOUS_STRATEGIES, FamousConfig, detect_inside_bar, detect_pin_bar
from systemtrain.strategy.rsi_divergence import RsiDivConfig
from systemtrain.strategy.wyckoff import WyckoffConfig

QUALITY_BAR = dict(min_wr=0.45, min_pf=1.5, min_trades=5, max_trades=30, min_return=0.12)


def _quality(m: dict) -> bool:
    return (
        m.get("total_return", 0) >= QUALITY_BAR["min_return"]
        and QUALITY_BAR["min_trades"] <= m.get("trade_count", 0) <= QUALITY_BAR["max_trades"]
        and m.get("win_rate", 0) >= QUALITY_BAR["min_wr"]
        and m.get("profit_factor", 0) >= QUALITY_BAR["min_pf"]
    )


def _row(name: str, period: str, m: dict) -> str:
    q = " ★" if _quality(m) else ""
    return (
        f"  {name:<18} {period:<6} {m.get('trade_count', 0):>3} lệnh | "
        f"WR {m.get('win_rate', 0):>5.1%} | PF {m.get('profit_factor', 0):>5.2f} | "
        f"RR {m.get('realized_rr', 0):>4.2f} | {m.get('total_return', 0):>+6.1%}{q}"
    )


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

    w_raw = yaml.safe_load(Path("config/wyckoff.yaml").read_text())["wyckoff"]
    w_raw.pop("preset", None)
    wcfg = WyckoffConfig.from_dict(w_raw)
    rcfg = RsiDivConfig.from_dict(
        yaml.safe_load(Path("config/rsi_divergence.yaml").read_text())["rsi_divergence"]
    )
    _, pcfg = FAMOUS_STRATEGIES["pin_bar"]
    pin_cfg = FamousConfig(**{f.name: getattr(pcfg, f.name) for f in fields(FamousConfig)})

    ib_cfg = FamousConfig(
        name="inside_bar", rr=2.0, htf_mode="strict", use_htf_filter=True,
        min_htf_adx=24.0, session_start=9, session_end=16, max_adx_1h=30.0,
        max_inside_range_ratio=0.60, min_mother_range_atr=0.40, breakout_lookforward=6,
    )

    strategies = [
        ("Wyckoff", WyckoffEngine(risk, wcfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("RSI Divergence", RsiDivEngine(risk, rcfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("Pin Bar Elite", SignalEngine(risk, detect_pin_bar, pin_cfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("Inside Bar", SignalEngine(risk, detect_inside_bar, ib_cfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
    ]

    print("=" * 78)
    print("  INSIDE BAR vs CHIẾN LƯỢC HIỆN TẠI | EURUSD 1H | RR=2.0")
    print("  Inside Bar: mother-bar breakout + 4H strict + ADX filter")
    print("=" * 78)

    report: dict = {"inside_bar_config": ib_cfg.to_dict(), "strategies": {}}
    for name, engine in strategies:
        tr = engine.run(train_df).metrics or {}
        oo = engine.run(oos_df).metrics or {}
        print(_row(name, "Train", tr))
        print(_row(name, "OOS", oo))
        report["strategies"][name] = {"train": tr, "oos": oo}

    ib_oos = report["strategies"]["Inside Bar"]["oos"]
    print("\n  " + "-" * 74)
    print("  KẾT LUẬN:")
    if _quality(ib_oos):
        print("    Inside Bar ĐẠT bar chất lượng production.")
    else:
        print("    Inside Bar KHÔNG tương đương production / Pin Bar Elite trên OOS.")
        print(f"    Best IB OOS: {ib_oos.get('trade_count',0)} lệnh WR {ib_oos.get('win_rate',0):.1%} "
              f"PF {ib_oos.get('profit_factor',0):.2f} {ib_oos.get('total_return',0):+.1%}")
        print("    Bar production: WR≥45%, PF≥1.5, 5–30 lệnh, OOS≥+12%")
    print("  ★ = đạt bar chất lượng")
    print("=" * 78)

    Path("output/inside_bar_report.json").write_text(json.dumps(report, indent=2, default=str))
    print("Saved: output/inside_bar_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
