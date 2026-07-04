"""Proven strategy templates as GA seeds — mean reversion & trend pullback."""

from __future__ import annotations

import random

from systemtrain.strategy.dsl import ConditionNode, LogicNode, StrategyGene, mutate_gene


def _cond(left: dict, op: str, right, is_ind: bool = False) -> ConditionNode:
    return ConditionNode(left=left, op=op, right=right, right_is_indicator=is_ind)


def template_mean_reversion(rsi_lo: float = 32, rsi_hi: float = 68, adx_max: float = 28) -> StrategyGene:
    long_entry = LogicNode(
        "and",
        [
            _cond({"name": "rsi", "period": 14}, "lt", rsi_lo),
            _cond({"name": "close"}, "lt", {"name": "bb_lower", "period": 20, "std_mult": 2.0}, True),
            _cond({"name": "adx", "period": 14}, "lt", adx_max),
        ],
    )
    short_entry = LogicNode(
        "and",
        [
            _cond({"name": "rsi", "period": 14}, "gt", rsi_hi),
            _cond({"name": "close"}, "gt", {"name": "bb_upper", "period": 20, "std_mult": 2.0}, True),
            _cond({"name": "adx", "period": 14}, "lt", adx_max),
        ],
    )
    return StrategyGene(
        long_entry=long_entry,
        short_entry=short_entry,
        direction="both",
        session_start=7,
        session_end=18,
        cooldown_bars=6,
        max_trades_per_day=3,
        sl_atr_mult=1.2,
        atr_period=14,
    )


def template_trend_pullback() -> StrategyGene:
    long_entry = LogicNode(
        "and",
        [
            _cond({"name": "close"}, "gt", {"name": "ema", "period": 50}, True),
            _cond({"name": "rsi", "period": 14}, "lt", 40),
            _cond({"name": "rsi", "period": 14}, "gt", 28),
            _cond({"name": "macd_hist", "fast": 12, "slow": 26, "signal": 9}, "gt", 0),
        ],
    )
    short_entry = LogicNode(
        "and",
        [
            _cond({"name": "close"}, "lt", {"name": "ema", "period": 50}, True),
            _cond({"name": "rsi", "period": 14}, "gt", 60),
            _cond({"name": "rsi", "period": 14}, "lt", 72),
            _cond({"name": "macd_hist", "fast": 12, "slow": 26, "signal": 9}, "lt", 0),
        ],
    )
    return StrategyGene(
        long_entry=long_entry,
        short_entry=short_entry,
        direction="both",
        session_start=8,
        session_end=17,
        cooldown_bars=5,
        max_trades_per_day=3,
        sl_atr_mult=1.4,
        atr_period=14,
    )


def template_stoch_reversal() -> StrategyGene:
    long_entry = LogicNode(
        "and",
        [
            _cond({"name": "stoch_k", "k_period": 14, "d_period": 3}, "lt", 22),
            _cond({"name": "stoch_k", "k_period": 14, "d_period": 3}, "cross_above",
                  {"name": "stoch_d", "k_period": 14, "d_period": 3}, True),
            _cond({"name": "close"}, "gt", {"name": "sma", "period": 20}, True),
        ],
    )
    short_entry = LogicNode(
        "and",
        [
            _cond({"name": "stoch_k", "k_period": 14, "d_period": 3}, "gt", 78),
            _cond({"name": "stoch_k", "k_period": 14, "d_period": 3}, "cross_below",
                  {"name": "stoch_d", "k_period": 14, "d_period": 3}, True),
            _cond({"name": "close"}, "lt", {"name": "sma", "period": 20}, True),
        ],
    )
    return StrategyGene(
        long_entry=long_entry,
        short_entry=short_entry,
        direction="both",
        session_start=7,
        session_end=18,
        cooldown_bars=4,
        max_trades_per_day=4,
        sl_atr_mult=1.3,
        atr_period=14,
    )


def template_rsi_divergence_style() -> StrategyGene:
    long_entry = LogicNode(
        "and",
        [
            _cond({"name": "rsi", "period": 14}, "lt", 35),
            _cond({"name": "close"}, "lt", {"name": "ema", "period": 20}, True),
            _cond({"name": "adx", "period": 14}, "gt", 18),
        ],
    )
    short_entry = LogicNode(
        "and",
        [
            _cond({"name": "rsi", "period": 14}, "gt", 65),
            _cond({"name": "close"}, "gt", {"name": "ema", "period": 20}, True),
            _cond({"name": "adx", "period": 14}, "gt", 18),
        ],
    )
    return StrategyGene(
        long_entry=long_entry,
        short_entry=short_entry,
        direction="both",
        session_start=7,
        session_end=19,
        cooldown_bars=5,
        max_trades_per_day=3,
        sl_atr_mult=1.25,
        atr_period=14,
    )


ALL_TEMPLATES = [
    template_mean_reversion,
    template_trend_pullback,
    template_stoch_reversal,
    template_rsi_divergence_style,
]


def seeded_population(size: int, rng: random.Random) -> list[StrategyGene]:
    """Mix strategy templates (with light mutation) and random genes."""
    genes: list[StrategyGene] = []
    for factory in ALL_TEMPLATES:
        base = factory()
        genes.append(base)
        genes.append(mutate_gene(base, 0.2, rng))
        genes.append(mutate_gene(base, 0.35, rng))

    from systemtrain.strategy.dsl import random_gene

    while len(genes) < size:
        if rng.random() < 0.4 and ALL_TEMPLATES:
            base = rng.choice(ALL_TEMPLATES)()
            genes.append(mutate_gene(base, 0.25, rng))
        else:
            genes.append(random_gene(rng))
    return genes[:size]
