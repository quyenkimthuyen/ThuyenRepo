"""Optimize strategy params on walk-forward validation — không chạm test OOS."""

from __future__ import annotations

import copy
from typing import Any

from .analyzer import analyze_patterns, load_strategy, save_strategy
from .backtest import run_backtest
from .detection_config import save_bar_detection_config
from .labels import load_setups
from .periods import suggested_backtest_period
from .pipeline import filter_train_setups

# Lưới từng tham số — greedy search (nhanh hơn full grid)
PARAM_GRID: dict[str, list[Any]] = {
    "backtest_min_score": [68, 76, 84, 92],
    "min_similarity": [0.64, 0.70, 0.76],
    "min_cluster_win_rate": [0.48, 0.54, 0.58],
    "bar_tag_threshold": [0.52, 0.58, 0.62],
    "entry_cooldown_bars": [24, 36, 48],
    "require_sequence_tag": [False, True],
    "preferred_entry_tags": [[], ["rejection"], ["pullback", "rejection"]],
}

SEARCH_ORDER = [
    "backtest_min_score",
    "min_similarity",
    "bar_tag_threshold",
    "min_cluster_win_rate",
    "preferred_entry_tags",
    "require_sequence_tag",
    "entry_cooldown_bars",
]

FAST_STRIDE = 4
GREEDY_ROUNDS = 1


