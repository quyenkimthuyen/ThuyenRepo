#!/usr/bin/env python3
"""Backtest RSI divergence H1 — neckline confirmation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.rsi_div_engine import RsiDivEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.rsi_divergence import RsiDivConfig, detect_rsi_divergence_signals

RR_SWEEP = [1.5, 2.0, 2.5, 3.0]


def _print_period(label: str, m: dict, equity: float, target_rr: float, sig_count: int) -> dict:
    end = equity * (1 + m.get("total_return", 0))
    print(f"  {label}")
    print(f"    Tín hiệu : {sig_count} | Lệnh : {m.get('trade_count', 0)}")
    print(f"    WR       : {m.get('win_rate', 0):.1%} | PF : {m.get('profit_factor', 0):.2f}")
    print(f"    RR target: {target_rr:.1f} | RR thực tế: {m.get('realized_rr', 0):.2f}")
    print(f"    Return   : {m.get('total_return', 0):+.1%} | ${equity:.0f} → ${end:.2f}")
    print(f"    Max DD   : {m.get('max_drawdown', 0):.1%}")
    print()
    return m


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
    cfg = RsiDivConfig()

    engine = RsiDivEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), cfg, args.equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
    )

    print("=" * 70)
    print("  RSI DIVERGENCE — EURUSD 1H")
    print("=" * 70)
    print("  Phân kỳ RSI + xác nhận phá neckline (close vượt đỉnh/đáy giữa 2 swing)")
    print(f"  RSI({cfg.rsi_period}) | RR={cfg.rr} | ADX 1H ≤ {cfg.max_adx_1h:.0f}")
    print("=" * 70)

    train_m = _print_period(
        "TRAIN 1 năm", engine.run(train_df).metrics, args.equity, cfg.rr,
        len(detect_rsi_divergence_signals(train_df, cfg)),
    )
    oos_m = _print_period(
        "OOS 2 năm blind", engine.run(oos_df).metrics, args.equity, cfg.rr,
        len(detect_rsi_divergence_signals(oos_df, cfg)),
    )

    print("  ── RR SWEEP (OOS) ──")
    rr_rows = []
    for rr in RR_SWEEP:
        c = RsiDivConfig(**{**cfg.to_dict(), "rr": rr})
        m = RsiDivEngine(
            RiskConfig(0.02, rr, 0.30, 10), c, args.equity,
            bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), config.pip_size,
        ).run(oos_df).metrics
        profit = args.equity * m.get("total_return", 0)
        print(f"    RR {rr:.1f}: {m.get('trade_count', 0)} lệnh WR {m.get('win_rate', 0):.1%} "
              f"PF {m.get('profit_factor', 0):.2f} {m.get('total_return', 0):+.1%} (${profit:+.2f})")
        rr_rows.append({"rr": rr, **m})

    report = {"config": cfg.to_dict(), "train": train_m, "oos": oos_m, "rr_sweep": rr_rows}
    Path("output/rsi_div_report.json").write_text(json.dumps(report, indent=2, default=str))
    Path("config/rsi_divergence.yaml").write_text(
        "rsi_divergence:\n" + "\n".join(f"  {k}: {v}" for k, v in cfg.to_dict().items()) + "\n"
    )
    print("\nSaved: output/rsi_div_report.json, config/rsi_divergence.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
