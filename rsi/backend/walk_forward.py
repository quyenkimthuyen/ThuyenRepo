"""Walk-forward validation — train vs out-of-sample test."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .zone_stats import ZoneConfig, analyze_zone_touches


DEFAULT_SPLIT = "2025-01-01"


def walk_forward_report(
    df: pd.DataFrame,
    cfg: ZoneConfig,
    split_date: str = DEFAULT_SPLIT,
) -> dict[str, Any]:
    split_ts = pd.Timestamp(split_date, tz="UTC")
    train_df = df[df.index < split_ts]
    test_df = df[df.index >= split_ts]

    train_stats = analyze_zone_touches(train_df, cfg) if len(train_df) > 200 else None
    test_stats = analyze_zone_touches(test_df, cfg) if len(test_df) > 200 else None

    def period_summary(stats: dict[str, Any] | None, label: str, period_df: pd.DataFrame) -> dict[str, Any]:
        if not stats or len(period_df) < 200:
            return {"label": label, "bars": len(period_df), "valid": False}
        zones = stats.get("zones", {})
        low = zones.get("low", {})
        high = zones.get("high", {})
        bt_exit = stats.get("backtest", {}).get("exit", {})
        combined = [r for r in stats.get("conditions", []) if r.get("combined")]
        best = max(combined, key=lambda r: r["reversal_rate"] if r["samples"] >= 5 else -1, default=None)
        return {
            "label": label,
            "valid": True,
            "bars": len(period_df),
            "range": {
                "start": period_df.index[0].isoformat(),
                "end": period_df.index[-1].isoformat(),
            },
            "low_exit_reversal_rate": low.get("exit_reversal_rate", 0),
            "high_exit_reversal_rate": high.get("exit_reversal_rate", 0),
            "low_touches": low.get("touches", 0),
            "high_touches": high.get("touches", 0),
            "backtest_exit": {
                "trades": bt_exit.get("trades", 0),
                "win_rate": bt_exit.get("win_rate", 0),
                "expectancy_r": bt_exit.get("expectancy_r", 0),
                "profit_factor": bt_exit.get("profit_factor", 0),
            },
            "best_combined": best,
        }

    train_sum = period_summary(train_stats, "Train", train_df)
    test_sum = period_summary(test_stats, "Test", test_df)

    if train_stats and test_stats:
        train_bt = train_stats["backtest"]["exit"]
        test_bt = test_stats["backtest"]["exit"]
        expectancy_delta = round(test_bt.get("expectancy_r", 0) - train_bt.get("expectancy_r", 0), 2)
        win_rate_delta = round(test_bt.get("win_rate", 0) - train_bt.get("win_rate", 0), 1)
    else:
        expectancy_delta = 0.0
        win_rate_delta = 0.0

    return {
        "split_date": split_date,
        "train": train_sum,
        "test": test_sum,
        "comparison": {
            "expectancy_r_delta": expectancy_delta,
            "win_rate_delta": win_rate_delta,
            "stable": abs(expectancy_delta) <= 0.15 and abs(win_rate_delta) <= 8,
        },
        "train_events": len(train_stats.get("events", [])) if train_stats else 0,
        "test_events": len(test_stats.get("events", [])) if test_stats else 0,
    }
