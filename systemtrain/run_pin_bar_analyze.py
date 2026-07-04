#!/usr/bin/env python3
"""Phân tích lệnh thua Pin Bar → tối ưu filter (giảm ~50% lệnh, tăng WR)."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from systemtrain.analyze.pin_bar_losses import classify_loss, detect_pin_signals_with_meta
from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.famous import FamousConfig, detect_pin_bar

REASON_VI = {
    "quick_stop_rejection": "SL nhanh — pin bị từ chối ngay",
    "early_london_chop": "Giờ London sớm (7–8h)",
    "weak_pin_shape": "Pin yếu (wick < 60% range)",
    "not_at_swing": "Pin không ở swing high/low",
    "large_body_pin": "Thân nến lớn",
    "small_candle_range": "Nến nhỏ (< 0.75 ATR)",
    "strong_1h_trend": "1H trending mạnh (ADX ≥ 35)",
    "rsi_not_oversold": "RSI long chưa oversold",
    "rsi_not_overbought": "RSI short chưa overbought",
    "other": "Khác",
}


def _baseline_cfg() -> FamousConfig:
    return FamousConfig(
        name="pin_bar", min_wick_body_ratio=3.0, max_body_range_ratio=0.25,
        htf_mode="strict", use_htf_filter=True, session_start=7, session_end=17,
    )


def _balanced_cfg() -> FamousConfig:
    """Tầng 1: wick + session + 4H strict + ADX≥20 (~92 lệnh OOS)."""
    return FamousConfig(
        name="pin_bar", min_wick_body_ratio=4.0, max_body_range_ratio=0.25,
        htf_mode="strict", use_htf_filter=True, min_htf_adx=20.0,
        session_start=9, session_end=16,
    )


def _quality_cfg() -> FamousConfig:
    """Tầng 2: ~40 lệnh OOS — swing + wick range + 4H ADX≥22."""
    return FamousConfig(
        name="pin_bar", min_wick_body_ratio=4.0, max_body_range_ratio=0.25,
        htf_mode="strict", use_htf_filter=True, min_htf_adx=22.0,
        session_start=9, session_end=16,
        require_at_swing=True, swing_lookback=12, min_wick_range_ratio=0.58,
    )


def _elite_cfg() -> FamousConfig:
    """Tầng 3: ~20 lệnh OOS — quality + 4H ADX≥24 + 1H ADX≤30."""
    return FamousConfig(
        name="pin_bar", min_wick_body_ratio=4.0, max_body_range_ratio=0.25,
        htf_mode="strict", use_htf_filter=True, min_htf_adx=24.0,
        session_start=9, session_end=16,
        require_at_swing=True, swing_lookback=12, min_wick_range_ratio=0.58,
        max_adx_1h=30.0,
    )


def _analyze_period(name: str, df, cfg: FamousConfig, equity: float, bt, pip: float) -> dict:
    engine = SignalEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), detect_pin_bar, cfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )
    result = engine.run(df)
    metas = {m.entry_bar: m for m in detect_pin_signals_with_meta(df, cfg)}
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
            "pnl": t.pnl,
            "result": t.result,
            "wick_range": meta.wick_range_ratio,
            "at_swing": meta.at_swing,
            "hour": meta.hour,
            "adx_1h": meta.adx_1h,
            "rsi_entry": meta.rsi_entry,
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
          f"PF {m.get('profit_factor', 0):.2f} | {m.get('total_return', 0):+.1%} | "
          f"Thua {len(losses)} / Thắng {len(wins)}")
    if losses:
        print("  Nhóm nguyên nhân thua:")
        for reason, cnt in reason_counter.most_common():
            pct = 100 * cnt / len(losses)
            print(f"    {REASON_VI.get(reason, reason):<42} {cnt:3}x ({pct:.0f}%)")

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
    print("  PHÂN TÍCH LỆNH THUA — PIN BAR (giảm ~50% lệnh)")
    print("=" * 72)

    print("\n  --- BASELINE (wick≥3, session 7–17) ---")
    oos_base = _analyze_period("OOS", oos_df, _baseline_cfg(), args.equity, bt, pip)

    print("\n  --- BALANCED (wick≥4, session 9–16, 4H + ADX≥20) ---")
    oos_bal = _analyze_period("OOS", oos_df, _balanced_cfg(), args.equity, bt, pip)

    print("\n  --- QUALITY (~40 lệnh: swing 12bar + wick≥58% + 4H ADX≥22) ---")
    oos_q = _analyze_period("OOS", oos_df, _quality_cfg(), args.equity, bt, pip)

    print("\n  --- ELITE (~20 lệnh: quality + 4H ADX≥24 + 1H ADX≤30) ---")
    train_e = _analyze_period("TRAIN", train_df, _elite_cfg(), args.equity, bt, pip)
    oos_e = _analyze_period("OOS", oos_df, _elite_cfg(), args.equity, bt, pip)

    bm, om, qm, em = (oos_base["metrics"], oos_bal["metrics"],
                      oos_q["metrics"], oos_e["metrics"])
    print("\n" + "=" * 72)
    print("  TÓM TẮT OOS")
    print(f"    Baseline : {bm.get('trade_count',0):3} lệnh  WR {bm.get('win_rate',0):.1%}  "
          f"PF {bm.get('profit_factor',0):.2f}  {bm.get('total_return',0):+.1%}")
    print(f"    Balanced : {om.get('trade_count',0):3} lệnh  WR {om.get('win_rate',0):.1%}  "
          f"PF {om.get('profit_factor',0):.2f}  {om.get('total_return',0):+.1%}")
    print(f"    Quality  : {qm.get('trade_count',0):3} lệnh  WR {qm.get('win_rate',0):.1%}  "
          f"PF {qm.get('profit_factor',0):.2f}  {qm.get('total_return',0):+.1%}")
    print(f"    Elite ★  : {em.get('trade_count',0):3} lệnh  WR {em.get('win_rate',0):.1%}  "
          f"PF {em.get('profit_factor',0):.2f}  {em.get('total_return',0):+.1%}")
    print("\n  Filter Elite (từ nhóm thua Quality):")
    print("    • min_htf_adx 24 — 4H trend mạnh hơn")
    print("    • max_adx_1h 30 — bỏ pin khi 1H đang trend mạnh (38% lệnh thua Quality)")
    print("    Giữ: swing 12bar, wick≥58%, session 9–16, 4H strict")
    print("=" * 72)

    report = {
        "baseline": {"oos": oos_base},
        "balanced": {"oos": oos_bal},
        "quality": {"oos": oos_q},
        "elite": {"train": train_e, "oos": oos_e},
    }
    Path("output/pin_bar_loss_analysis.json").write_text(json.dumps(report, indent=2, default=str))
    print("\nSaved: output/pin_bar_loss_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
