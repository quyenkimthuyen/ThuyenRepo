"""Win-rate focused optimizer — target WR >= 60% with RR>=2 fixed."""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.learn.features import FEATURE_COLUMNS
from systemtrain.learn.setup_miner import (
    LearnedSetup,
    MinedRule,
    _combine_wr,
    _eval_htf_filters,
    _mutate_setup,
    _rule_to_setup,
    _score_rules,
    mine_setups,
)
from systemtrain.learn.labels import compute_trade_labels
from systemtrain.learn.features import HTF_LONG_FILTERS, HTF_SHORT_FILTERS
from systemtrain.optimize.models import CandidateResult
from systemtrain.optimize.scoring import holdout_metrics
from systemtrain.optimize.walk_forward import (
    aggregate_walk_forward_results,
    generate_walk_forward_folds,
    slice_fold,
)
from systemtrain.strategy.learned import learned_to_gene


@dataclass
class WRSearchResult:
    gene: Any
    setup: LearnedSetup
    train_metrics: dict[str, Any]
    holdout_metrics: dict[str, Any]
    oos_metrics: dict[str, Any]
    wf_summary: dict[str, Any]
    train_wr: float
    holdout_wr: float
    oos_wr: float


def wr_fitness(
    metrics: dict[str, Any],
    holdout: dict[str, Any] | None = None,
    target_wr: float = 0.60,
    min_trades: int = 20,
) -> float:
    wr = metrics.get("win_rate", 0)
    trades = metrics.get("trade_count", 0)
    pf = metrics.get("profit_factor", 0)
    if trades < min_trades:
        return -8.0 + (trades / min_trades) * 5.0 + wr * 5.0
    score = wr * 15.0 + min(pf, 3.0) * 4.0
    if wr >= target_wr:
        score += 12.0
    else:
        score -= (target_wr - wr) * 25.0
    if holdout and holdout.get("trade_count", 0) >= 6:
        hwr = holdout.get("win_rate", 0)
        score += hwr * 20.0
        if hwr >= target_wr:
            score += 15.0
        else:
            score -= (target_wr - hwr) * 30.0
    if metrics.get("halted"):
        score -= 5.0
    return float(score)


def _mine_high_wr_rules(
    train_df: pd.DataFrame,
    min_samples: int = 12,
    min_wr: float = 0.52,
) -> list[MinedRule]:
    long_lab, short_lab = compute_trade_labels(train_df)
    long_lab.name = "long"
    short_lab.name = "short"
    htf_long = _eval_htf_filters(train_df, HTF_LONG_FILTERS)
    htf_short = _eval_htf_filters(train_df, HTF_SHORT_FILTERS)
    rules: list[MinedRule] = []

    for feat in FEATURE_COLUMNS:
        if feat not in train_df.columns:
            continue
        series = train_df[feat].dropna()
        if len(series) < min_samples * 3:
            continue
        for pct in range(5, 96, 2):
            thresh = float(np.percentile(series, pct))
            for op in ("lt", "gt", "lte", "gte"):
                for labels, htf_mask in ((long_lab, htf_long), (short_lab, htf_short)):
                    rule = _score_rules(train_df, labels, feat, op, thresh, htf_mask, min_samples)
                    if rule and rule.win_rate >= min_wr:
                        rules.append(rule)
    rules.sort(key=lambda r: (r.win_rate, r.samples), reverse=True)
    return rules[:60]


def _build_setups_from_rules(rules: list[MinedRule], max_setups: int = 200) -> list[LearnedSetup]:
    setups: list[LearnedSetup] = []
    long_r = [r for r in rules if r.direction == "long"]
    short_r = [r for r in rules if r.direction == "short"]

    for r in long_r[:25]:
        setups.append(_rule_to_setup([r], "long"))
        s = _rule_to_setup([r], "long")
        s.direction = "long_only"
        setups.append(s)

    for r in short_r[:25]:
        setups.append(_rule_to_setup([r], "short"))
        s = _rule_to_setup([r], "short")
        s.direction = "short_only"
        setups.append(s)

    for i, r1 in enumerate(long_r[:12]):
        for r2 in long_r[i + 1 : i + 8]:
            if r1.feature == r2.feature:
                continue
            setups.append(_rule_to_setup([r1, r2], "long"))
        for r2 in long_r[i + 1 : i + 5]:
            for r3 in long_r[i + 2 : i + 4]:
                if len({r1.feature, r2.feature, r3.feature}) < 3:
                    continue
                setups.append(_rule_to_setup([r1, r2, r3], "long"))

    for i, r1 in enumerate(short_r[:12]):
        for r2 in short_r[i + 1 : i + 8]:
            if r1.feature == r2.feature:
                continue
            setups.append(_rule_to_setup([r1, r2], "short"))
        for r2 in short_r[i + 1 : i + 5]:
            for r3 in short_r[i + 2 : i + 4]:
                if len({r1.feature, r2.feature, r3.feature}) < 3:
                    continue
                setups.append(_rule_to_setup([r1, r2, r3], "short"))

    # Precision templates
    templates = [
        LearnedSetup(
            long_rules=[
                MinedRule("__feat_pullback_long", "gte", 0.5, "long", 0, 0, 0),
                MinedRule("__feat_london", "gte", 0.5, "long", 0, 0, 0),
            ],
            direction="long_only", sl_atr_mult=1.0, cooldown_bars=6, max_trades_per_day=2,
        ),
        LearnedSetup(
            short_rules=[
                MinedRule("__feat_pullback_short", "gte", 0.5, "short", 0, 0, 0),
                MinedRule("__feat_ny", "gte", 0.5, "short", 0, 0, 0),
            ],
            direction="short_only", sl_atr_mult=1.0, cooldown_bars=6, max_trades_per_day=2,
        ),
        LearnedSetup(
            short_rules=[MinedRule("__feat_mr_short", "gte", 0.5, "short", 0, 0, 0)],
            direction="short_only",
            htf_short_filter=[("__htf_adx", "lt", 20.0)],
            sl_atr_mult=0.95, cooldown_bars=8, max_trades_per_day=2,
        ),
        LearnedSetup(
            long_rules=[MinedRule("__feat_mr_long", "gte", 0.5, "long", 0, 0, 0)],
            direction="long_only",
            htf_long_filter=[("__htf_adx", "lt", 20.0)],
            sl_atr_mult=0.95, cooldown_bars=8, max_trades_per_day=2,
        ),
    ]
    setups.extend(templates)

    seen: set[str] = set()
    unique: list[LearnedSetup] = []
    for s in setups:
        key = str(s.to_dict())
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)
        if len(unique) >= max_setups:
            break
    return unique


