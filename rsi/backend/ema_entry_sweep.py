"""So sánh entry chạm EMA lần 2 vs lần 3 sau RSI chạm vùng."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data_service import load_candles
from .divergence import find_rsi_divergences
from .entry_signals import find_ema_touch_entry
from .setup_optimizer import RECOMMENDED, backtest_setup, walk_forward_setup, _touch_index
from .zone_stats import ZoneConfig, analyze_zone_touches

SPLIT_DATE = "2025-01-01"
MIN_TRADES = 20


def _signal_stats(df: pd.DataFrame, events: list[dict[str, Any]]) -> dict[str, Any]:
    low = [e for e in events if e["zone"] == "low"]
    stats: dict[str, int] = {}
    configs = [
        ("touch_2", dict(target_touch=2)),
        ("touch_3", dict(target_touch=3)),
        ("reject_2", dict(target_touch=2, require_rejection=True)),
        ("reject_3", dict(target_touch=3, require_rejection=True)),
        ("reject_3_pb10", dict(target_touch=3, require_rejection=True, entry_pullback_pips=10.0)),
    ]
    for name, kw in configs:
        filled = 0
        for ev in low:
            i = _touch_index(df, ev)
            if i is None:
                continue
            if find_ema_touch_entry(df, i, "low", **kw) is not None:
                filled += 1
        stats[name] = filled
    n = len(low)
    return {
        "rsi_touches": n,
        "signals": stats,
        "fill_rates": {k: round(v / n * 100, 1) if n else 0.0 for k, v in stats.items()},
    }


def run_ema_sweep(df: pd.DataFrame | None = None, split_date: str = SPLIT_DATE) -> dict[str, Any]:
    df = df if df is not None else load_candles()
    cfg = ZoneConfig(horizon_bars=48, stop_loss_pips=25.0, take_profit_r=2.5)
    events = analyze_zone_touches(df, cfg)["events"]
    div = find_rsi_divergences(df)

    common = {
        "zone": "low",
        "sl_mode": "fixed",
        "stop_loss_pips": 25.0,
        "take_profit_mode": "r",
        "take_profit_r": 2.5,
        "max_bars": 48,
        "spread_pips": 1.0,
        "divergences": div,
    }

    strategies = [
        "delay_1",
        "ema_touch_2",
        "ema_touch_3",
        "ema_reject_2",
        "ema_reject_3",
        "ema_reject_3_pb10",
    ]
    rows: list[dict[str, Any]] = []
    for strat in strategies:
        full = backtest_setup(df, events, entry_strategy=strat, **common)
        wf = walk_forward_setup(df, events, split_date=split_date, entry_strategy=strat, **common)
        exp = full.get("expectancy_r", 0.0)
        pf = full.get("profit_factor", 0.0)
        stable = wf["comparison"]["stable"]
        score = exp * pf * (1.2 if stable else 0.5) if full.get("trades", 0) >= MIN_TRADES else -999
        rows.append({
            "entry_strategy": strat,
            "trades": full.get("trades", 0),
            "expectancy_r": exp,
            "profit_factor": pf,
            "win_rate": full.get("win_rate", 0),
            "total_pips": full.get("total_pips", 0),
            "stable": stable,
            "train_exp": wf["train"].get("expectancy_r", 0),
            "test_exp": wf["test"].get("expectancy_r", 0),
            "score": round(score, 3),
            "full": full,
            "walk_forward": wf,
        })

    ema_only = [r for r in rows if r["entry_strategy"].startswith("ema_")]
    ema_valid = [r for r in ema_only if r["trades"] >= MIN_TRADES]
    ema_valid.sort(key=lambda r: (r["score"], r["expectancy_r"]), reverse=True)
    best_ema = ema_valid[0] if ema_valid else None

    all_valid = [r for r in rows if r["trades"] >= MIN_TRADES]
    all_valid.sort(key=lambda r: (r["score"], r["expectancy_r"]), reverse=True)
    best_overall = all_valid[0] if all_valid else None

    return {
        "signal_stats": _signal_stats(df, events),
        "results": rows,
        "best_ema": best_ema,
        "best_overall": best_overall,
        "current": RECOMMENDED.get("entry_strategy"),
    }


if __name__ == "__main__":
    out = run_ema_sweep()
    s = out["signal_stats"]
    print("=== Tín hiệu sau RSI chạm vùng hỗ trợ ===")
    print(f"RSI touches: {s['rsi_touches']}")
    for k, v in s["signals"].items():
        print(f"  {k}: {v} ({s['fill_rates'][k]}%)")
    print("\n=== Backtest SL25 TP2.5R ===")
    for r in out["results"]:
        ok = "✓" if r["trades"] >= MIN_TRADES else "·"
        print(
            f"{ok} {r['entry_strategy']:18} n={r['trades']:3} exp={r['expectancy_r']:+.2f}R "
            f"PF={r['profit_factor']:.2f} WR={r['win_rate']}% "
            f"WF train={r['train_exp']:+.2f} test={r['test_exp']:+.2f} stable={r['stable']}"
        )
    if out["best_ema"]:
        print(f"\nBest EMA entry: {out['best_ema']['entry_strategy']}")
    if out["best_overall"]:
        print(f"Best overall: {out['best_overall']['entry_strategy']}")
