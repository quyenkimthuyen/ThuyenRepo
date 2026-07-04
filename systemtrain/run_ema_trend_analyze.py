#!/usr/bin/env python3
"""Phân tích lệnh thua EMA 50/200 → tối ưu thông số."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from systemtrain.analyze.ema_trend_losses import (
    classify_loss,
    detect_ema_signals_with_meta,
    ema_50200_base_cfg,
)
from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.ema_trend import EmaTrendConfig, detect_ema_trend, ema_50200_best_cfg

REASON_VI = {
    "extended_trend": "Trend kéo dài — EMA50/200 spread ≥1.0 ATR",
    "wide_ema_spread": "EMA spread rộng (0.5–1.0 ATR) — vào muộn",
    "loose_pullback": "Pullback lỏng — giá xa EMA50",
    "elevated_1h_adx": "1H ADX cao (≥26) — momentum ngược",
    "weak_4h_adx": "4H ADX yếu (<30)",
    "quick_sl": "SL nhanh (≤3 bar)",
    "session_edge": "Biên phiên (7–8h, 16h)",
    "other": "Khác",
}


def _analyze(name: str, df, cfg: EmaTrendConfig, equity: float, bt, pip: float) -> dict:
    engine = SignalEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), detect_ema_trend, cfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )
    result = engine.run(df)
    metas = {m.entry_bar: m for m in detect_ema_signals_with_meta(df, cfg)}
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
            "spread_atr": meta.ema_spread_atr,
            "dist_atr": meta.dist_fast_atr,
            "htf_adx": meta.htf_adx,
            "adx_1h": meta.adx_1h,
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
        print("  Lệnh thua:")
        for lo in losses:
            rs = ", ".join(REASON_VI.get(r, r) for r in lo["reasons"][:2])
            print(f"    {lo['entry'][:16]} {lo['direction']:>5} spread={lo['spread_atr']:.2f}ATR "
                  f"dist={lo['dist_atr']:.2f} 4H_ADX={lo['htf_adx']:.0f} → {rs}")
        print("  Nhóm nguyên nhân:")
        for reason, cnt in reason_counter.most_common():
            pct = 100 * cnt / len(losses)
            print(f"    {REASON_VI.get(reason, reason):<52} {cnt:2}x ({pct:.0f}%)")

    return {"losses": losses, "wins": wins, "reason_counts": dict(reason_counter), "metrics": m}


def _run_cfg(df, cfg: EmaTrendConfig, equity: float, bt, pip: float) -> dict:
    engine = SignalEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), detect_ema_trend, cfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )
    return engine.run(df).metrics or {}


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
    print("  PHÂN TÍCH LỆNH THUA — EMA 50/200")
    print("=" * 72)

    base_cfg = ema_50200_base_cfg()
    print("\n  --- BASE (trước tối ưu) ---")
    oos_base = _analyze("OOS", oos_df, base_cfg, args.equity, bt, pip)
    train_base = _analyze("TRAIN", train_df, base_cfg, args.equity, bt, pip)

    elite_cfg = ema_50200_best_cfg()
    print("\n  --- ELITE (sau tối ưu) ---")
    oos_elite = _analyze("OOS", oos_df, elite_cfg, args.equity, bt, pip)
    train_elite = _analyze("TRAIN", train_df, elite_cfg, args.equity, bt, pip)

    base_d = base_cfg.to_dict()
    candidates = [
        ("max_spread=2.0", {**base_d, "max_ema_spread_atr": 2.0}),
        ("max_spread=2.2", {**base_d, "max_ema_spread_atr": 2.2}),
        ("pullback=0.40", {**base_d, "pullback_atr": 0.40}),
        ("pullback=0.38", {**base_d, "pullback_atr": 0.38}),
        ("max_adx=25", {**base_d, "max_adx_1h": 25.0}),
        ("max_adx=26", {**base_d, "max_adx_1h": 26.0}),
        ("elite combo", elite_cfg.to_dict()),
    ]
    print("\n  --- THỬ FILTER TỪ PHÂN TÍCH ---")
    print(f"  {'Filter':<22} {'OOS':>4} {'WR':>6} {'PF':>5} {'ret':>7} | {'TR':>4} {'ret':>7}")
    sweep = []
    for label, d in candidates:
        cfg = EmaTrendConfig(**{k: v for k, v in d.items() if k in EmaTrendConfig.__dataclass_fields__})
        o = _run_cfg(oos_df, cfg, args.equity, bt, pip)
        t = _run_cfg(train_df, cfg, args.equity, bt, pip)
        sweep.append({"label": label, "config": d, "oos": o, "train": t})
        print(f"  {label:<22} {o.get('trade_count', 0):4} {o.get('win_rate', 0):5.1%} "
              f"{o.get('profit_factor', 0):5.2f} {o.get('total_return', 0):+6.1%} | "
              f"{t.get('trade_count', 0):4} {t.get('total_return', 0):+6.1%}")

    bm = oos_elite["metrics"]
    print("\n" + "=" * 72)
    print("  KẾT LUẬN")
    print(f"    Elite: {bm.get('trade_count', 0)} lệnh OOS WR {bm.get('win_rate', 0):.1%} "
          f"PF {bm.get('profit_factor', 0):.2f} {bm.get('total_return', 0):+.1%}")
    print("    Nguyên nhân thua chính (base):")
    print("      • extended_trend / wide_ema_spread — vào khi trend đã kéo dài (spread EMA lớn)")
    print("      • elevated_1h_adx — momentum 1H quá mạnh ngược hướng pullback")
    print("    Filter: max_ema_spread_atr≤2.2 + pullback_atr=0.38 + max_adx_1h=26")
    print("=" * 72)

    report = {
        "base": {"train": train_base, "oos": oos_base},
        "elite": {"train": train_elite, "oos": oos_elite},
        "filter_sweep": sweep,
        "elite_config": elite_cfg.to_dict(),
    }
    Path("output/ema_trend_loss_analysis.json").write_text(json.dumps(report, indent=2, default=str))
    print("\nSaved: output/ema_trend_loss_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
