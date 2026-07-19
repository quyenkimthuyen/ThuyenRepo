"""Sweep improved entry + SL combos; pick best by expectancy & walk-forward."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .data_service import load_candles
from .divergence import find_rsi_divergences
from .entry_signals import EntryStrategy
from .setup_optimizer import backtest_setup, walk_forward_setup
from .zone_stats import ZoneConfig, analyze_zone_touches

MIN_TRADES = 30
SPLIT_DATE = "2025-01-01"

ENTRY_STRATEGIES: list[EntryStrategy] = [
    "touch",
    "delay_1",
    "delay_2",
    "confirm_candle",
    "confirm_delay1",
    "touch_div",
    "touch_confirm",
]

SL_CONFIGS: list[dict[str, Any]] = [
    {"sl_mode": "fixed", "stop_loss_pips": 25.0},
    {"sl_mode": "atr", "stop_loss_atr_mult": 1.0, "stop_loss_pips": 25.0},
    {"sl_mode": "atr", "stop_loss_atr_mult": 1.5, "stop_loss_pips": 25.0},
    {"sl_mode": "swing", "stop_loss_pips": 25.0},
]

TP_CONFIGS: list[dict[str, Any]] = [
    {"take_profit_mode": "rsi_zone", "take_profit_r": 2.5},
    {"take_profit_mode": "r", "take_profit_r": 2.5},
]


def run_sweep(df: pd.DataFrame | None = None, split_date: str = SPLIT_DATE) -> dict[str, Any]:
    df = df if df is not None else load_candles()
    cfg = ZoneConfig(horizon_bars=48, stop_loss_pips=25.0, take_profit_r=2.5)
    stats = analyze_zone_touches(df, cfg)
    events = stats["events"]
    divergences = find_rsi_divergences(df)

    rows: list[dict[str, Any]] = []

    for zone in ("low",):
        for entry_strategy in ENTRY_STRATEGIES:
            for sl in SL_CONFIGS:
                for tp in TP_CONFIGS:
                    params = {
                        "zone": zone,
                        "entry_strategy": entry_strategy,
                        "max_bars": 48,
                        "spread_pips": 1.0,
                        "filters": [],
                        **sl,
                        **tp,
                    }
                    full = backtest_setup(df, events, divergences=divergences, **params)
                    if full.get("trades", 0) < MIN_TRADES:
                        continue
                    wf = walk_forward_setup(
                        df, events, split_date=split_date, divergences=divergences, **params
                    )
                    stable = wf["comparison"]["stable"]
                    exp = full.get("expectancy_r", 0.0)
                    pf = full.get("profit_factor", 0.0)
                    score = exp * pf * (1.2 if stable else 0.5)
                    rows.append({
                        "score": round(score, 3),
                        "expectancy_r": exp,
                        "profit_factor": pf,
                        "trades": full.get("trades"),
                        "win_rate": full.get("win_rate"),
                        "stable": stable,
                        "train_exp": wf["train"].get("expectancy_r", 0),
                        "test_exp": wf["test"].get("expectancy_r", 0),
                        "params": params,
                        "full": full,
                        "walk_forward": wf,
                    })

    rows.sort(key=lambda r: (r["score"], r["expectancy_r"]), reverse=True)
    best = rows[0] if rows else None
    baseline = backtest_setup(
        df,
        events,
        zone="low",
        entry_strategy="touch",
        sl_mode="fixed",
        stop_loss_pips=25.0,
        take_profit_mode="rsi_zone",
        take_profit_r=2.5,
        max_bars=48,
        divergences=divergences,
    )
    baseline_wf = walk_forward_setup(
        df,
        events,
        split_date=split_date,
        zone="low",
        entry_strategy="touch",
        sl_mode="fixed",
        stop_loss_pips=25.0,
        take_profit_mode="rsi_zone",
        take_profit_r=2.5,
        max_bars=48,
        divergences=divergences,
    )

    return {
        "candidates": rows[:15],
        "best": best,
        "baseline": {"full": baseline, "walk_forward": baseline_wf},
        "total_tested": len(ENTRY_STRATEGIES) * len(SL_CONFIGS) * len(TP_CONFIGS),
        "passed_min_trades": len(rows),
    }


def format_best(sweep: dict[str, Any]) -> str:
    best = sweep.get("best")
    if not best:
        return "No setup passed minimum trade count."
    p = best["params"]
    lines = [
        f"Best: entry={p['entry_strategy']} sl={p['sl_mode']} tp={p['take_profit_mode']}",
        f"  expectancy={best['expectancy_r']}R PF={best['profit_factor']} n={best['trades']} WR={best['win_rate']}%",
        f"  WF train={best['train_exp']}R test={best['test_exp']}R stable={best['stable']}",
    ]
    b = sweep["baseline"]["full"]
    lines.append(
        f"Baseline touch/fixed/rsi_zone: exp={b.get('expectancy_r')}R PF={b.get('profit_factor')} n={b.get('trades')}"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_sweep()
    print(format_best(result))
    print(f"\nTop 5 of {result['passed_min_trades']} valid setups:")
    for i, row in enumerate(result["candidates"][:5], 1):
        p = row["params"]
        print(
            f"{i}. {p['entry_strategy']:16} sl={p['sl_mode']:5} tp={p['take_profit_mode']:8} "
            f"exp={row['expectancy_r']:+.2f}R PF={row['profit_factor']:.2f} n={row['trades']} stable={row['stable']}"
        )