def _walk_forward(engine, train_df, gene, wf_cfg) -> dict[str, Any]:
    folds = generate_walk_forward_folds(train_df, wf_cfg)
    fold_results = []
    for fold in folds:
        test_df = slice_fold(train_df, fold, "test")
        if len(test_df) < 60:
            continue
        fold_results.append(compute_metrics(engine.run(test_df, gene)))
    return aggregate_walk_forward_results(fold_results)


def search_high_wr_strategy(
    engine: BacktestEngine,
    train_df: pd.DataFrame,
    oos_df: pd.DataFrame,
    wf_cfg,
    target_wr: float = 0.60,
    seed_setup: LearnedSetup | None = None,
    seed: int = 42,
) -> WRSearchResult | None:
    rng = random.Random(seed)
    print("  [WR] Phase 1: mine high-WR label rules...")
    hi_rules = _mine_high_wr_rules(train_df, min_samples=10, min_wr=0.50)
    print(f"  [WR] Found {len(hi_rules)} rules with label WR>=50%")

    print("  [WR] Phase 2: label mining + tree setups...")
    label_setups = mine_setups(
        train_df, min_samples=12, min_win_rate=0.50, min_lift=0.05, max_setups=50
    )

    print("  [WR] Phase 3: build combo setups + backtest on train...")
    combos = _build_setups_from_rules(hi_rules)
    all_setups = combos + label_setups

    if seed_setup:
        all_setups.insert(0, copy.deepcopy(seed_setup))
        for _ in range(30):
            all_setups.append(_mutate_setup(seed_setup, rng))

    # Session / SL grid on top candidates placeholder — tested via mutate
    scored: list[tuple[float, LearnedSetup, dict, dict]] = []
    sl_values = [0.85, 0.95, 1.05, 1.15, 1.25]
    cooldown_values = [4, 6, 8, 10]
    session_windows = [(7, 12), (8, 16), (9, 15), (12, 18)]

    for setup in all_setups:
        for sl_mult in sl_values:
            for cooldown in cooldown_values:
                for sess_start, sess_end in session_windows:
                    s = copy.deepcopy(setup)
                    s.sl_atr_mult = sl_mult
                    s.cooldown_bars = cooldown
                    s.session_start = sess_start
                    s.session_end = sess_end
                    s.max_trades_per_day = min(s.max_trades_per_day, 3)
                    gene = learned_to_gene(s)
                    m = compute_metrics(engine.run(train_df, gene))
                    if m.get("trade_count", 0) < 12:
                        continue
                    h = holdout_metrics(engine, train_df, gene)
                    score = wr_fitness(m, h, target_wr, min_trades=15)
                    scored.append((score, s, m, h))

    if not scored:
        print("  [WR] No viable setups found")
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_setup, train_m, holdout_m = scored[0]

    # Phase 4: local refine top 8 by holdout WR (not train)
    print("  [WR] Phase 4: refine top setups for WR...")
    def _holdout_key(x):
        h = x[3] or {}
        return (h.get("win_rate", 0), h.get("trade_count", 0), x[2].get("win_rate", 0))

    top_setups = [x[1] for x in sorted(scored, key=_holdout_key, reverse=True)[:8]]
    best_score, best_setup, train_m, holdout_m = scored[0]
    for setup in top_setups:
        for _ in range(60):
            mutant = _mutate_setup(setup, rng)
            mutant.max_trades_per_day = min(mutant.max_trades_per_day, 3)
            gene = learned_to_gene(mutant)
            m = compute_metrics(engine.run(train_df, gene))
            if m.get("trade_count", 0) < 12:
                continue
            h = holdout_metrics(engine, train_df, gene)
            score = wr_fitness(m, h, target_wr, min_trades=15)
            if score > best_score:
                best_score, best_setup, train_m, holdout_m = score, mutant, m, h

    gene = learned_to_gene(best_setup)
    wf = _walk_forward(engine, train_df, gene, wf_cfg)
    oos_m = compute_metrics(engine.run(oos_df, gene))

    print(
        f"  [WR] Best: train_WR={train_m.get('win_rate', 0):.1%} "
        f"holdout_WR={(holdout_m or {}).get('win_rate', 0):.1%} "
        f"OOS_WR={oos_m.get('win_rate', 0):.1%} trades={oos_m.get('trade_count', 0)}"
    )

    return WRSearchResult(
        gene=gene,
        setup=best_setup,
        train_metrics=train_m,
        holdout_metrics=holdout_m or {},
        oos_metrics=oos_m,
        wf_summary=wf,
        train_wr=train_m.get("win_rate", 0),
        holdout_wr=(holdout_m or {}).get("win_rate", 0),
        oos_wr=oos_m.get("win_rate", 0),
    )
