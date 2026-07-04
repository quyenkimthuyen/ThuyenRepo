"""Mine setups by real backtest on train — learns what actually works, not theory."""

from __future__ import annotations

import random
from typing import Any

import numpy as np

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.learn.features import FEATURE_COLUMNS
from systemtrain.learn.setup_miner import LearnedSetup, MinedRule, mine_setups
from systemtrain.optimize.models import CandidateResult, GAResult
from systemtrain.optimize.refine_setup import refine_learned_candidates
from systemtrain.optimize.walk_forward import (
    aggregate_walk_forward_results,
    generate_walk_forward_folds,
    slice_fold,
)
from systemtrain.optimize.scoring import combined_robust_score, holdout_metrics, robust_fitness_score
from systemtrain.strategy.learned import learned_to_gene


def _random_learned_setup(rng: random.Random, direction: str = "both") -> LearnedSetup:
    """Generate creative random setup from feature space."""
    feat = rng.choice(FEATURE_COLUMNS)
    pct = rng.uniform(0.05, 0.95)
    op = rng.choice(("lt", "gt", "lte", "gte"))

    setup = LearnedSetup(
        direction=direction,
        session_start=rng.randint(7, 10),
        session_end=rng.randint(15, 19),
        cooldown_bars=rng.randint(2, 6),
        max_trades_per_day=rng.randint(3, 5),
        sl_atr_mult=round(rng.uniform(1.0, 1.6), 2),
        atr_period=rng.choice([10, 14]),
    )
    rule = MinedRule(feat, op, pct, "long" if "long" in direction else "short", 0, 0, 0)
    if direction in ("long_only", "both"):
        setup.long_rules = [rule]
    if direction in ("short_only", "both"):
        setup.short_rules = [MinedRule(feat, op, pct, "short", 0, 0, 0)]
    return setup


def _scale_thresholds(setup: LearnedSetup, df, rng: random.Random) -> LearnedSetup:
    """Convert percentile placeholders to real thresholds from train distribution."""
    import copy
    s = copy.deepcopy(setup)
    for rules in (s.long_rules, s.short_rules):
        for r in rules:
            if r.feature not in df.columns:
                continue
            series = df[r.feature].dropna()
            if len(series) < 50:
                continue
            if 0 < r.threshold < 1:
                r.threshold = float(np.percentile(series, r.threshold * 100))
    return s


def _regime_creative_setups() -> list[LearnedSetup]:
    """Pre-built regime-aware patterns (trend pullback, range MR, breakout)."""
    return [
        LearnedSetup(
            long_rules=[
                MinedRule("__feat_trend_long", "gte", 0.5, "long", 0, 0, 0),
                MinedRule("__feat_pullback_long", "gte", 0.5, "long", 0, 0, 0),
            ],
            direction="long_only",
            sl_atr_mult=1.15,
        ),
        LearnedSetup(
            short_rules=[
                MinedRule("__feat_trend_short", "gte", 0.5, "short", 0, 0, 0),
                MinedRule("__feat_pullback_short", "gte", 0.5, "short", 0, 0, 0),
            ],
            direction="short_only",
            sl_atr_mult=1.15,
        ),
        LearnedSetup(
            long_rules=[MinedRule("__feat_mr_long", "gte", 0.5, "long", 0, 0, 0)],
            direction="long_only",
            htf_long_filter=[],
            sl_atr_mult=1.1,
        ),
        LearnedSetup(
            short_rules=[MinedRule("__feat_mr_short", "gte", 0.5, "short", 0, 0, 0)],
            direction="short_only",
            htf_short_filter=[],
            sl_atr_mult=1.1,
        ),
        LearnedSetup(
            long_rules=[
                MinedRule("__feat_breakout_long", "gte", 0.5, "long", 0, 0, 0),
                MinedRule("__feat_london", "gte", 0.5, "long", 0, 0, 0),
            ],
            direction="long_only",
            sl_atr_mult=1.25,
        ),
        LearnedSetup(
            short_rules=[
                MinedRule("__feat_breakout_short", "gte", 0.5, "short", 0, 0, 0),
            ],
            direction="short_only",
            sl_atr_mult=1.25,
        ),
        LearnedSetup(
            long_rules=[MinedRule("__feat_rsi_spread", "lt", -5.0, "long", 0, 0, 0)],
            direction="long_only",
        ),
        LearnedSetup(
            short_rules=[MinedRule("__feat_rsi_spread", "gt", 5.0, "short", 0, 0, 0)],
            direction="short_only",
        ),
        LearnedSetup(
            long_rules=[
                MinedRule("__feat_pullback_long", "gte", 0.5, "long", 0, 0, 0),
                MinedRule("__feat_london", "gte", 0.5, "long", 0, 0, 0),
            ],
            direction="long_only",
            sl_atr_mult=1.2,
        ),
        LearnedSetup(
            short_rules=[
                MinedRule("__feat_pullback_short", "gte", 0.5, "short", 0, 0, 0),
            ],
            direction="short_only",
            sl_atr_mult=1.2,
        ),
    ]


