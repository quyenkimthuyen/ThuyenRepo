#!/usr/bin/env python3
"""Phân tích lệnh thua RSI divergence → tối ưu filter."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from systemtrain.analyze.rsi_div_losses import classify_loss, detect_rsi_signals_with_meta
from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.rsi_div_engine import RsiDivEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.rsi_divergence import RsiDivConfig

REASON_VI = {
    "counter_4h_trend": "Ngược xu hướng 4H (mean-reversion — bình thường)",
    "strong_4h_trend_against": "4H trend mạnh ngược lệnh (ADX 4H cao)",
    "weak_rsi_div": "Phân kỳ RSI yếu (Δ < 4)",
    "weak_price_div": "Phân kỳ giá yếu",
    "rsi_not_oversold": "RSI entry chưa oversold (long)",
    "rsi_not_overbought": "RSI entry chưa overbought (short)",
    "strong_1h_trend": "1H trending mạnh (ADX ≥ 30)",
    "late_neckline_break": "Phá neckline trễ (≥ 6 bar)",
    "quick_stop_false_break": "SL nhanh — false breakout",
    "short_swing_gap": "Khoảng cách swing ngắn (< 14 bar)",
    "other": "Khác",
}


def _analyze_period(name: str, df, cfg: RsiDivConfig, equity: float, bt, pip: float) -> dict:
    engine = RsiDivEngine(RiskConfig(0.02, cfg.rr, 0.30, 10), cfg, equity,
                          bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip)
    result = engine.run(df)
    metas = {m.entry_bar: m for m in detect_rsi_signals_with_meta(df, cfg)}
    losses, wins = [], []
    reason_counter: Counter = Counter()

    for t in result.trades:
        if not t.is_closed:
            continue
        bar = df.index.get_loc(t.entry_time)
        meta = metas.get(bar)
        if meta is None:
            continue
        row = {
            "entry": str(t.entry_time),
            "direction": "long" if t.direction == 1 else "short",
            "div_type": meta.div_type,
            "pnl": t.pnl,
            "result": t.result,
            "rsi_diff": meta.rsi_diff,
            "rsi_entry": meta.rsi_entry,
            "htf_trend": meta.htf_trend,
            "htf_adx": meta.htf_adx,
            "adx_1h": meta.adx_1h,
            "neckline_delay": meta.neckline_delay,
            "swing_gap": meta.swing_gap,
        }
        if t.pnl <= 0:
            reasons = classify_loss(meta, t, df)
            row["reasons"] = reasons
            for r in reasons:
                reason_counter[r] += 1
            losses.append(row)
        else:
            wins.append(row)

    m = result.metrics or {}
    print(f"\n  [{name}] Lệnh {m.get('trade_count', 0)} | WR {m.get('win_rate', 0):.1%} | "
          f"{m.get('total_return', 0):+.1%} | Thua {len(losses)} / Thắng {len(wins)}")
    if losses:
        print("  Lệnh thua:")
        for lo in losses:
            rs = ", ".join(REASON_VI.get(r, r) for r in lo["reasons"])
            print(f"    {lo['entry'][:16]} {lo['direction']:>5} ADX1H={lo['adx_1h']:.0f} 4H={lo['htf_trend']:+.0f} → {rs}")
        print("  Nhóm nguyên nhân:")
        for reason, cnt in reason_counter.most_common():
            print(f"    {REASON_VI.get(reason, reason):<45} {cnt}x")

    return {"losses": losses, "wins": wins, "reason_counts": dict(reason_counter), "metrics": m}


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

    print("=" * 72)
    print("  PHÂN TÍCH LỆNH THUA — RSI DIVERGENCE")
    print("=" * 72)

    old_cfg = RsiDivConfig(max_adx_1h=0, max_htf_adx_counter=0, max_neckline_delay=99)
    new_cfg = RsiDivConfig()

    print("\n  --- TRƯỚC TỐI ƯU (baseline) ---")
    train_old = _analyze_period("TRAIN", train_df, old_cfg, args.equity, bt, pip)
    oos_old = _analyze_period("OOS", oos_df, old_cfg, args.equity, bt, pip)

    print("\n  --- SAU TỐI ƯU (max ADX 1H ≤ 35) ---")
    train_new = _analyze_period("TRAIN", train_df, new_cfg, args.equity, bt, pip)
    oos_new = _analyze_period("OOS", oos_df, new_cfg, args.equity, bt, pip)

    print("\n" + "=" * 72)
    print("  KẾT LUẬN TỐI ƯU")
    om, nm = oos_old["metrics"], oos_new["metrics"]
    print(f"    OOS baseline : {om.get('trade_count',0)} lệnh WR {om.get('win_rate',0):.1%} {om.get('total_return',0):+.1%}")
    print(f"    OOS optimized: {nm.get('trade_count',0)} lệnh WR {nm.get('win_rate',0):.1%} {nm.get('total_return',0):+.1%}")
    print("    Filter chính: bỏ lệnh khi ADX 1H > 35 (trend mạnh, mean-reversion kém)")
    print("=" * 72)

    report = {"baseline": {"train": train_old, "oos": oos_old}, "optimized": {"train": train_new, "oos": oos_new}}
    Path("output/rsi_div_loss_analysis.json").write_text(json.dumps(report, indent=2, default=str))
    print(f"\nSaved: output/rsi_div_loss_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
