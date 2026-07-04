"""
Expert parametric strategy families — optimize parameters, not random DSL trees.

Rationale (pro trading view):
- 15m EURUSD edge comes from regime-aware setups (trend pullback, range fade, session breakout)
- Random indicator trees overfit noise; parameterized families generalize better
- Fewer conditions + tunable thresholds = more stable OOS
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from systemtrain.strategy.dsl import ConditionNode, LogicNode, StrategyGene


def _c(left: dict, op: str, right, is_ind: bool = False) -> ConditionNode:
    return ConditionNode(left=left, op=op, right=right, right_is_indicator=is_ind)


def _and(*nodes: ConditionNode) -> LogicNode:
    return LogicNode("and", list(nodes))


@dataclass
class ExpertParams:
    family: str
    session_start: int = 8
    session_end: int = 17
    cooldown_bars: int = 6
    max_trades_per_day: int = 3
    sl_atr_mult: float = 1.3
    atr_period: int = 14
    direction: str = "both"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "session_start": self.session_start,
            "session_end": self.session_end,
            "cooldown_bars": self.cooldown_bars,
            "max_trades_per_day": self.max_trades_per_day,
            "sl_atr_mult": self.sl_atr_mult,
            "atr_period": self.atr_period,
            "direction": self.direction,
            **self.extra,
        }


def build_gene(params: ExpertParams) -> StrategyGene:
    f = params.family
    e = params.extra

    if f == "pullback_trend":
        ema_tr = e.get("ema_trend", 100)
        rsi_p = e.get("rsi_period", 14)
        rsi_lo = e.get("rsi_long_hi", 45)
        rsi_floor = e.get("rsi_long_lo", 30)
        adx_min = e.get("adx_min", 18)
        long_entry = _and(
            _c({"name": "close"}, "gt", {"name": "ema", "period": ema_tr}, True),
            _c({"name": "rsi", "period": rsi_p}, "lt", rsi_lo),
            _c({"name": "rsi", "period": rsi_p}, "gt", rsi_floor),
            _c({"name": "adx", "period": 14}, "gt", adx_min),
        )
        short_entry = _and(
            _c({"name": "close"}, "lt", {"name": "ema", "period": ema_tr}, True),
            _c({"name": "rsi", "period": rsi_p}, "gt", 100 - rsi_lo),
            _c({"name": "rsi", "period": rsi_p}, "lt", 100 - rsi_floor),
            _c({"name": "adx", "period": 14}, "gt", adx_min),
        )
    elif f == "range_rsi":
        rsi_p = e.get("rsi_period", 7)
        rsi_buy = e.get("rsi_buy", 28)
        rsi_sell = e.get("rsi_sell", 72)
        adx_max = e.get("adx_max", 25)
        long_entry = _and(
            _c({"name": "rsi", "period": rsi_p}, "lt", rsi_buy),
            _c({"name": "adx", "period": 14}, "lt", adx_max),
            _c({"name": "close"}, "lt", {"name": "bb_lower", "period": 20, "std_mult": 2.0}, True),
        )
        short_entry = _and(
            _c({"name": "rsi", "period": rsi_p}, "gt", rsi_sell),
            _c({"name": "adx", "period": 14}, "lt", adx_max),
            _c({"name": "close"}, "gt", {"name": "bb_upper", "period": 20, "std_mult": 2.0}, True),
        )
    elif f == "momentum_continuation":
        ema_f = e.get("ema_fast", 21)
        ema_s = e.get("ema_slow", 55)
        rsi_p = e.get("rsi_period", 14)
        long_entry = _and(
            _c({"name": "ema", "period": ema_f}, "gt", {"name": "ema", "period": ema_s}, True),
            _c({"name": "close"}, "gt", {"name": "ema", "period": ema_f}, True),
            _c({"name": "rsi", "period": rsi_p}, "gt", e.get("rsi_long_min", 52)),
            _c({"name": "rsi", "period": rsi_p}, "lt", e.get("rsi_long_max", 68)),
            _c({"name": "macd_hist", "fast": 12, "slow": 26, "signal": 9}, "gt", 0),
        )
        short_entry = _and(
            _c({"name": "ema", "period": ema_f}, "lt", {"name": "ema", "period": ema_s}, True),
            _c({"name": "close"}, "lt", {"name": "ema", "period": ema_f}, True),
            _c({"name": "rsi", "period": rsi_p}, "lt", e.get("rsi_short_max", 48)),
            _c({"name": "rsi", "period": rsi_p}, "gt", e.get("rsi_short_min", 32)),
            _c({"name": "macd_hist", "fast": 12, "slow": 26, "signal": 9}, "lt", 0),
        )
    elif f == "stoch_pullback":
        long_entry = _and(
            _c({"name": "close"}, "gt", {"name": "ema", "period": e.get("ema_trend", 50)}, True),
            _c({"name": "stoch_k", "k_period": 14, "d_period": 3}, "lt", e.get("stoch_buy", 25)),
            _c({"name": "stoch_k", "k_period": 14, "d_period": 3}, "cross_above",
               {"name": "stoch_d", "k_period": 14, "d_period": 3}, True),
        )
        short_entry = _and(
            _c({"name": "close"}, "lt", {"name": "ema", "period": e.get("ema_trend", 50)}, True),
            _c({"name": "stoch_k", "k_period": 14, "d_period": 3}, "gt", e.get("stoch_sell", 75)),
            _c({"name": "stoch_k", "k_period": 14, "d_period": 3}, "cross_below",
               {"name": "stoch_d", "k_period": 14, "d_period": 3}, True),
        )
    elif f == "breakout_trend":
        lb = e.get("lookback", 16)
        ema_tr = e.get("ema_trend", 80)
        long_entry = _and(
            _c({"name": "close"}, "gt", {"name": "ema", "period": ema_tr}, True),
            _c({"name": "close"}, "gt", {"name": "rolling_high", "period": lb}, True),
            _c({"name": "adx", "period": 14}, "gt", e.get("adx_min", 20)),
        )
        short_entry = _and(
            _c({"name": "close"}, "lt", {"name": "ema", "period": ema_tr}, True),
            _c({"name": "close"}, "lt", {"name": "rolling_low", "period": lb}, True),
            _c({"name": "adx", "period": 14}, "gt", e.get("adx_min", 20)),
        )
    else:
        raise ValueError(f"Unknown family: {f}")

    return StrategyGene(
        long_entry=long_entry if params.direction in ("long_only", "both") else None,
        short_entry=short_entry if params.direction in ("short_only", "both") else None,
        direction=params.direction,
        session_start=params.session_start,
        session_end=params.session_end,
        cooldown_bars=params.cooldown_bars,
        max_trades_per_day=params.max_trades_per_day,
        sl_atr_mult=params.sl_atr_mult,
        atr_period=params.atr_period,
    )


FAMILIES = ("pullback_trend", "range_rsi", "momentum_continuation", "stoch_pullback", "breakout_trend")


def random_expert_params(rng: random.Random, family: str | None = None) -> ExpertParams:
    family = family or rng.choice(FAMILIES)
    base = ExpertParams(
        family=family,
        session_start=rng.randint(7, 10),
        session_end=rng.randint(15, 19),
        cooldown_bars=rng.randint(2, 6),
        max_trades_per_day=rng.randint(3, 5),
        sl_atr_mult=round(rng.uniform(1.0, 1.6), 2),
        atr_period=rng.choice([10, 14, 20]),
        direction=rng.choice(["long_only", "short_only", "both"]),
    )

    if family == "pullback_trend":
        base.extra = {
            "ema_trend": rng.choice([50, 80, 100, 150]),
            "rsi_period": rng.choice([7, 10, 14]),
            "rsi_long_hi": rng.randint(40, 50),
            "rsi_long_lo": rng.randint(25, 38),
            "adx_min": rng.randint(15, 28),
        }
    elif family == "range_rsi":
        base.extra = {
            "rsi_period": rng.choice([5, 7, 10, 14]),
            "rsi_buy": rng.randint(22, 35),
            "rsi_sell": rng.randint(65, 78),
            "adx_max": rng.randint(18, 30),
        }
    elif family == "momentum_continuation":
        base.extra = {
            "ema_fast": rng.choice([13, 21, 34]),
            "ema_slow": rng.choice([34, 55, 89]),
            "rsi_period": rng.choice([10, 14]),
            "rsi_long_min": rng.randint(50, 58),
            "rsi_long_max": rng.randint(62, 72),
            "rsi_short_min": rng.randint(28, 38),
            "rsi_short_max": rng.randint(42, 50),
        }
    elif family == "stoch_pullback":
        base.extra = {
            "ema_trend": rng.choice([34, 50, 80]),
            "stoch_buy": rng.randint(18, 30),
            "stoch_sell": rng.randint(70, 82),
        }
    elif family == "breakout_trend":
        base.extra = {
            "lookback": rng.choice([8, 12, 16, 24]),
            "ema_trend": rng.choice([50, 80, 100]),
            "adx_min": rng.randint(18, 30),
        }
    return base


def mutate_expert_params(params: ExpertParams, rng: random.Random, rate: float = 0.35) -> ExpertParams:
    d = params.to_dict()
    family = d["family"]
    new = random_expert_params(rng, family=family)
    for key in ("session_start", "session_end", "cooldown_bars", "sl_atr_mult"):
        if rng.random() < rate:
            setattr(new, key, d[key])
    if rng.random() < rate:
        new.direction = d["direction"]
    for k, v in d.items():
        if k in FAMILIES or k in ("family", "session_start", "session_end", "cooldown_bars",
                                   "max_trades_per_day", "sl_atr_mult", "atr_period", "direction"):
            continue
        if k in new.extra and rng.random() < rate:
            new.extra[k] = v
    return new
