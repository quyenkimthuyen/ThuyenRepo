from __future__ import annotations

import random
from typing import Any

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.optimize.fitness import evaluate_strategy, passes_train_constraints
from systemtrain.optimize.refine import refine_candidates
from systemtrain.optimize.walk_forward import (
    aggregate_walk_forward_results,
    generate_walk_forward_folds,
    slice_fold,
)
from systemtrain.strategy.dsl import StrategyGene
from systemtrain.strategy.generator import breed_next_generation, create_initial_population


from systemtrain.optimize.models import CandidateResult, GAResult


class GeneticOptimizer:
    def __init__(
        self,
        engine: BacktestEngine,
        train_df: pd.DataFrame,
        fitness_cfg: dict,
        optimize_cfg: dict,
        wf_cfg,
        seed: int = 42,
    ):
        self.engine = engine
        self.train_df = train_df
        self.fitness_cfg = fitness_cfg
        self.optimize_cfg = optimize_cfg
        self.wf_cfg = wf_cfg
        self.rng = random.Random(seed)
        self.folds = generate_walk_forward_folds(train_df, wf_cfg)
        self.min_trades = optimize_cfg.get("min_trades_per_year", 80)

    def run(self) -> GAResult:
        pop_size = self.optimize_cfg.get("population_size", 40)
        generations = self.optimize_cfg.get("generations", 25)
        top_k = self.optimize_cfg.get("top_k", 3)
        pool_k = self.optimize_cfg.get("refine_pool_size", 12)
        refinement_rounds = self.optimize_cfg.get("refinement_rounds", 35)

        population = create_initial_population(pop_size, seed=self.rng.randint(0, 10_000))
        generation_log: list[dict[str, Any]] = []

        for gen in range(generations):
            scores: list[float] = []
            best_wr = 0.0
            for gene in population:
                score, metrics = self._evaluate_on_train(gene)
                scores.append(score)
                best_wr = max(best_wr, metrics.get("win_rate", 0))

            valid_scores = [s for s in scores if s > -0.5]
            generation_log.append(
                {
                    "generation": gen,
                    "best_fitness": max(scores) if scores else -1,
                    "avg_fitness": sum(valid_scores) / len(valid_scores) if valid_scores else -1,
                    "best_win_rate": best_wr,
                    "population_size": len(population),
                }
            )

            population = breed_next_generation(
                population,
                scores,
                elite_count=self.optimize_cfg.get("elite_count", 5),
                tournament_size=self.optimize_cfg.get("tournament_size", 3),
                crossover_rate=self.optimize_cfg.get("crossover_rate", 0.7),
                mutation_rate=self.optimize_cfg.get("mutation_rate", 0.3),
                rng=self.rng,
            )

        final_candidates = self._select_final_candidates(population, top_k=pool_k)

        if refinement_rounds > 0:
            final_candidates = refine_candidates(
                self.engine,
                self.train_df,
                final_candidates,
                self.fitness_cfg,
                self.min_trades,
                rounds_per_candidate=refinement_rounds,
                seed=self.rng.randint(0, 10_000),
            )

        for cand in final_candidates:
            cand.wf_summary = self._walk_forward_eval(cand.gene)

        merged = self._dedupe_candidates(final_candidates, top_k)
        if len(merged) < top_k:
            backup = self._select_final_candidates(population, top_k=pool_k)
            for cand in backup:
                if len(merged) >= top_k:
                    break
                key = str(cand.gene.to_dict())
                if key not in {str(c.gene.to_dict()) for c in merged}:
                    cand.wf_summary = self._walk_forward_eval(cand.gene)
                    merged.append(cand)

        merged.sort(key=lambda c: c.fitness, reverse=True)
        return GAResult(
            best_candidates=merged[:pool_k],
            generation_log=generation_log,
        )

    def _dedupe_candidates(
        self, candidates: list[CandidateResult], top_k: int
    ) -> list[CandidateResult]:
        seen: set[str] = set()
        unique: list[CandidateResult] = []
        for c in candidates:
            key = str(c.gene.to_dict())
            if key in seen:
                continue
            seen.add(key)
            unique.append(c)
            if len(unique) >= top_k:
                break
        return unique

    def _evaluate_on_train(self, gene: StrategyGene) -> tuple[float, dict]:
        return evaluate_strategy(
            self.engine, gene, self.train_df, self.fitness_cfg, self.min_trades
        )

    def _select_final_candidates(self, population: list[StrategyGene], top_k: int) -> list[CandidateResult]:
        scored: list[CandidateResult] = []
        for gene in population:
            score, metrics = self._evaluate_on_train(gene)
            scored.append(CandidateResult(gene=gene, fitness=score, train_metrics=metrics))
        scored.sort(key=lambda c: c.fitness, reverse=True)
        seen: set[str] = set()
        unique: list[CandidateResult] = []
        for c in scored:
            key = str(c.gene.to_dict())
            if key not in seen:
                seen.add(key)
                unique.append(c)
            if len(unique) >= top_k:
                break
        return unique

    def _walk_forward_eval(self, gene: StrategyGene) -> dict[str, Any]:
        if not self.folds:
            _, metrics = self._evaluate_on_train(gene)
            return {"folds_passed": 0, "folds_total": 0, "note": "no_folds", "full_train": metrics}

        fold_results = []
        min_trades_fold = max(20, self.min_trades // 4)

        for fold in self.folds:
            test_df = slice_fold(self.train_df, fold, "test")
            if len(test_df) < 50:
                continue
            result = self.engine.run(test_df, gene)
            from systemtrain.backtest.metrics import compute_metrics

            metrics = compute_metrics(result)
            passed = passes_train_constraints(
                metrics,
                {**self.fitness_cfg, "min_win_rate": self.fitness_cfg.get("min_win_rate", 0.60) * 0.95},
                min_trades_fold,
            )
            metrics["passed"] = passed
            fold_results.append(metrics)

        return aggregate_walk_forward_results(fold_results)
