#!/usr/bin/env python3
"""So sánh RSI divergence H1 vs H4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.rsi_div_engine import RsiDivEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import htf_for_entry, to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.rsi_divergence import RsiDivConfig, detect_rsi_divergence_signals


def _run_tf(tf: str, equity: float, cfg: RsiDivConfig, bt: dict, pip: float) -> dict:
    raw = TrainingPipeline(Config.load()).load_data()
    df = to_entry_timeframe(raw, tf)
    train_df, oos_df = split_train_oos(df, 1, 2)
    htf = htf_for_entry(tf)
    train_df = prepare_dataframe(train_df, htf)
    oos_df = prepare_dataframe(oos_df, htf)

    engine = RsiDivEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), cfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )
    tr = engine.run(train_df).metrics or {}
    oo = engine.run(oos_df).metrics or {}
    return {
        "timeframe": tf,
        "htf_filter": htf,
        "train_bars": len(train_df),
        "oos_bars": len(oos_df),
        "train_signals": len(detect_rsi_divergence_signals(train_df, cfg)),
        "oos_signals": len(detect_rsi_divergence_signals(oos_df, cfg)),
        "train": tr,
        "oos": oo,
    }


def _print_row(label: str, r: dict, equity: float) -> None:
    oo = r["oos"]
    tr = r["train"]
    end = equity * (1 + oo.get("total_return", 0))
    print(
        f"  {label:<6} HTF={r['htf_filter']:<3} | "
        f"Train {tr.get('trade_count', 0):>2}t {tr.get('total_return', 0):+.1%} | "
        f"OOS {oo.get('trade_count', 0):>2}t WR {oo.get('win_rate', 0):.1%} "
        f"PF {oo.get('profit_factor', 0):.2f} {oo.get('total_return', 0):+.1%} → ${end:.2f} | "
        f"sig {r['oos_signals']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equity", type=float, default=1000.0)
    args = parser.parse_args()

    config = Config.load()
    bt = config.backtest
    pip = config.pip_size

    print("=" * 78)
    print("  RSI DIVERGENCE — SO SÁNH H1 vs H4")
    print("=" * 78)

    h1_cfg = RsiDivConfig()
    h4_default = RsiDivConfig()
    h4_tuned = RsiDivConfig(
        min_swing_gap=6,
        max_swing_gap=60,
        max_adx_1h=40.0,
        cooldown_bars=4,
    )
    h4_no_adx = RsiDivConfig(min_swing_gap=6, max_swing_gap=60, max_adx_1h=0, cooldown_bars=4)

    rows = [
        ("H1 opt", _run_tf("1h", args.equity, h1_cfg, bt, pip)),
        ("H4 def", _run_tf("4h", args.equity, h4_default, bt, pip)),
        ("H4 tune", _run_tf("4h", args.equity, h4_tuned, bt, pip)),
        ("H4 noADX", _run_tf("4h", args.equity, h4_no_adx, bt, pip)),
    ]

    for label, r in rows:
        _print_row(label, r, args.equity)

    print("\n  Ghi chú H4: filter HTF = Daily (1D) | tune = gap ngắn hơn + ADX≤40")
    print("=" * 78)

    report = {label: r for label, r in rows}
    Path("output/rsi_div_h4_compare.json").write_text(json.dumps(report, indent=2, default=str))
    print("Saved: output/rsi_div_h4_compare.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
