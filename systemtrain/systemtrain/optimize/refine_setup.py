"""Local search on learned setups — mutate thresholds, session, SL."""

from __future__ import annotations

import copy
import random
from typing import Any

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.learn.setup_miner import LearnedSetup, MinedRule, _mutate_setup
from systemtrain.optimize.scoring import combined_robust_score, holdout_metrics, robust_fitness_score
from systemtrain.optimize.models import CandidateResult
from systemtrain.optimize.walk_forward import (
    aggregate_walk_forward_results,
    generate_walk_forward_folds,
    slice_fold,
)
from systemtrain.strategy.learned import learned_to_gene


def setup_from_dict(d: dict[str, Any]) -> LearnedSetup:
    setup = LearnedSetup(
        session_start=d.get("session_start", 7),
        session_end=d.get("session_end", 18),
        cooldown_bars=d.get("cooldown_bars", 4),
        max_trades_per_day=d.get("max_trades_per_day", 4),
        sl_atr_mult=d.get("sl_atr_mult", 1.3),
        atr_period=d.get("atr_period", 14),
        direction=d.get("direction", "both"),
        htf_long_filter=[tuple(x) for x in d.get("htf_long_filter", [])],
        htf_short_filter=[tuple(x) for x in d.get("htf_short_filter", [])],
        source_wr=d.get("source_wr", 0),
        source_samples=d.get("source_samples", 0),
    )
    for r in d.get("long_rules", []):
        setup.long_rules.append(
            MinedRule(
                feature=r["feature"], op=r["op"], threshold=r["threshold"],
                direction=r.get("direction", "long"), win_rate=r.get("win_rate", 0),
                samples=r.get("samples", 0), expectancy=r.get("expectancy", 0),
            )
        )
    for r in d.get("short_rules", []):
        setup.short_rules.append(
            MinedRule(
                feature=r["feature"], op=r["op"], threshold=r["threshold"],
                direction=r.get("direction", "short"), win_rate=r.get("win_rate", 0),
                samples=r.get("samples", 0), expectancy=r.get("expectancy", 0),
            )
        )
    return setup


def _walk_forward(engine: BacktestEngine, df, gene, wf_cfg) -> dict[str, Any]:
    folds = generate_walk_forward_folds(df, wf_cfg)
    fold_results = []
    for fold in folds:
        test_df = slice_fold(df, fold, "test")
        if len(test_df) < 80:
            continue
        result = engine.run(test_df, gene)
        fold_results.append(compute_metrics(result))
    return aggregate_walk_forward_results(fold_results)


def refine_learned_candidates(
    engine: BacktestEngine,
    train_df,
    candidates: list[CandidateResult],
    wf_cfg,
    rounds: int = 10,
    seed: int = 42,
) -> list[CandidateResult]:
    """Mutate top learned setups and keep improvements."""
    rng = random.Random(seed)
    refined: list[CandidateResult] = []

    for cand in candidates[:15]:
        if not cand.gene.learned_setup:
            refined.append(cand)
            continue

        best = copy.deepcopy(cand)
        setup = setup_from_dict(cand.gene.learned_setup)

        for _ in range(rounds):
            mutant = _mutate_setup(setup, rng)
            gene = learned_to_gene(mutant)
            result = engine.run(train_df, gene)
            metrics = compute_metrics(result)
            if metrics.get("trade_count", 0) < 20:
                continue
            wf = _walk_forward(engine, train_df, gene, wf_cfg)
            holdout = holdout_metrics(engine, train_df, gene)
            score = combined_robust_score(metrics, wf, holdout)
            if score > best.fitness:
                mutant.source_wr = metrics.get("win_rate", 0)
                mutant.source_samples = metrics.get("trade_count", 0)
                wf = dict(wf)
                wf["holdout"] = holdout
                best = CandidateResult(
                    gene=learned_to_gene(mutant),
                    fitness=score,
                    train_metrics=metrics,
                    wf_summary=wf,
                )

        refined.append(best)

    refined.sort(key=lambda c: c.fitness, reverse=True)
    return refined
