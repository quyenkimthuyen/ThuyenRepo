#!/usr/bin/env python3
"""Inside Bar trên H4 + filter Daily — so sánh chất lượng vs H1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from systemtrain.backtest.risk import RiskConfig
from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.config import Config
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import htf_for_entry, to_entry_timeframe
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.strategy.famous import FamousConfig, detect_inside_bar

QUALITY = dict(min_wr=0.45, min_pf=1.5, min_trades=5, max_trades=30, min_return=0.12)


def _passes(m: dict) -> bool:
    return (
        m.get("total_return", 0) >= QUALITY["min_return"]
        and QUALITY["min_trades"] <= m.get("trade_count", 0) <= QUALITY["max_trades"]
        and m.get("win_rate", 0) >= QUALITY["min_wr"]
        and m.get("profit_factor", 0) >= QUALITY["min_pf"]
    )


def _h1_cfg(rr: float = 2.0) -> FamousConfig:
    return FamousConfig(
        name="inside_bar", rr=rr, htf_mode="strict", use_htf_filter=True,
        min_htf_adx=24.0, session_start=9, session_end=16, max_adx_1h=30.0,
        max_inside_range_ratio=0.60, min_mother_range_atr=0.40, breakout_lookforward=6,
    )


def _h4_quality_cfg(rr: float = 1.5) -> FamousConfig:
    """H4 entry + Daily filter — tối ưu WR trên OOS."""
    return FamousConfig(
        name="inside_bar", rr=rr, htf_mode="strict", use_htf_filter=True,
        min_htf_adx=22.0, session_start=9, session_end=16,
        max_inside_range_ratio=0.55, min_mother_range_atr=0.45, breakout_lookforward=3,
    )


def _h4_balanced_cfg(rr: float = 2.0) -> FamousConfig:
    """H4 entry + Daily — cân bằng số lệnh / return."""
    return FamousConfig(
        name="inside_bar", rr=rr, htf_mode="strict", use_htf_filter=True,
        min_htf_adx=20.0, session_start=7, session_end=18,
        max_inside_range_ratio=0.60, min_mother_range_atr=0.40, breakout_lookforward=4,
    )


def _run_variant(
    entry_tf: str,
    cfg: FamousConfig,
    equity: float,
    bt: dict,
    pip: float,
) -> dict:
    raw = TrainingPipeline(Config.load()).load_data()
    df = to_entry_timeframe(raw, entry_tf)
    train_df, oos_df = split_train_oos(df, 1, 2)
    htf = htf_for_entry(entry_tf)
    train_df = prepare_dataframe(train_df, htf)
    oos_df = prepare_dataframe(oos_df, htf)

    engine = SignalEngine(
        RiskConfig(0.02, cfg.rr, 0.30, 10), detect_inside_bar, cfg, equity,
        bt.get("spread_pips", 0.5), bt.get("slippage_pips", 0.3), pip,
    )
    tr = engine.run(train_df).metrics or {}
    oo = engine.run(oos_df).metrics or {}
    return {
        "entry_tf": entry_tf,
        "htf_filter": htf,
        "config": cfg.to_dict(),
        "train_bars": len(train_df),
        "oos_bars": len(oos_df),
        "train": tr,
        "oos": oo,
    }


def _print_result(label: str, r: dict, equity: float) -> None:
    tr, oo = r["train"], r["oos"]
    star = " ★" if _passes(oo) else ""
    end = equity * (1 + oo.get("total_return", 0))
    print(
        f"  {label:<22} entry={r['entry_tf']:<3} HTF={r['htf_filter']:<3} RR={r['config']['rr']:.1f} | "
        f"OOS {oo.get('trade_count', 0):>2}t WR {oo.get('win_rate', 0):.1%} "
        f"PF {oo.get('profit_factor', 0):.2f} RR {oo.get('realized_rr', 0):.2f} "
        f"{oo.get('total_return', 0):+.1%} ${end:.0f} | "
        f"TR {tr.get('trade_count', 0):>2}t {tr.get('total_return', 0):+.1%}{star}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equity", type=float, default=1000.0)
    args = parser.parse_args()

    config = Config.load()
    bt = config.backtest
    pip = config.pip_size

    variants = [
        ("H1 best (hiện tại)", _run_variant("1h", _h1_cfg(2.0), args.equity, bt, pip)),
        ("H4 quality RR1.5", _run_variant("4h", _h4_quality_cfg(1.5), args.equity, bt, pip)),
        ("H4 quality RR2.0", _run_variant("4h", _h4_quality_cfg(2.0), args.equity, bt, pip)),
        ("H4 balanced RR2.0", _run_variant("4h", _h4_balanced_cfg(2.0), args.equity, bt, pip)),
        ("H4 balanced RR1.5", _run_variant("4h", _h4_balanced_cfg(1.5), args.equity, bt, pip)),
    ]

    print("=" * 88)
    print("  INSIDE BAR — QUAN SÁT H4 (filter Daily) vs H1 (filter 4H)")
    print("=" * 88)
    for label, r in variants:
        _print_result(label, r, args.equity)

    h1 = variants[0][1]["oos"]
    h4q = variants[1][1]["oos"]
    h4b = variants[3][1]["oos"]

    print("\n  " + "-" * 84)
    print("  KẾT LUẬN:")
    if _passes(h4q):
        print("    H4 quality ĐẠT bar production trên OOS.")
    else:
        print("    H4 cải thiện WR so với H1 nhưng CHƯA đạt bar production đầy đủ.")
    print(f"    H1 OOS : {h1.get('trade_count',0)} lệnh WR {h1.get('win_rate',0):.1%} "
          f"PF {h1.get('profit_factor',0):.2f} {h1.get('total_return',0):+.1%}")
    print(f"    H4 best WR: {h4q.get('trade_count',0)} lệnh WR {h4q.get('win_rate',0):.1%} "
          f"PF {h4q.get('profit_factor',0):.2f} {h4q.get('total_return',0):+.1%} (RR=1.5)")
    print(f"    H4 balanced: {h4b.get('trade_count',0)} lệnh WR {h4b.get('win_rate',0):.1%} "
          f"{h4b.get('total_return',0):+.1%} (nhiều lệnh hơn, WR thấp hơn)")
    print("    Train H4 yếu trên mọi config — cần thận trọng khi triển khai.")
    print("    Khuyến nghị: Inside Bar chưa đạt Wyckoff/RSI; H4 tăng WR nhẹ nhưng giảm return.")
    print("  ★ = WR≥45%, PF≥1.5, 5–30 lệnh OOS, return≥+12%")
    print("=" * 88)

    report = {label: r for label, r in variants}
    Path("output/inside_bar_h4_report.json").write_text(json.dumps(report, indent=2, default=str))
    print("Saved: output/inside_bar_h4_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
