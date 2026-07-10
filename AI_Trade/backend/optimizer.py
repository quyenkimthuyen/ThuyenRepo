"""Optimize strategy params on validation (2023) — không chạm test OOS."""

from __future__ import annotations

import copy
import json
from typing import Any

from .analyzer import analyze_patterns, load_strategy
from .backtest import run_backtest
from .config import STRATEGY_PATH
from .detection_config import save_bar_detection_config
from .labels import load_setups
from .pipeline import filter_train_setups

# Sau lọc 50 setup chất lượng — lọc entry chặt hơn, ít lệnh hơn
HEURISTIC_PARAMS: dict[str, Any] = {
    "min_similarity": 0.68,
    "max_similarity": 0.88,
    "backtest_min_score": 80,
    "min_cluster_win_rate": 0.55,
    "bar_tag_threshold": 0.55,
    "require_sequence_tag": False,
    "entry_cooldown_bars": 24,
    "preferred_entry_tags": ["rejection"],
}


def _apply_params(strategy: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(strategy)
    for key in (
        "min_similarity",
        "max_similarity",
        "backtest_min_score",
        "min_cluster_win_rate",
        "bar_tag_threshold",
        "require_sequence_tag",
        "entry_cooldown_bars",
        "preferred_entry_tags",
    ):
        if key in params:
            out[key] = params[key]
    return out


def _derive_params_from_analysis(strategy: dict[str, Any]) -> dict[str, Any]:
    """Tinh chỉnh nhẹ từ tag insights trên train."""
    params = dict(HEURISTIC_PARAMS)
    tag_rows = (strategy.get("tags") or {}).get("tags") or []
    if not tag_rows:
        return params

    avg_wr = sum(r.get("win_rate", 0) for r in tag_rows) / max(len(tag_rows), 1)
    if avg_wr < 0.40:
        params["min_similarity"] = 0.64
        params["backtest_min_score"] = 62
        params["min_cluster_win_rate"] = 0.52
    return params


def optimize_on_validation(
    strategy: dict[str, Any] | None = None,
    *,
    period: str = "bt_2023",
) -> dict[str, Any]:
    strategy = copy.deepcopy(strategy or load_strategy())
    if not strategy:
        raise ValueError("Chưa có chiến lược — chạy Analyze trước.")

    tag_info = strategy.get("tags") or {}
    avoid = list(set(tag_info.get("avoid_tags") or []) | {"reversal", "breakout"})
    low_wr = [
        r["tag"]
        for r in tag_info.get("tags") or []
        if r.get("total", 0) >= 10 and r.get("win_rate", 1) <= 0.36
    ]
    avoid.extend(low_wr)
    avoid = sorted(set(avoid))

    strategy["tags"] = {**tag_info, "avoid_tags": avoid}
    strategy["similarity_train_filter"] = {
        "exclude_tags": avoid,
        "max_setups": 150,
    }

    params = _derive_params_from_analysis(strategy)
    baseline = run_backtest(period, strategy=strategy)
    optimized = _apply_params(strategy, params)
    optimized["optimized"] = True
    optimized["optimization"] = {
        "period": period,
        "method": "heuristic_from_train + validation_check",
        "best_params": params,
        "baseline_metrics": baseline.get("metrics"),
        "avoid_tags": avoid,
    }

    result = run_backtest(period, strategy=optimized)
    optimized["optimization"]["validation_metrics"] = result.get("metrics")

    STRATEGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_PATH.write_text(json.dumps(optimized, indent=2), encoding="utf-8")

    save_bar_detection_config(
        {
            "backtest_min_score": int(params["backtest_min_score"]),
            "bar_tag_threshold": float(params["bar_tag_threshold"]),
        }
    )

    return {
        "status": "ok",
        "best_params": params,
        "baseline": baseline.get("metrics"),
        "optimized_metrics": result.get("metrics"),
        "strategy_path": str(STRATEGY_PATH),
        "train_setups_used": len(filter_train_setups(load_setups(), optimized)),
        "avoid_tags": avoid,
    }


def analyze_and_optimize(train_period: str | None = None) -> dict[str, Any]:
    analysis = analyze_patterns(train_period=train_period)
    if analysis.get("status") != "ok":
        return {"status": "analyze_failed", "analysis": analysis}

    try:
        optimization = optimize_on_validation()
    except Exception as exc:
        return {"status": "optimize_failed", "analysis": analysis, "error": str(exc)}

    return {
        "status": "ok",
        "analysis": {
            "setup_count": analysis.get("setup_count"),
            "win_rate_train": analysis.get("win_rate_train"),
            "rule_mode": analysis.get("rule_mode"),
            "tag_insights": analysis.get("tag_insights"),
        },
        "optimization": optimization,
    }
