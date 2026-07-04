from __future__ import annotations

from typing import Any

import numpy as np

from systemtrain.backtest.engine import BacktestEngine, BacktestResult
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig
from systemtrain.strategy.dsl import StrategyGene


def evaluate_strategy(
    engine: BacktestEngine,
    gene: StrategyGene,
    df,
    fitness_cfg: dict,
    min_trades: int = 80,
) -> tuple[float, dict[str, Any]]:
    result = engine.run(df, gene)
    metrics = compute_metrics(result)
    score = compute_fitness(metrics, gene, fitness_cfg, min_trades)
    return score, metrics


def compute_fitness(
    metrics: dict[str, Any],
    gene: StrategyGene,
    cfg: dict,
    min_trades: int = 80,
) -> float:
    trade_count = metrics.get("trade_count", 0)
    if trade_count < min_trades:
        ratio = trade_count / max(min_trades, 1)
        return max(-1.0, -0.95 + ratio * 1.2)

    if metrics.get("halted"):
        wr = metrics.get("win_rate", 0)
        return max(-0.5, -0.3 + wr * 1.5)

    min_wr = cfg.get("min_win_rate", 0.60)
    min_pf = cfg.get("min_profit_factor", 1.2)
    max_dd = cfg.get("max_drawdown", 0.25)
    min_stab = cfg.get("min_monthly_stability", 0.55)
    complexity_penalty = cfg.get("complexity_penalty", 0.02)

    wr = metrics.get("win_rate", 0)
    pf = metrics.get("profit_factor", 0)
    dd = metrics.get("max_drawdown", 1)
    stab = metrics.get("monthly_stability", 0)
    exp = metrics.get("expectancy", 0)
    rr = metrics.get("realized_rr", 0)

    # Win rate is primary objective
    score = wr * 6.0 + min(pf, 5.0) * 1.0 + stab * 2.5 + (max_dd - dd) * 2.0
    score += min(rr / 2.0, 1.0) * 1.5
    score += np.sign(exp) * min(abs(exp) / 50, 1.0)

    meets_all = wr >= min_wr and pf >= min_pf and dd <= max_dd and stab >= min_stab and rr >= 1.8
    if meets_all:
        score += 15.0
    elif wr >= min_wr and pf >= min_pf and dd <= max_dd:
        score += 8.0
    elif wr >= min_wr - 0.03:
        score += 3.0

    score -= complexity_penalty * gene.complexity()
    return float(score)


def passes_train_constraints(metrics: dict[str, Any], cfg: dict, min_trades: int) -> bool:
    if metrics.get("trade_count", 0) < min_trades:
        return False
    if metrics.get("halted"):
        return False
    if metrics.get("win_rate", 0) < cfg.get("min_win_rate", 0.60):
        return False
    if metrics.get("profit_factor", 0) < cfg.get("min_profit_factor", 1.2):
        return False
    if metrics.get("max_drawdown", 1) > cfg.get("max_drawdown", 0.25):
        return False
    if metrics.get("monthly_stability", 0) < cfg.get("min_monthly_stability", 0.55):
        return False
    if metrics.get("realized_rr", 0) < 1.5:
        return False
    return True
