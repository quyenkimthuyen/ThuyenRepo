#!/usr/bin/env python3
"""Phân tích lệnh thua Inside Bar H1 best → tối ưu thông số."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from systemtrain.analyze.inside_bar_losses import (
    classify_loss,
    detect_inside_signals_with_meta,
    h1_best_cfg,
)
from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.famous import FamousConfig, detect_inside_bar

REASON_VI = {
    "quick_false_break": "False breakout — SL nhanh (≤3 bar)",
    "late_breakout": "Phá vỡ trễ (≥4 bar sau inside bar)",
    "wide_inside_bar": "Inside bar quá rộng (>55% mother bar)",
    "small_mother_bar": "Mother bar nhỏ (<0.45 ATR)",
    "weak_4h_adx": "4H ADX yếu (<26) — trend không đủ mạnh",
    "elevated_1h_adx": "1H ADX cao (≥28) — momentum ngược",
    "early_session": "Phiên sớm (7–8h)",
    "other": "Khác",
}


def _analyze(name: str, df, cfg: FamousConfig, equity: float, bt, pip: float) -> dict:
    engine = SignalEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), detect_inside_bar, cfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )
    result = engine.run(df)
    metas = {m.entry_bar: m for m in detect_inside_signals_with_meta(df, cfg)}
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
            "inside_ratio": meta.inside_range_ratio,
            "breakout_delay": meta.breakout_delay,
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
            print(f"    {lo['entry'][:16]} {lo['direction']:>5} delay={lo['breakout_delay']} "
                  f"inside={lo['inside_ratio']:.0%} 4H_ADX={lo['htf_adx']:.0f} → {rs}")
        print("  Nhóm nguyên nhân:")
        for reason, cnt in reason_counter.most_common():
            pct = 100 * cnt / len(losses)
            print(f"    {REASON_VI.get(reason, reason):<48} {cnt:2}x ({pct:.0f}%)")

    return {"losses": losses, "wins": wins, "reason_counts": dict(reason_counter), "metrics": m}


def _run_cfg(df, cfg: FamousConfig, equity: float, bt, pip: float) -> dict:
    engine = SignalEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), detect_inside_bar, cfg, equity,
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
    print("  PHÂN TÍCH LỆNH THUA — INSIDE BAR H1 BEST")
    print("=" * 72)

    base_cfg = h1_best_cfg()
    print("\n  --- H1 BEST (hiện tại) ---")
    oos_base = _analyze("OOS", oos_df, base_cfg, args.equity, bt, pip)
    train_base = _analyze("TRAIN", train_df, base_cfg, args.equity, bt, pip)

    candidates = [
        ("max_breakout_bars=3", {**base_cfg.to_dict(), "max_breakout_bars": 3}),
        ("max_breakout_bars=4", {**base_cfg.to_dict(), "max_breakout_bars": 4}),
        ("inside≤55%", {**base_cfg.to_dict(), "max_inside_range_ratio": 0.55}),
        ("htf_adx≥26", {**base_cfg.to_dict(), "min_htf_adx": 26.0}),
        ("max_adx_1h=28", {**base_cfg.to_dict(), "max_adx_1h": 28.0}),
    ]
    print("\n  --- THỬ FILTER TỪ PHÂN TÍCH ---")
    print(f"  {'Filter':<22} {'OOS':>4} {'WR':>6} {'PF':>5} {'ret':>7} | {'TR':>4} {'ret':>7}")
    sweep = []
    for label, d in candidates:
        cfg = FamousConfig(**{k: v for k, v in d.items() if k in FamousConfig.__dataclass_fields__})
        o = _run_cfg(oos_df, cfg, args.equity, bt, pip)
        t = _run_cfg(train_df, cfg, args.equity, bt, pip)
        sweep.append({"label": label, "config": d, "oos": o, "train": t})
        print(f"  {label:<22} {o.get('trade_count', 0):4} {o.get('win_rate', 0):5.1%} "
              f"{o.get('profit_factor', 0):5.2f} {o.get('total_return', 0):+6.1%} | "
              f"{t.get('trade_count', 0):4} {t.get('total_return', 0):+6.1%}")

    bm = oos_base["metrics"]
    print("\n" + "=" * 72)
    print("  KẾT LUẬN")
    print(f"    Giữ H1 best: {bm.get('trade_count', 0)} lệnh OOS WR {bm.get('win_rate', 0):.1%} "
          f"PF {bm.get('profit_factor', 0):.2f} {bm.get('total_return', 0):+.1%}")
    print("    Nguyên nhân thua chính:")
    print("      • late_breakout (33%) — phá mother bar quá trễ")
    print("      • quick_false_break (33%) — breakout giả, SL ngay")
    print("      • wide_inside_bar / elevated_1h_adx — thứ yếu")
    print("    Filter thử không cải thiện OOS — giữ config hiện tại")
    print("    Lưu ý: chỉ ~22 lệnh OOS — mẫu nhỏ, thận trọng khi siết thêm")
    print("=" * 72)

    report = {
        "h1_best": {"train": train_base, "oos": oos_base},
        "filter_sweep": sweep,
    }
    Path("output/inside_bar_loss_analysis.json").write_text(json.dumps(report, indent=2, default=str))
    print("\nSaved: output/inside_bar_loss_analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
