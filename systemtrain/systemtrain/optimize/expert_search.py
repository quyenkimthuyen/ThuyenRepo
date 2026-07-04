"""Expert parameter search — walk-forward driven optimization."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.optimize.fitness import evaluate_strategy, passes_train_constraints
from systemtrain.optimize.models import CandidateResult, GAResult
from systemtrain.optimize.walk_forward import (
    aggregate_walk_forward_results,
    generate_walk_forward_folds,
    slice_fold,
)
from systemtrain.strategy.expert import (
    FAMILIES,
    build_gene,
    mutate_expert_params,
    random_expert_params,
)


@dataclass
class ExpertSearchConfig:
    trials: int = 250
    refine_trials: int = 80
    refine_top: int = 15
    top_k: int = 3
    min_trades_per_year: int = 60


class ExpertSearchOptimizer:
    """
    Search expert strategy families with walk-forward validation.
    Primary fitness = robustness across WF folds, not single-year curve-fit.
    """

    def __init__(
        self,
        engine: BacktestEngine,
        train_df: pd.DataFrame,
        fitness_cfg: dict,
        wf_cfg,
        search_cfg: ExpertSearchConfig | None = None,
        seed: int = 42,
    ):
        self.engine = engine
        self.train_df = train_df
        self.fitness_cfg = fitness_cfg
        self.wf_cfg = wf_cfg
        self.cfg = search_cfg or ExpertSearchConfig()
        self.rng = random.Random(seed)
        self.folds = generate_walk_forward_folds(train_df, wf_cfg)
        self.min_trades = self.cfg.min_trades_per_year

    def run(self) -> GAResult:
        candidates: list[CandidateResult] = []
        log: list[dict[str, Any]] = []

        # Phase 1: broad search — each family represented
        per_family = max(self.cfg.trials // len(FAMILIES), 30)
        for family in FAMILIES:
            for _ in range(per_family):
                params = random_expert_params(self.rng, family=family)
                cand = self._evaluate(params)
                candidates.append(cand)

        candidates.sort(key=lambda c: c.fitness, reverse=True)
        log.append({
            "phase": "broad_search",
            "trials": len(candidates),
            "best_fitness": candidates[0].fitness if candidates else -1,
            "best_wr": candidates[0].train_metrics.get("win_rate", 0) if candidates else 0,
        })

        # Phase 2: refine top experts
        pool = self._dedupe(candidates)[: self.cfg.refine_top]
        refined: list[CandidateResult] = list(pool)
        for base in pool:
            parent_params = base.wf_summary.get("expert_params")
            if parent_params is None:
                continue
            from systemtrain.strategy.expert import ExpertParams
            fam = parent_params["family"]
            extra = {k: v for k, v in parent_params.items()
                     if k not in ("family", "session_start", "session_end", "cooldown_bars",
                                  "max_trades_per_day", "sl_atr_mult", "atr_period", "direction")}
            p = ExpertParams(
                family=fam,
                session_start=parent_params.get("session_start", 8),
                session_end=parent_params.get("session_end", 17),
                cooldown_bars=parent_params.get("cooldown_bars", 6),
                max_trades_per_day=parent_params.get("max_trades_per_day", 3),
                sl_atr_mult=parent_params.get("sl_atr_mult", 1.3),
                atr_period=parent_params.get("atr_period", 14),
                direction=parent_params.get("direction", "both"),
                extra=extra,
            )
            n_refine = max(self.cfg.refine_trials // max(len(pool), 1), 5)
            for _ in range(n_refine):
                mutant = mutate_expert_params(p, self.rng)
                refined.append(self._evaluate(mutant))

        refined.sort(key=lambda c: c.fitness, reverse=True)
        # Keep only candidates with enough trades (avoid 5-trade 60% WR overfit)
        min_keep = max(self.min_trades // 2, 30)
        viable = [c for c in refined if c.train_metrics.get("trade_count", 0) >= min_keep]
        pool_list = viable if viable else refined
        unique = self._dedupe(pool_list)[: self.cfg.top_k]

        log.append({
            "phase": "refine",
            "best_fitness": unique[0].fitness if unique else -1,
            "best_wr": unique[0].train_metrics.get("win_rate", 0) if unique else 0,
        })

        return GAResult(best_candidates=unique, generation_log=log)

    def _evaluate(self, params) -> CandidateResult:
        from systemtrain.strategy.expert import ExpertParams

        if not isinstance(params, ExpertParams):
            params = params
        gene = build_gene(params)
        score, metrics = evaluate_strategy(
            self.engine, gene, self.train_df, self.fitness_cfg, self.min_trades
        )
        wf = self._walk_forward(gene)
        wf_wr = wf.get("avg_win_rate", 0)
        wf_pass = wf.get("folds_passed", 0)
        wf_total = max(wf.get("folds_total", 1), 1)
        trades = metrics.get("trade_count", 0)

        blended = score
        if trades >= self.min_trades and not metrics.get("halted"):
            blended = score * 0.35 + wf_wr * 6.0 + (wf_pass / wf_total) * 4.0
            if metrics.get("win_rate", 0) >= self.fitness_cfg.get("min_win_rate", 0.6):
                blended += 8.0
            if metrics.get("profit_factor", 0) >= 1.3:
                blended += 3.0
        elif trades < self.min_trades:
            blended = score - (1.0 - trades / max(self.min_trades, 1)) * 5.0

        if metrics.get("halted"):
            blended -= 4.0

        wf["expert_params"] = params.to_dict()
        return CandidateResult(
            gene=gene,
            fitness=blended,
            train_metrics=metrics,
            wf_summary=wf,
        )

    def _walk_forward(self, gene) -> dict[str, Any]:
        if not self.folds:
            return {"folds_passed": 0, "folds_total": 0}
        fold_results = []
        min_trades_fold = max(15, self.min_trades // 5)
        for fold in self.folds:
            test_df = slice_fold(self.train_df, fold, "test")
            if len(test_df) < 100:
                continue
            result = self.engine.run(test_df, gene)
            from systemtrain.backtest.metrics import compute_metrics
            metrics = compute_metrics(result)
            passed = passes_train_constraints(
                metrics,
                {**self.fitness_cfg, "min_win_rate": 0.52, "min_monthly_stability": 0.4},
                min_trades_fold,
            )
            metrics["passed"] = passed
            fold_results.append(metrics)
        return aggregate_walk_forward_results(fold_results)

    def _dedupe(self, candidates: list[CandidateResult]) -> list[CandidateResult]:
        seen: set[str] = set()
        out: list[CandidateResult] = []
        for c in candidates:
            key = str(c.gene.to_dict())
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out