def _apply_params(strategy: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(strategy)
    for key in PARAM_GRID:
        if key in params:
            out[key] = copy.deepcopy(params[key])
    out.setdefault("max_similarity", 0.92)
    return out


def _initial_params(strategy: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(strategy[key])
        for key in PARAM_GRID
        if key in strategy
    }


def _derive_avoid_tags(strategy: dict[str, Any]) -> list[str]:
    tag_info = strategy.get("tags") or {}
    avoid = set(tag_info.get("avoid_tags") or []) | {"reversal"}
    for r in tag_info.get("tags") or []:
        if r.get("total", 0) >= 8 and r.get("win_rate", 1) <= 0.38:
            avoid.add(r["tag"])
        if r.get("tag") == "breakout" and r.get("win_rate", 1) <= 0.45:
            avoid.add("breakout")
    return sorted(avoid)


def _objective(metrics: dict[str, Any]) -> float:
    if metrics.get("pass"):
        return (
            10_000
            + metrics.get("profit_factor", 0) * 120
            + metrics.get("win_rate", 0) * 80
            - metrics.get("max_drawdown_pips", 0) * 0.4
            + min(metrics.get("trades", 0), 80) * 2
        )

    score = 0.0
    trades = int(metrics.get("trades", 0))
    pf = float(metrics.get("profit_factor", 0))
    dd = float(metrics.get("max_drawdown_pips", 0))
    wr = float(metrics.get("win_rate", 0))

    if trades < 30:
        score -= (30 - trades) * 40
    else:
        score += 80
    score += min(pf, 3.0) * 150
    if pf >= 1.3:
        score += 100
    if dd <= 250:
        score += 60
    else:
        score -= (dd - 250) * 0.8
    score += wr * 60
    return score


def _prepare_strategy(strategy: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(strategy)
    avoid = _derive_avoid_tags(out)
    tag_info = out.get("tags") or {}
    out["tags"] = {**tag_info, "avoid_tags": avoid}
    out["similarity_train_filter"] = {
        "exclude_tags": avoid,
        "max_setups": 150,
    }
    return out


def _eval_params(
    strategy: dict[str, Any],
    params: dict[str, Any],
    validation_period: str,
    *,
    bar_stride: int,
) -> dict[str, Any]:
    trial = _apply_params(strategy, params)
    return run_backtest(
        validation_period,
        strategy=trial,
        bar_stride=bar_stride,
    ).get("metrics", {})


def _greedy_search(
    strategy: dict[str, Any],
    validation_period: str,
    *,
    start_params: dict[str, Any],
    bar_stride: int = FAST_STRIDE,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    params = dict(start_params)
    history: list[dict[str, Any]] = []

    metrics = _eval_params(strategy, params, validation_period, bar_stride=bar_stride)
    best_score = _objective(metrics)

    for _round in range(GREEDY_ROUNDS):
        for key in SEARCH_ORDER:
            local_best = params.get(key)
            local_score = best_score
            local_metrics = metrics
            for val in PARAM_GRID[key]:
                trial = {**params, key: copy.deepcopy(val)}
                m = _eval_params(strategy, trial, validation_period, bar_stride=bar_stride)
                sc = _objective(m)
                if sc > local_score:
                    local_score = sc
                    local_best = copy.deepcopy(val)
                    local_metrics = m
            if local_best is not None:
                params[key] = local_best
                best_score = local_score
                metrics = local_metrics
                history.append(
                    {
                        "round": _round + 1,
                        "param": key,
                        "value": local_best,
                        "score": round(best_score, 1),
                        "metrics": metrics,
                    }
                )

    return params, metrics, history


def optimize_on_validation(
    strategy: dict[str, Any] | None = None,
    *,
    train_period: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    strategy = _prepare_strategy(strategy or load_strategy(train_period))
    if not strategy:
        raise ValueError("Chưa có chiến lược — chạy Analyze trước.")

    train_period = train_period or strategy.get("train_period")
    validation_period = period or (
        suggested_backtest_period(train_period) if train_period else "bt_2023"
    )

    baseline = run_backtest(validation_period, strategy=strategy)
    start_params = _initial_params(strategy)
    for key, values in PARAM_GRID.items():
        if key not in start_params:
            start_params[key] = copy.deepcopy(values[len(values) // 2])

    best_params, fast_metrics, history = _greedy_search(
        strategy,
        validation_period,
        start_params=start_params,
        bar_stride=FAST_STRIDE,
    )

    optimized = _apply_params(strategy, best_params)
    optimized["optimized"] = True
    optimized["optimization"] = {
        "train_period": train_period,
        "validation_period": validation_period,
        "method": "greedy_pass_criteria",
        "fast_stride": FAST_STRIDE,
        "best_params": best_params,
        "baseline_metrics": baseline.get("metrics"),
        "fast_search_metrics": fast_metrics,
        "search_history": history[-12:],
        "avoid_tags": optimized.get("tags", {}).get("avoid_tags"),
    }

    result = run_backtest(validation_period, strategy=optimized)
    optimized["optimization"]["validation_metrics"] = result.get("metrics")

    save_strategy(optimized, train_period=optimized.get("train_period"))

    save_bar_detection_config(
        {
            "backtest_min_score": int(best_params["backtest_min_score"]),
            "bar_tag_threshold": float(best_params["bar_tag_threshold"]),
        }
    )

    return {
        "status": "ok",
        "train_period": train_period,
        "validation_period": validation_period,
        "best_params": best_params,
        "baseline": baseline.get("metrics"),
        "optimized_metrics": result.get("metrics"),
        "fast_search_metrics": fast_metrics,
        "search_history": history[-12:],
        "train_setups_used": len(filter_train_setups(load_setups(), optimized)),
        "avoid_tags": optimized.get("tags", {}).get("avoid_tags"),
        "pass": bool(result.get("metrics", {}).get("pass")),
    }


def analyze_and_optimize(train_period: str | None = None) -> dict[str, Any]:
    analysis = analyze_patterns(train_period=train_period)
    if analysis.get("status") != "ok":
        return {"status": "analyze_failed", "analysis": analysis}

    try:
        optimization = optimize_on_validation(train_period=train_period)
    except Exception as exc:
        return {"status": "optimize_failed", "analysis": analysis, "error": str(exc)}

    return {
        "status": "ok",
        "analysis": analysis,
        "optimization": optimization,
        "train_period": analysis.get("train_period"),
        "train_year": analysis.get("train_year"),
        "setup_count": analysis.get("setup_count"),
        "win_rate_train": analysis.get("win_rate_train"),
        "rule_mode": analysis.get("rule_mode"),
        "tag_insights": analysis.get("tag_insights"),
        "tag_coverage": analysis.get("tag_coverage"),
        "bar_annotation_count": analysis.get("bar_annotation_count"),
        "pipeline": analysis.get("pipeline"),
        "pipeline_flow": analysis.get("pipeline_flow"),
        "rules": analysis.get("rules"),
        "risk": analysis.get("risk"),
        "tag_profiles": analysis.get("tag_profiles"),
        "tag_signatures": analysis.get("tag_signatures"),
        "feature_insights": analysis.get("feature_insights"),
        "tree_summary": analysis.get("tree_summary"),
        "optimization_pass": optimization.get("pass"),
        "validation_period": optimization.get("validation_period"),
        "optimized_metrics": optimization.get("optimized_metrics"),
        "baseline_metrics": optimization.get("baseline"),
        "best_params": optimization.get("best_params"),
    }
