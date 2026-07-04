from __future__ import annotations

import copy
import random
from typing import Any

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.optimize.fitness import evaluate_strategy
from systemtrain.optimize.models import CandidateResult
from systemtrain.strategy.dsl import StrategyGene, mutate_gene


def refine_candidates(
    engine: BacktestEngine,
    train_df: pd.DataFrame,
    candidates: list[CandidateResult],
    fitness_cfg: dict,
    min_trades: int,
    rounds_per_candidate: int = 40,
    variants_per_round: int = 3,
    seed: int = 42,
) -> list[CandidateResult]:
    """Local search: fine-tune top candidates via focused mutation."""
    rng = random.Random(seed)
    refined: list[CandidateResult] = []

    for cand in candidates:
        best = copy.deepcopy(cand)
        for _ in range(rounds_per_candidate):
            for _ in range(variants_per_round):
                mutant = mutate_gene(best.gene, 0.18, rng)
                score, metrics = evaluate_strategy(
                    engine, mutant, train_df, fitness_cfg, min_trades
                )
                if score > best.fitness:
                    best = CandidateResult(gene=mutant, fitness=score, train_metrics=metrics)
        refined.append(best)

    refined.sort(key=lambda c: _train_rank(c.train_metrics, c.fitness), reverse=True)
    return refined


def _train_rank(metrics: dict[str, Any], fitness: float) -> float:
    wr = metrics.get("win_rate", 0)
    pf = metrics.get("profit_factor", 0)
    dd = metrics.get("max_drawdown", 1)
    stab = metrics.get("monthly_stability", 0)
    trades = metrics.get("trade_count", 0)
    if metrics.get("halted"):
        return fitness - 1.0
    return wr * 6.0 + min(pf, 4) * 1.5 + stab * 2.0 + (0.25 - dd) * 2.0 + min(trades / 200, 0.5)


def rank_validated(result: dict[str, Any]) -> float:
    """Rank for keeping top-3 strategies."""
    if result.get("passed"):
        oos = result.get("oos_metrics", {})
        return (
            1000.0
            + oos.get("win_rate", 0) * 8
            + min(oos.get("profit_factor", 0), 4) * 2
            + oos.get("monthly_stability", 0) * 3
            - oos.get("max_drawdown", 0) * 4
        )
    train = result.get("train_metrics", {})
    oos = result.get("oos_metrics", {})
    return (
        result.get("fitness", -1) * 2
        + train.get("win_rate", 0) * 5
        + oos.get("win_rate", 0) * 3
        + min(train.get("profit_factor", 0), 3)
        - train.get("max_drawdown", 0) * 2
    )