class BacktestMiner:
    """Discover setups via simulation on train history + 4H filter."""

    def __init__(
        self,
        engine: BacktestEngine,
        train_df,
        fitness_cfg: dict,
        wf_cfg,
        top_k: int = 3,
        random_trials: int = 200,
        seed: int = 42,
    ):
        self.engine = engine
        self.train_df = train_df
        self.fitness_cfg = fitness_cfg
        self.wf_cfg = wf_cfg
        self.top_k = top_k
        self.random_trials = random_trials
        self.rng = random.Random(seed)
        self.folds = generate_walk_forward_folds(train_df, wf_cfg)

    def run(self) -> GAResult:
        print("  [Learn] Phase 1: label-based mining + decision trees...")
        label_setups = mine_setups(
            self.train_df, min_samples=25, min_win_rate=0.38, min_lift=0.03, max_setups=40
        )

        print(f"  [Learn] Phase 2: backtest {self.random_trials} creative setups on train...")
        all_setups = list(label_setups)
        for _ in range(self.random_trials):
            d = self.rng.choice(["long_only", "short_only", "both"])
            all_setups.append(
                _scale_thresholds(_random_learned_setup(self.rng, d), self.train_df, self.rng)
            )
        all_setups.extend(_regime_creative_setups())

        scored: list[tuple[float, dict, LearnedSetup, dict]] = []
        for setup in all_setups:
            setup = _scale_thresholds(setup, self.train_df, self.rng)
            gene = learned_to_gene(setup)
            result = self.engine.run(self.train_df, gene)
            m = compute_metrics(result)
            if m.get("trade_count", 0) < 25:
                continue
            wf = self._walk_forward(gene)
            holdout = holdout_metrics(self.engine, self.train_df, gene)
            score = combined_robust_score(m, wf, holdout)
            scored.append((score, m, setup, wf, holdout))

        scored.sort(key=lambda x: x[0], reverse=True)
        print(f"  [Learn] Phase 2 viable: {len(scored)} setups (≥25 trades)")

        # Phase 3: refine top candidates locally
        prelim: list[CandidateResult] = []
        seen: set[str] = set()
        for score, m, setup, wf, holdout in scored[: max(self.top_k * 4, 20)]:
            key = str(setup.to_dict())
            if key in seen:
                continue
            seen.add(key)
            setup.source_wr = m.get("win_rate", 0)
            setup.source_samples = m.get("trade_count", 0)
            gene = learned_to_gene(setup)
            wf["learned_setup"] = setup.to_dict()
            wf["holdout"] = holdout
            prelim.append(CandidateResult(gene=gene, fitness=score, train_metrics=m, wf_summary=wf))

        if prelim:
            print(f"  [Learn] Phase 3: refine top {min(15, len(prelim))} setups...")
            refined = refine_learned_candidates(
                self.engine, self.train_df, prelim, self.wf_cfg, rounds=8, seed=self.rng.randint(0, 9999)
            )
            results = refined[: self.top_k]
        else:
            results = []

        if results:
            b = results[0]
            wf = b.wf_summary
            print(
                f"  [Learn] Best robust: train_WR={b.train_metrics.get('win_rate', 0):.1%} "
                f"WF_WR={wf.get('avg_win_rate', 0):.1%} "
                f"WF_PF={wf.get('avg_profit_factor', 0):.2f} "
                f"trades={b.train_metrics.get('trade_count', 0)}"
            )

        return GAResult(
            best_candidates=results,
            generation_log=[{"phase": "backtest_mine", "viable": len(scored), "refined": len(prelim)}],
        )

    def _walk_forward(self, gene) -> dict[str, Any]:
        if not self.folds:
            return {"folds_passed": 0, "folds_total": 0}
        fold_results = []
        for fold in self.folds:
            test_df = slice_fold(self.train_df, fold, "test")
            if len(test_df) < 80:
                continue
            result = self.engine.run(test_df, gene)
            metrics = compute_metrics(result)
            fold_results.append(metrics)
        return aggregate_walk_forward_results(fold_results)
