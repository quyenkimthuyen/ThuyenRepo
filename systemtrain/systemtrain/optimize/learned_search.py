"""Optimize data-mined setups discovered from train history."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.learn.setup_miner import mine_setups
from systemtrain.optimize.fitness import evaluate_strategy, passes_train_constraints
from systemtrain.optimize.models import CandidateResult, GAResult
from systemtrain.optimize.walk_forward import (
    aggregate_walk_forward_results,
    generate_walk_forward_folds,
    slice_fold,
)
from systemtrain.strategy.learned import learned_to_gene


@dataclass
class LearnedSearchConfig:
    min_samples: int = 35
    min_mined_wr: float = 0.58
    max_setups: int = 50
    top_k: int = 3
    min_trades_per_year: int = 50


class LearnedSearchOptimizer:
    """
    1. Mine setups from 1-year train history (features + 1H filter + labels)
    2. Backtest + walk-forward each discovered setup
    3. Rank by robustness, not textbook templates
    """

    def __init__(
        self,
        engine: BacktestEngine,
        train_df: pd.DataFrame,
        fitness_cfg: dict,
        wf_cfg,
        search_cfg: LearnedSearchConfig | None = None,
        output_dir: Path | None = None,
        seed: int = 42,
    ):
        self.engine = engine
        self.train_df = train_df
        self.fitness_cfg = fitness_cfg
        self.wf_cfg = wf_cfg
        self.cfg = search_cfg or LearnedSearchConfig()
        self.output_dir = output_dir or Path("output")
        self.seed = seed
        self.folds = generate_walk_forward_folds(train_df, wf_cfg)

    def run(self) -> GAResult:
        print("  [Learn] Mining setups from train history (1H filter + feature search)...")
        setups = mine_setups(
            self.train_df,
            min_samples=self.cfg.min_samples,
            min_win_rate=self.cfg.min_mined_wr,
            min_lift=0.08,
            max_setups=self.cfg.max_setups,
            seed=self.seed,
        )
        print(f"  [Learn] Discovered {len(setups)} candidate setups")

        mined_report = [s.to_dict() for s in setups[:20]]
        report_path = self.output_dir / "mined_setups.json"
        report_path.parent.mkdir(exist_ok=True)
        with report_path.open("w") as f:
            json.dump(mined_report, f, indent=2)
        print(f"  [Learn] Mined rules saved: {report_path}")

        candidates: list[CandidateResult] = []
        for setup in setups:
            gene = learned_to_gene(setup)
            score, metrics = evaluate_strategy(
                self.engine, gene, self.train_df, self.fitness_cfg, self.cfg.min_trades_per_year
            )
            wf = self._walk_forward(gene)
            wf_wr = wf.get("avg_win_rate", 0)
            trades = metrics.get("trade_count", 0)

            blended = score
            if trades >= self.cfg.min_trades_per_year // 2:
                blended = (
                    score * 0.3
                    + wf_wr * 7.0
                    + setup.source_wr * 5.0
                    + min(trades / 100, 1.0) * 3.0
                )
                if metrics.get("win_rate", 0) >= 0.55:
                    blended += 5.0
            if metrics.get("halted"):
                blended -= 3.0

            wf["learned_setup"] = setup.to_dict()
            wf["mined_wr"] = setup.source_wr
            wf["mined_samples"] = setup.source_samples
            candidates.append(
                CandidateResult(gene=gene, fitness=blended, train_metrics=metrics, wf_summary=wf)
            )

        candidates.sort(key=lambda c: c.fitness, reverse=True)
        unique = self._dedupe(candidates)[: self.cfg.top_k]

        if unique:
            best = unique[0]
            print(
                f"  [Learn] Best: mined_WR={best.wf_summary.get('mined_wr', 0):.1%} "
                f"train_WR={best.train_metrics.get('win_rate', 0):.1%} "
                f"trades={best.train_metrics.get('trade_count', 0)}"
            )

        return GAResult(
            best_candidates=unique,
            generation_log=[{"phase": "setup_mining", "discovered": len(setups), "kept": len(unique)}],
        )

    def _walk_forward(self, gene) -> dict[str, Any]:
        if not self.folds:
            return {"folds_passed": 0, "folds_total": 0}
        fold_results = []
        min_trades_fold = max(15, self.cfg.min_trades_per_year // 5)
        for fold in self.folds:
            test_df = slice_fold(self.train_df, fold, "test")
            if len(test_df) < 100:
                continue
            result = self.engine.run(test_df, gene)
            from systemtrain.backtest.metrics import compute_metrics
            metrics = compute_metrics(result)
            passed = passes_train_constraints(
                metrics,
                {**self.fitness_cfg, "min_win_rate": 0.52, "min_monthly_stability": 0.35},
                min_trades_fold,
            )
            metrics["passed"] = passed
            fold_results.append(metrics)
        return aggregate_walk_forward_results(fold_results)

    def _dedupe(self, candidates: list[CandidateResult]) -> list[CandidateResult]:
        seen: set[str] = set()
        out: list[CandidateResult] = []
        for c in candidates:
            key = str(c.gene.learned_setup)
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out
