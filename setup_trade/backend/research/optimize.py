from __future__ import annotations

import copy
import itertools
from typing import Any

from backend.core.folds import require_optimize_period
from backend.data.loader import load_candles, slice_period
from backend.indicators import add_indicators
from backend.simulator.backtest import run_backtest
from backend.strategy.rsi_ema_v1.config import load_strategy_config

PARAM_GRID: dict[str, list[Any]] = {
    "ema_tolerance_atr": [0.25, 0.35, 0.45, 0.55],
    "entry_cooldown_bars": [12, 24, 36, 48],
    "max_mid_touches": [1, 2],
    "sl_on_ema_break": [False, True],
}

SEARCH_ORDER = ["ema_tolerance_atr", "entry_cooldown_bars", "max_mid_touches", "sl_on_ema_break"]


def _apply_params(base: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    if "ema_tolerance_atr" in params:
        cfg["ema_tolerance_atr"] = params["ema_tolerance_atr"]
    if "entry_cooldown_bars" in params:
        cfg["entry_cooldown_bars"] = params["entry_cooldown_bars"]
    if "max_mid_touches" in params:
        cfg.setdefault("setups", {}).setdefault("s2_extreme_bounce", {})["max_mid_touches"] = params[
            "max_mid_touches"
        ]
    if "sl_on_ema_break" in params:
        cfg.setdefault("risk", {})["sl_on_ema_break"] = params["sl_on_ema_break"]
    return cfg


def _initial_params(cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "ema_tolerance_atr": float(cfg.get("ema_tolerance_atr", 0.35)),
        "entry_cooldown_bars": int(cfg.get("entry_cooldown_bars", 24)),
        "max_mid_touches": int((cfg.get("setups", {}).get("s2_extreme_bounce") or {}).get("max_mid_touches", 2)),
        "sl_on_ema_break": bool((cfg.get("risk") or {}).get("sl_on_ema_break", False)),
    }


def _objective(result: dict[str, Any]) -> float:
    m = result.get("metrics") or {}
    if result.get("pass"):
        return (
            10_000
            + m.get("profit_factor", 0) * 120
            + m.get("win_rate", 0) * 80
            - m.get("max_drawdown_pips", 0) * 0.4
            + min(m.get("trades", 0), 80) * 2
        )
    score = 0.0
    trades = int(m.get("trades", 0))
    pf = float(m.get("profit_factor", 0))
    dd = float(m.get("max_drawdown_pips", 0))
    wr = float(m.get("win_rate", 0))
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


def _eval(cfg: dict[str, Any], params: dict[str, Any], period: str, df) -> dict[str, Any]:
    trial_cfg = _apply_params(cfg, params)
    return run_backtest(df, period, strategy_config=trial_cfg)


def optimize_period(
    optimize_period_name: str,
    *,
    method: str = "greedy",
    save_best: bool = True,
) -> dict[str, Any]:
    fold = require_optimize_period(optimize_period_name)
    base = load_strategy_config()
    df = add_indicators(slice_period(load_candles(), optimize_period_name))

    if method == "grid_full":
        return _grid_full(base, df, optimize_period_name, fold, save_best)

    return _greedy_search(base, df, optimize_period_name, fold, save_best)


def _greedy_search(
    base: dict[str, Any],
    df,
    period: str,
    fold: dict[str, Any],
    save_best: bool,
) -> dict[str, Any]:
    best_params = _initial_params(base)
    best_result = _eval(base, best_params, period, df)
    best_score = _objective(best_result)
    trials: list[dict[str, Any]] = [
        {"params": dict(best_params), "score": best_score, "metrics": best_result["metrics"]}
    ]

    for key in SEARCH_ORDER:
        for value in PARAM_GRID[key]:
            if best_params.get(key) == value:
                continue
            trial_params = {**best_params, key: value}
            result = _eval(base, trial_params, period, df)
            score = _objective(result)
            trials.append({"params": trial_params, "score": score, "metrics": result["metrics"]})
            if score > best_score:
                best_params = trial_params
                best_result = result
                best_score = score

    saved = None
    if save_best:
        from backend.strategy.rsi_ema_v1.store import save_strategy_file

        saved = save_strategy_file(_apply_params(base, best_params))

    return {
        "status": "ok",
        "method": "greedy",
        "fold_id": fold["id"],
        "optimize_period": period,
        "best_params": best_params,
        "best_score": round(best_score, 2),
        "best_metrics": best_result["metrics"],
        "best_pass": best_result["pass"],
        "trials": len(trials),
        "strategy_saved": saved is not None,
    }


def _grid_full(
    base: dict[str, Any],
    df,
    period: str,
    fold: dict[str, Any],
    save_best: bool,
) -> dict[str, Any]:
    keys = SEARCH_ORDER
    combos = list(itertools.product(*[PARAM_GRID[k] for k in keys]))
    best_params = _initial_params(base)
    best_result = _eval(base, best_params, period, df)
    best_score = _objective(best_result)

    for combo in combos:
        params = dict(zip(keys, combo))
        result = _eval(base, params, period, df)
        score = _objective(result)
        if score > best_score:
            best_params = params
            best_result = result
            best_score = score

    saved = None
    if save_best:
        from backend.strategy.rsi_ema_v1.store import save_strategy_file

        saved = save_strategy_file(_apply_params(base, best_params))

    return {
        "status": "ok",
        "method": "grid_full",
        "fold_id": fold["id"],
        "optimize_period": period,
        "combinations_tested": len(combos),
        "best_params": best_params,
        "best_score": round(best_score, 2),
        "best_metrics": best_result["metrics"],
        "best_pass": best_result["pass"],
        "strategy_saved": saved is not None,
    }
