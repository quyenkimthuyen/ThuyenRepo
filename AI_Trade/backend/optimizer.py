"""Optimize strategy params on validation (2023) — không chạm test OOS."""

from __future__ import annotations

import copy
import json
from itertools import product
from typing import Any

from .analyzer import analyze_patterns, load_strategy
from .backtest import run_backtest
from .config import STRATEGY_PATH
from .detection_config import save_bar_detection_config
from .labels import load_setups
from .pipeline import filter_train_setups

DEFAULT_GRID: dict[str, list[Any]] = {
    "min_similarity": [0.56, 0.60, 0.64],
    "backtest_min_score": [55, 60, 65],
    "min_cluster_win_rate": [0.45, 0.50],
    "bar_tag_threshold": [0.50, 0.52],
}


def _score_metrics(metrics: dict[str, Any]) -> float:
    trades = int(metrics.get("trades") or 0)
    pf = float(metrics.get("profit_factor") or 0)
    wr = float(metrics.get("win_rate") or 0)
    dd = float(metrics.get("max_drawdown_pips") or 9999)
    exp = float(metrics.get("expectancy_pips") or 0)
    passed = bool(metrics.get("pass"))

    if trades < 10:
        return -5000 + trades

    base = pf * 25 + wr * 15 + exp * 3 - dd / 40 + min(trades, 120) / 15
    if passed:
        base += 500
    return base


def _apply_params(strategy: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(strategy)
    for key in ("min_similarity", "backtest_min_score", "min_cluster_win_rate", "bar_tag_threshold"):
        if key in params:
            out[key] = params[key]
    if "require_sequence_tag" in params:
        out["require_sequence_tag"] = bool(params["require_sequence_tag"])
    return out


def optimize_on_validation(
    strategy: dict[str, Any] | None = None,
    *,
    grid: dict[str, list[Any]] | None = None,
    period: str = "validation",
) -> dict[str, Any]:
    strategy = copy.deepcopy(strategy or load_strategy())
    if not strategy:
        raise ValueError("Chưa có chiến lược — chạy Analyze trước.")

    tag_info = strategy.get("tags") or {}
    avoid = list(set(tag_info.get("avoid_tags") or []) | {"reversal"})
    strategy["tags"] = {**tag_info, "avoid_tags": avoid}
    strategy["similarity_train_filter"] = {
        "exclude_tags": avoid,
        "max_setups": 180,
    }

    grid = grid or DEFAULT_GRID
    keys = list(grid.keys())
    combos = [dict(zip(keys, vals)) for vals in product(*(grid[k] for k in keys))]

    baseline = run_backtest(period, strategy=strategy)
    best_params: dict[str, Any] = {}
    best_score = _score_metrics(baseline.get("metrics") or {})
    best_result = baseline

    for params in combos:
        trial = _apply_params(strategy, params)
        result = run_backtest(period, strategy=trial)
        score = _score_metrics(result.get("metrics") or {})
        if score > best_score:
            best_score = score
            best_params = params
            best_result = result

    optimized = _apply_params(strategy, best_params)
    optimized["optimized"] = True
    optimized["optimization"] = {
        "period": period,
        "trials": len(combos) + 1,
        "best_params": best_params,
        "baseline_metrics": baseline.get("metrics"),
        "validation_metrics": best_result.get("metrics"),
        "score": round(best_score, 2),
    }

    STRATEGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_PATH.write_text(json.dumps(optimized, indent=2), encoding="utf-8")

    det_patch = {}
    if "backtest_min_score" in best_params:
        det_patch["backtest_min_score"] = int(best_params["backtest_min_score"])
    if "bar_tag_threshold" in best_params:
        det_patch["bar_tag_threshold"] = float(best_params["bar_tag_threshold"])
    if det_patch:
        save_bar_detection_config(det_patch)

    return {
        "status": "ok",
        "best_params": best_params,
        "baseline": baseline.get("metrics"),
        "optimized_metrics": best_result.get("metrics"),
        "strategy_path": str(STRATEGY_PATH),
        "train_setups_used": len(filter_train_setups(load_setups(), optimized)),
        "avoid_tags": avoid,
    }


def analyze_and_optimize() -> dict[str, Any]:
    analysis = analyze_patterns()
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
