"""Optimize RSI H4 band strategy on walk-forward validation."""

from __future__ import annotations

import copy
from typing import Any

from .analyzer import analyze_patterns, load_strategy, save_strategy
from .backtest import run_backtest
from .labels import load_setups
from .periods import suggested_backtest_period
from .rsi_h4_strategy import load_rsi_h4_config

PARAM_GRID: dict[str, list[Any]] = {
    "entry_cooldown_bars": [12, 24, 36, 48, 72],
    "ema_tolerance_atr": [0.25, 0.35, 0.45, 0.55],
    "lookback_bars": [60, 80, 120, 160],
    "rsi_rise_min": [0.1, 0.2, 0.3, 0.5],
}

SEARCH_ORDER = [
    "lookback_bars",
    "ema_tolerance_atr",
    "rsi_rise_min",
    "entry_cooldown_bars",
]

FAST_STRIDE = 2
GREEDY_ROUNDS = 1


def _apply_params(strategy: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(strategy)
    for key, value in params.items():
        if key in PARAM_GRID:
            out[key] = copy.deepcopy(value)
    return out


def _initial_params(strategy: dict[str, Any]) -> dict[str, Any]:
    cfg = load_rsi_h4_config(strategy)
    return {
        "entry_cooldown_bars": int(strategy.get("entry_cooldown_bars", cfg.get("entry_cooldown_bars", 24))),
        "ema_tolerance_atr": float(strategy.get("ema_tolerance_atr", cfg.get("ema_tolerance_atr", 0.35))),
        "lookback_bars": int(strategy.get("lookback_bars", cfg.get("lookback_bars", 120))),
        "rsi_rise_min": float(strategy.get("rsi_rise_min", cfg.get("rsi_rise_min", 0.3))),
    }


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


def _eval_params(
    strategy: dict[str, Any],
    params: dict[str, Any],
    validation_period: str,
    *,
    bar_stride: int,
) -> dict[str, Any]:
    trial = _apply_params(strategy, params)
    result = run_backtest(periods=[validation_period], strategy=trial, bar_stride=bar_stride)
    return result.get("metrics") or {}


def _greedy_search(
    strategy: dict[str, Any],
    validation_period: str,
    *,
    bar_stride: int = FAST_STRIDE,
) -> tuple[dict[str, Any], dict[str, Any]]:
    best_params = _initial_params(strategy)
    best_metrics = _eval_params(strategy, best_params, validation_period, bar_stride=bar_stride)
    best_score = _objective(best_metrics)

    for _ in range(GREEDY_ROUNDS):
        for key in SEARCH_ORDER:
            options = PARAM_GRID.get(key, [])
            if not options:
                continue
            local_best = best_params[key]
            local_metrics = best_metrics
            local_score = best_score
            for value in options:
                trial = {**best_params, key: value}
                metrics = _eval_params(strategy, trial, validation_period, bar_stride=bar_stride)
                score = _objective(metrics)
                if score > local_score:
                    local_best = value
                    local_metrics = metrics
                    local_score = score
            best_params[key] = local_best
            best_metrics = local_metrics
            best_score = local_score

    return best_params, best_metrics


def analyze_and_optimize(train_period: str | None = None) -> dict[str, Any]:
    analysis = analyze_patterns(train_period=train_period)
    if analysis.get("status") != "ok":
        return {"status": analysis.get("status"), "analysis": analysis}

    train_period = analysis["train_period"]
    strategy = load_strategy(train_period)
    if not strategy:
        return {"status": "no_strategy", "analysis": analysis}

    validation_period = suggested_backtest_period(train_period)
    baseline = run_backtest(periods=[validation_period], strategy=strategy, bar_stride=1)
    baseline_metrics = baseline.get("metrics") or {}

    if baseline_metrics.get("pass"):
        return {
            "status": "ok",
            "train_period": train_period,
            "validation_period": validation_period,
            "analysis": analysis,
            "optimization": {
                "status": "ok",
                "train_period": train_period,
                "validation_period": validation_period,
                "best_params": _initial_params(strategy),
                "baseline": baseline_metrics,
                "optimized_metrics": baseline_metrics,
                "skipped": True,
                "skip_reason": "baseline_already_passes",
                "pass": True,
            },
        }

    best_params, opt_metrics_fast = _greedy_search(strategy, validation_period, bar_stride=FAST_STRIDE)
    optimized = _apply_params(strategy, best_params)
    opt_metrics = _eval_params(strategy, best_params, validation_period, bar_stride=1)
    save_strategy(optimized, train_period=train_period)

    baseline_score = _objective(baseline_metrics)
    opt_score = _objective(opt_metrics)
    if opt_score <= baseline_score:
        save_strategy(strategy, train_period=train_period)
        opt_metrics = baseline_metrics
        best_params = _initial_params(strategy)
        skipped = True
        skip_reason = "optimized_not_better"
    else:
        skipped = False
        skip_reason = None

    return {
        "status": "ok",
        "train_period": train_period,
        "validation_period": validation_period,
        "analysis": analysis,
        "optimization": {
            "status": "ok",
            "train_period": train_period,
            "validation_period": validation_period,
            "best_params": best_params,
            "baseline": baseline_metrics,
            "optimized_metrics": opt_metrics,
            "skipped": skipped,
            "skip_reason": skip_reason,
            "pass": bool(opt_metrics.get("pass")),
        },
    }
