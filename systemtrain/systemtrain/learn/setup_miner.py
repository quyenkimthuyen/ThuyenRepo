"""
Mine profitable setups from 1-year history — data-driven, not template-driven.

Process:
1. Build feature matrix + triple-barrier labels on TRAIN only
2. Search single rules & pairs that maximize win rate with min samples
3. Enforce 1H alignment filter on discovered setups
4. Convert to executable LearnedSetup strategies
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.learn.features import FEATURE_COLUMNS, HTF_LONG_FILTERS, HTF_SHORT_FILTERS
from systemtrain.learn.labels import compute_trade_labels
from systemtrain.learn.regime import regime_range_mask, regime_trend_mask


@dataclass
class MinedRule:
    feature: str
    op: str  # lt, gt, lte, gte
    threshold: float
    direction: str  # long, short
    win_rate: float
    samples: int
    expectancy: float

    def to_dict(self) -> dict:
        return {
            "feature": self.feature,
            "op": self.op,
            "threshold": float(self.threshold),
            "direction": self.direction,
            "win_rate": float(self.win_rate),
            "samples": int(self.samples),
            "expectancy": float(self.expectancy),
        }


@dataclass
class LearnedSetup:
    """Strategy discovered from historical mining."""

    long_rules: list[MinedRule] = field(default_factory=list)
    short_rules: list[MinedRule] = field(default_factory=list)
    htf_long_filter: list[tuple[str, str, float]] = field(default_factory=lambda: list(HTF_LONG_FILTERS))
    htf_short_filter: list[tuple[str, str, float]] = field(default_factory=lambda: list(HTF_SHORT_FILTERS))
    session_start: int = 7
    session_end: int = 18
    cooldown_bars: int = 4
    max_trades_per_day: int = 4
    sl_atr_mult: float = 1.3
    atr_period: int = 14
    direction: str = "both"
    source_wr: float = 0.0
    source_samples: int = 0

    def to_dict(self) -> dict:
        return {
            "long_rules": [r.to_dict() for r in self.long_rules],
            "short_rules": [r.to_dict() for r in self.short_rules],
            "htf_long_filter": self.htf_long_filter,
            "htf_short_filter": self.htf_short_filter,
            "session_start": self.session_start,
            "session_end": self.session_end,
            "cooldown_bars": self.cooldown_bars,
            "max_trades_per_day": self.max_trades_per_day,
            "sl_atr_mult": self.sl_atr_mult,
            "atr_period": self.atr_period,
            "direction": self.direction,
            "source_wr": self.source_wr,
            "source_samples": self.source_samples,
        }


def _apply_op(series: pd.Series, op: str, thresh: float) -> pd.Series:
    if op == "lt":
        return series < thresh
    if op == "gt":
        return series > thresh
    if op == "lte":
        return series <= thresh
    if op == "gte":
        return series >= thresh
    return pd.Series(False, index=series.index)


def _eval_htf_filters(df: pd.DataFrame, filters: list[tuple[str, str, float]]) -> np.ndarray:
    mask = np.ones(len(df), dtype=bool)
    for feat, op, thresh in filters:
        if feat not in df.columns:
            return np.zeros(len(df), dtype=bool)
        mask &= _apply_op(df[feat], op, thresh).fillna(False).values
    return mask


def _score_rules(
    df: pd.DataFrame,
    labels: pd.Series,
    feature: str,
    op: str,
    thresh: float,
    htf_mask: np.ndarray,
    min_samples: int,
) -> MinedRule | None:
    if feature not in df.columns:
        return None
    cond = _apply_op(df[feature], op, thresh).fillna(False).values
    valid = cond & htf_mask & labels.notna().values
    n = valid.sum()
    if n < min_samples:
        return None
    wins = labels.values[valid].mean()
    exp = wins * 2.0 - (1.0 - wins) * 1.0
    direction = "long" if labels.name == "long" else "short"
    return MinedRule(feature, op, thresh, direction, float(wins), int(n), float(exp))


def mine_setups(
    train_df: pd.DataFrame,
    min_samples: int = 35,
    min_win_rate: float = 0.58,
    min_lift: float = 0.08,
    max_single_rules: int = 80,
    max_setups: int = 40,
    seed: int = 42,
) -> list[LearnedSetup]:
    """Discover setups from train history."""
    rng = random.Random(seed)
    long_lab, short_lab = compute_trade_labels(train_df)
    long_lab.name = "long"
    short_lab.name = "short"

    baseline_long = float(long_lab.dropna().mean()) if long_lab.notna().sum() else 0.32
    baseline_short = float(short_lab.dropna().mean()) if short_lab.notna().sum() else 0.32
    effective_min_wr = max(min_win_rate, baseline_long + min_lift, 0.42)

    htf_long = _eval_htf_filters(train_df, HTF_LONG_FILTERS)
    htf_short = _eval_htf_filters(train_df, HTF_SHORT_FILTERS)
    trend_mask = regime_trend_mask(train_df)
    range_mask = regime_range_mask(train_df)

    singles: list[MinedRule] = []

    for feat in FEATURE_COLUMNS:
        if feat not in train_df.columns:
            continue
        series = train_df[feat].dropna()
        if len(series) < min_samples * 2:
            continue
        for pct in range(5, 96, 3):
            thresh = float(np.percentile(series, pct))
            for op in ("lt", "gt", "lte", "gte"):
                for labels, htf_mask, base in (
                    (long_lab, htf_long, baseline_long),
                    (short_lab, htf_short, baseline_short),
                    (long_lab, trend_mask & htf_long, baseline_long),
                    (short_lab, trend_mask & htf_short, baseline_short),
                    (long_lab, range_mask, baseline_long),
                    (short_lab, range_mask, baseline_short),
                ):
                    rule = _score_rules(train_df, labels, feat, op, thresh, htf_mask, min_samples)
                    if rule and rule.win_rate >= max(effective_min_wr, base + min_lift * 0.8):
                        singles.append(rule)

    singles.sort(key=lambda r: (r.win_rate, r.samples, r.expectancy), reverse=True)
    singles = singles[:max_single_rules]

    setups: list[LearnedSetup] = []

    # Decision tree discovered setups (creative / non-obvious combos)
    from systemtrain.learn.rule_tree import mine_tree_rules
    tree_setups = mine_tree_rules(
        train_df, long_lab, short_lab, FEATURE_COLUMNS, htf_long, htf_short
    )
    setups.extend(tree_setups)

    # Pullback composites as fixed creative setups
    for feat, direction in (("__feat_pullback_long", "long"), ("__feat_pullback_short", "short")):
        if feat not in train_df.columns:
            continue
        labels = long_lab if direction == "long" else short_lab
        htf_m = htf_long if direction == "long" else htf_short
        rule = _score_rules(train_df, labels, feat, "gte", 0.5, htf_m, min_samples)
        if rule and rule.win_rate >= baseline_long + min_lift:
            setups.append(_rule_to_setup([rule], direction))

    # Single-rule setups
    for rule in singles[: max_setups // 2]:
        setup = _rule_to_setup([rule], rule.direction)
        setup.source_wr = rule.win_rate
        setup.source_samples = rule.samples
        setups.append(setup)

    # Pair combinations of top rules (same direction, different features)
    long_rules = [r for r in singles if r.direction == "long"][:15]
    short_rules = [r for r in singles if r.direction == "short"][:15]

    for i, r1 in enumerate(long_rules):
        for r2 in long_rules[i + 1 : i + 6]:
            if r1.feature == r2.feature:
                continue
            wr, n = _combine_wr(train_df, long_lab, [r1, r2], htf_long)
            if n >= min_samples and wr >= max(effective_min_wr, baseline_long + min_lift):
                setup = _rule_to_setup([r1, r2], "long")
                setup.source_wr = wr
                setup.source_samples = n
                setups.append(setup)

    for i, r1 in enumerate(short_rules):
        for r2 in short_rules[i + 1 : i + 6]:
            if r1.feature == r2.feature:
                continue
            wr, n = _combine_wr(train_df, short_lab, [r1, r2], htf_short)
            if n >= min_samples and wr >= max(effective_min_wr, baseline_short + min_lift):
                setup = _rule_to_setup([r1, r2], "short")
                setup.source_wr = wr
                setup.source_samples = n
                setups.append(setup)

    # Creative mutations: vary session, cooldown, sl_atr on best setups
    base = sorted(setups, key=lambda s: (s.source_wr, s.source_samples), reverse=True)[:10]
    for b in base:
        for _ in range(3):
            mutant = _mutate_setup(b, rng)
            setups.append(mutant)

    setups.sort(key=lambda s: (s.source_wr, s.source_samples), reverse=True)
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


def _combine_wr(
    df: pd.DataFrame,
    labels: pd.Series,
    rules: list[MinedRule],
    htf_mask: np.ndarray,
) -> tuple[float, int]:
    mask = htf_mask.copy()
    for r in rules:
        mask &= _apply_op(df[r.feature], r.op, r.threshold).fillna(False).values
    valid = mask & labels.notna().values
    n = valid.sum()
    if n == 0:
        return 0.0, 0
    return float(labels.values[valid].mean()), int(n)


def _rule_to_setup(rules: list[MinedRule], direction: str) -> LearnedSetup:
    if direction == "long":
        return LearnedSetup(
            long_rules=list(rules),
            short_rules=[],
            direction="long_only" if not any(r.direction == "short" for r in rules) else "both",
        )
    return LearnedSetup(
        long_rules=[],
        short_rules=list(rules),
        direction="short_only",
    )


def _mutate_setup(setup: LearnedSetup, rng: random.Random) -> LearnedSetup:
    import copy
    s = copy.deepcopy(setup)
    s.session_start = max(6, min(10, s.session_start + rng.randint(-1, 1)))
    s.session_end = max(15, min(20, s.session_end + rng.randint(-1, 1)))
    s.cooldown_bars = max(2, min(8, s.cooldown_bars + rng.randint(-2, 2)))
    s.sl_atr_mult = round(max(0.9, min(1.8, s.sl_atr_mult + rng.uniform(-0.15, 0.15))), 2)
    s.max_trades_per_day = max(2, min(5, s.max_trades_per_day + rng.randint(-1, 1)))
    return s


def generate_learned_signals(
    df: pd.DataFrame,
    setup: LearnedSetup,
) -> tuple[pd.Series, pd.Series]:
    """Execute a mined setup on feature-enriched dataframe."""
    n = len(df)
    long_raw = np.zeros(n, dtype=bool)
    short_raw = np.zeros(n, dtype=bool)

    if setup.long_rules:
        mask = _eval_htf_filters(df, setup.htf_long_filter)
        for rule in setup.long_rules:
            mask &= _apply_op(df[rule.feature], rule.op, rule.threshold).fillna(False).values
        long_raw = mask

    if setup.short_rules:
        mask = _eval_htf_filters(df, setup.htf_short_filter)
        for rule in setup.short_rules:
            mask &= _apply_op(df[rule.feature], rule.op, rule.threshold).fillna(False).values
        short_raw = mask

    from systemtrain.strategy.dsl import _apply_filters

    long_sig = _apply_filters(
        long_raw, df.index, setup.session_start, setup.session_end,
        setup.cooldown_bars, setup.max_trades_per_day,
    )
    short_sig = _apply_filters(
        short_raw, df.index, setup.session_start, setup.session_end,
        setup.cooldown_bars, setup.max_trades_per_day,
    )
    return pd.Series(long_sig, index=df.index), pd.Series(short_sig, index=df.index)
