#!/usr/bin/env python3
"""Backtest Supply/Demand vs chiến lược hiện tại — EURUSD 1H."""

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
from systemtrain.strategy.supply_demand import SupplyDemandConfig, detect_supply_demand
from systemtrain.strategy.wyckoff import WyckoffConfig

QUALITY = dict(min_wr=0.45, min_pf=1.5, min_trades=5, max_trades=30, min_return=0.12)


def _star(m: dict) -> str:
    ok = (
        m.get("total_return", 0) >= QUALITY["min_return"]
        and QUALITY["min_trades"] <= m.get("trade_count", 0) <= QUALITY["max_trades"]
        and m.get("win_rate", 0) >= QUALITY["min_wr"]
        and m.get("profit_factor", 0) >= QUALITY["min_pf"]
    )
    return " ★" if ok else ""


def _balanced_sd_cfg() -> SupplyDemandConfig:
    """Best S/D sau grid — cân bằng số lệnh / chất lượng."""
    return SupplyDemandConfig(
        min_impulse_atr=0.85,
        max_base_range_atr=1.0,
        require_rejection=True,
        min_wick_body_ratio=2.0,
        htf_mode="strict",
        min_htf_adx=20.0,
        session_start=9,
        session_end=16,
        max_retest_bars=56,
        max_adx_1h=35.0,
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
    _, ib_cfg = FAMOUS_STRATEGIES["inside_bar"]
    _, pin_cfg = FAMOUS_STRATEGIES["pin_bar"]
    pin_cfg = FamousConfig(**{f.name: getattr(pin_cfg, f.name) for f in fields(FamousConfig)})
    sd_cfg = _balanced_sd_cfg()

    engines = [
        ("Wyckoff", WyckoffEngine(risk, wcfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("RSI Divergence", RsiDivEngine(risk, rcfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("Pin Bar Elite", SignalEngine(risk, detect_pin_bar, pin_cfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("Inside Bar H1", SignalEngine(risk, detect_inside_bar, ib_cfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
        ("Supply/Demand", SignalEngine(risk, detect_supply_demand, sd_cfg, args.equity, bt["spread_pips"], bt["slippage_pips"], pip)),
    ]

    print("=" * 82)
    print("  SUPPLY / DEMAND vs CHIẾN LƯỢC HIỆN TẠI | EURUSD 1H | RR=2.0")
    print("  S/D: base + impulse → retest vùng + rejection | filter 4H strict")
    print("=" * 82)
    print(f"  {'Chiến lược':<18} {'':^6} {'Lệnh':>4} {'WR':>6} {'PF':>5} {'RR':>5} {'Return':>7}")
    print("  " + "-" * 78)

    report: dict = {"supply_demand_config": sd_cfg.to_dict(), "strategies": {}}
    for name, engine in engines:
        tr = engine.run(train_df).metrics or {}
        oo = engine.run(oos_df).metrics or {}
        report["strategies"][name] = {"train": tr, "oos": oo}
        for period, m in [("Train", tr), ("OOS", oo)]:
            print(
                f"  {name:<18} {period:<6} {m.get('trade_count', 0):4} "
                f"{m.get('win_rate', 0):6.1%} {m.get('profit_factor', 0):5.2f} "
                f"{m.get('realized_rr', 0):5.2f} {m.get('total_return', 0):+6.1%}"
                f"{_star(m) if period == 'OOS' else ''}"
            )

    sd = report["strategies"]["Supply/Demand"]["oos"]
    print("\n  " + "-" * 78)
    print("  KẾT LUẬN:")
    if _star(sd):
        print("    Supply/Demand đạt bar chất lượng — có thể theo dõi thêm.")
    else:
        print("    Supply/Demand CHƯA hiệu quả tương đương production trên OOS.")
        print(f"    Best S/D: {sd.get('trade_count',0)} lệnh WR {sd.get('win_rate',0):.1%} "
              f"PF {sd.get('profit_factor',0):.2f} {sd.get('total_return',0):+.1%}")
        print("    Quá ít lệnh với filter chặt; quá nhiều lệnh + WR thấp khi nới lỏng.")
    print("  ★ = WR≥45%, PF≥1.5, 5–30 lệnh, OOS≥+12%")
    print("=" * 82)

    Path("output/supply_demand_report.json").write_text(json.dumps(report, indent=2, default=str))
    print("Saved: output/supply_demand_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
