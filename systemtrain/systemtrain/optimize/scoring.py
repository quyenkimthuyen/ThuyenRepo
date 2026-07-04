"""Robust scoring for setup mining — prioritize walk-forward over train fit."""

from __future__ import annotations

from typing import Any

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics


def robust_fitness_score(train_m: dict[str, Any], wf: dict[str, Any]) -> float:
    """
    Rank by walk-forward robustness, not train curve-fit.
    Penalize large train→WF degradation and thin WF evidence.
    """
    train_wr = train_m.get("win_rate", 0)
    train_pf = train_m.get("profit_factor", 0)
    trades = train_m.get("trade_count", 0)
    wf_wr = wf.get("avg_win_rate", train_wr)
    wf_pf = wf.get("avg_profit_factor", train_pf)
    wf_dd = wf.get("avg_max_drawdown", 1.0)
    folds = wf.get("folds_total", 0)

    score = wf_wr * 12.0 + min(wf_pf, 3.0) * 4.0
    score += train_wr * 2.0 + min(train_pf, 3.0) * 1.0
    score += min(trades / 100, 1.0) * 2.0
    score += (0.35 - wf_dd) * 3.0
    score -= abs(train_wr - wf_wr) * 18.0

    if folds >= 2:
        score += folds * 0.5
        if wf_pf >= 1.0:
            score += 3.0
        elif wf_pf < 0.85:
            score -= 4.0
    elif folds < 2:
        score -= 6.0

    if trades < 40:
        score -= (40 - trades) * 0.08

    if train_m.get("halted"):
        score -= 5.0
    return float(score)


def holdout_metrics(
    engine: BacktestEngine,
    train_df: pd.DataFrame,
    gene,
    months: int = 3,
) -> dict[str, Any]:
    """Score on last N months of train — pseudo-OOS before blind test."""
    cutoff = train_df.index.max() - pd.DateOffset(months=months)
    hold = train_df.loc[cutoff:].copy()
    if len(hold) < 80:
        return {}
    return compute_metrics(engine.run(hold, gene))


def combined_robust_score(
    train_m: dict[str, Any],
    wf: dict[str, Any],
    holdout: dict[str, Any],
) -> float:
    score = robust_fitness_score(train_m, wf)
    if not holdout:
        return score - 3.0
    h_wr = holdout.get("win_rate", 0)
    h_pf = holdout.get("profit_factor", 0)
    h_trades = holdout.get("trade_count", 0)
    score += h_wr * 6.0 + min(h_pf, 2.5) * 2.0
    score -= abs(train_m.get("win_rate", 0) - h_wr) * 12.0
    if h_trades < 12:
        score -= 5.0
    if h_pf < 0.9:
        score -= 3.0
    return float(score)
