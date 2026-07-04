from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.indicators.library import compute_indicator

COMPARATORS = ("lt", "gt", "lte", "gte", "cross_above", "cross_below")
LOGIC_OPS = ("and", "or", "not")
DIRECTIONS = ("long_only", "short_only", "both")

from systemtrain.data.prepared import indicator_column_key
from systemtrain.strategy.indicator_pool import INDICATOR_POOL

THRESHOLD_RANGES = {
    "rsi": (20, 80),
    "stoch_k": (20, 80),
    "adx": (15, 40),
    "default": (-0.01, 0.01),
}


@dataclass
class ConditionNode:
    """Leaf: compare indicator vs value or vs another indicator."""

    left: dict[str, Any]
    op: str
    right: dict[str, Any] | float
    right_is_indicator: bool = False

    def complexity(self) -> int:
        return 1


@dataclass
class LogicNode:
    op: str
    children: list["ConditionNode | LogicNode"]

    def complexity(self) -> int:
        return 1 + sum(c.complexity() for c in self.children)


Node = ConditionNode | LogicNode


@dataclass
class StrategyGene:
    """Full strategy specification."""

    long_entry: Node | None
    short_entry: Node | None
    direction: str = "both"
    session_start: int = 7
    session_end: int = 17
    cooldown_bars: int = 4
    max_trades_per_day: int = 3
    sl_atr_mult: float = 1.5
    atr_period: int = 14
    learned_setup: dict[str, Any] | None = None  # data-mined setup

    def complexity(self) -> int:
        if self.learned_setup:
            lr = len(self.learned_setup.get("long_rules", []))
            sr = len(self.learned_setup.get("short_rules", []))
            return lr + sr

    def to_dict(self) -> dict:
        return {
            "long_entry": _node_to_dict(self.long_entry),
            "short_entry": _node_to_dict(self.short_entry),
            "direction": self.direction,
            "session_start": self.session_start,
            "session_end": self.session_end,
            "cooldown_bars": self.cooldown_bars,
            "max_trades_per_day": self.max_trades_per_day,
            "sl_atr_mult": self.sl_atr_mult,
            "atr_period": self.atr_period,
            "learned_setup": self.learned_setup,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyGene":
        return cls(
            long_entry=_node_from_dict(d.get("long_entry")),
            short_entry=_node_from_dict(d.get("short_entry")),
            direction=d.get("direction", "both"),
            session_start=d.get("session_start", 7),
            session_end=d.get("session_end", 17),
            cooldown_bars=d.get("cooldown_bars", 4),
            max_trades_per_day=d.get("max_trades_per_day", 3),
            sl_atr_mult=d.get("sl_atr_mult", 1.5),
            atr_period=d.get("atr_period", 14),
            learned_setup=d.get("learned_setup"),
        )


def _node_to_dict(node: Node | None) -> dict | None:
    if node is None:
        return None
    if isinstance(node, ConditionNode):
        return {
            "type": "condition",
            "left": node.left,
            "op": node.op,
            "right": node.right,
            "right_is_indicator": node.right_is_indicator,
        }
    return {
        "type": "logic",
        "op": node.op,
        "children": [_node_to_dict(c) for c in node.children],
    }


def _node_from_dict(d: dict | None) -> Node | None:
    if d is None:
        return None
    if d["type"] == "condition":
        return ConditionNode(
            left=d["left"],
            op=d["op"],
            right=d["right"],
            right_is_indicator=d.get("right_is_indicator", False),
        )
    return LogicNode(op=d["op"], children=[_node_from_dict(c) for c in d["children"]])


def _get_series(df: pd.DataFrame, spec: dict) -> pd.Series:
    key = indicator_column_key(spec)
    if key in df.columns:
        return df[key]
    name = spec["name"]
    params = {k: v for k, v in spec.items() if k != "name"}
    return compute_indicator(df, name, params)


def _eval_condition_series(df: pd.DataFrame, node: ConditionNode) -> pd.Series:
    left = _get_series(df, node.left)
    if node.right_is_indicator and isinstance(node.right, dict):
        right = _get_series(df, node.right)
    else:
        right = float(node.right)

    if node.op == "lt":
        return left < right
    if node.op == "gt":
        return left > right
    if node.op == "lte":
        return left <= right
    if node.op == "gte":
        return left >= right
    if node.op == "cross_above":
        if isinstance(right, pd.Series):
            return (left.shift(1) <= right.shift(1)) & (left > right)
        return (left.shift(1) <= right) & (left > right)
    if node.op == "cross_below":
        if isinstance(right, pd.Series):
            return (left.shift(1) >= right.shift(1)) & (left < right)
        return (left.shift(1) >= right) & (left < right)
    return pd.Series(False, index=df.index)


def _eval_node_series(df: pd.DataFrame, node: Node) -> pd.Series:
    if isinstance(node, ConditionNode):
        return _eval_condition_series(df, node)
    if node.op == "not":
        return ~_eval_node_series(df, node.children[0])
    if node.op == "and":
        result = pd.Series(True, index=df.index)
        for child in node.children:
            result &= _eval_node_series(df, child)
        return result
    if node.op == "or":
        result = pd.Series(False, index=df.index)
        for child in node.children:
            result |= _eval_node_series(df, child)
        return result
    return pd.Series(False, index=df.index)


def _apply_filters(
    raw_mask: np.ndarray,
    index: pd.DatetimeIndex,
    session_start: int,
    session_end: int,
    cooldown_bars: int,
    max_trades_per_day: int,
) -> np.ndarray:
    hours = index.hour.values
    dates = index.date
    n = len(raw_mask)
    out = np.zeros(n, dtype=bool)
    candidates = np.where(raw_mask)[0]
    last_bar = -cooldown_bars - 1
    trades_today: dict = {}

    for i in candidates:
        if i < 1:
            continue
        if hours[i] < session_start or hours[i] >= session_end:
            continue
        day_key = dates[i]
        if trades_today.get(day_key, 0) >= max_trades_per_day:
            continue
        if i - last_bar <= cooldown_bars:
            continue
        out[i] = True
        last_bar = i
        trades_today[day_key] = trades_today.get(day_key, 0) + 1

    return out


def generate_signals(df: pd.DataFrame, gene: StrategyGene) -> tuple[pd.Series, pd.Series]:
    """Vectorized entry signals with session/cooldown filters."""
    if gene.learned_setup:
        from systemtrain.learn.setup_miner import LearnedSetup, MinedRule, generate_learned_signals

        d = gene.learned_setup
        setup = LearnedSetup(
            long_rules=[],
            short_rules=[],
            session_start=d.get("session_start", gene.session_start),
            session_end=d.get("session_end", gene.session_end),
            cooldown_bars=d.get("cooldown_bars", gene.cooldown_bars),
            max_trades_per_day=d.get("max_trades_per_day", gene.max_trades_per_day),
            sl_atr_mult=d.get("sl_atr_mult", gene.sl_atr_mult),
            atr_period=d.get("atr_period", gene.atr_period),
            direction=d.get("direction", gene.direction),
            htf_long_filter=[tuple(x) for x in d.get("htf_long_filter", [])],
            htf_short_filter=[tuple(x) for x in d.get("htf_short_filter", [])],
            source_wr=d.get("source_wr", 0),
            source_samples=d.get("source_samples", 0),
        )
        for r in d.get("long_rules", []):
            setup.long_rules.append(MinedRule(
                feature=r["feature"], op=r["op"], threshold=r["threshold"],
                direction=r.get("direction", "long"), win_rate=r.get("win_rate", 0),
                samples=r.get("samples", 0), expectancy=r.get("expectancy", 0),
            ))
        for r in d.get("short_rules", []):
            setup.short_rules.append(MinedRule(
                feature=r["feature"], op=r["op"], threshold=r["threshold"],
                direction=r.get("direction", "short"), win_rate=r.get("win_rate", 0),
                samples=r.get("samples", 0), expectancy=r.get("expectancy", 0),
            ))
        return generate_learned_signals(df, setup)

    n = len(df)
    long_raw = np.zeros(n, dtype=bool)
    short_raw = np.zeros(n, dtype=bool)

    if gene.direction in ("long_only", "both") and gene.long_entry:
        long_raw = _eval_node_series(df, gene.long_entry).fillna(False).values
    if gene.direction in ("short_only", "both") and gene.short_entry:
        short_raw = _eval_node_series(df, gene.short_entry).fillna(False).values

    long_sig = _apply_filters(
        long_raw, df.index, gene.session_start, gene.session_end,
        gene.cooldown_bars, gene.max_trades_per_day,
    )
    short_sig = _apply_filters(
        short_raw, df.index, gene.session_start, gene.session_end,
        gene.cooldown_bars, gene.max_trades_per_day,
    )

    return pd.Series(long_sig, index=df.index), pd.Series(short_sig, index=df.index)


def _random_threshold(indicator_name: str, close_price: float = 1.1) -> float:
    if indicator_name in ("close", "high", "low", "open"):
        return close_price * random.uniform(0.98, 1.02)
    if indicator_name in THRESHOLD_RANGES:
        lo, hi = THRESHOLD_RANGES[indicator_name]
        return random.uniform(lo, hi)
    lo, hi = THRESHOLD_RANGES["default"]
    return random.uniform(lo, hi)


def _random_indicator_spec() -> dict:
    name, params = random.choice(INDICATOR_POOL)
    return {"name": name, **params}


def _random_condition() -> ConditionNode:
    left = _random_indicator_spec()
    op = random.choice(COMPARATORS)
    if random.random() < 0.35:
        right = _random_indicator_spec()
        return ConditionNode(left=left, op=op, right=right, right_is_indicator=True)
    thresh = _random_threshold(left["name"])
    return ConditionNode(left=left, op=op, right=thresh, right_is_indicator=False)


def _random_logic_tree(depth: int = 0, max_depth: int = 2) -> Node:
    if depth >= max_depth or random.random() < 0.4:
        return _random_condition()
    op = random.choice(["and", "or"])
    n_children = random.randint(2, 3)
    return LogicNode(op=op, children=[_random_logic_tree(depth + 1, max_depth) for _ in range(n_children)])


def random_gene(rng: random.Random | None = None) -> StrategyGene:
    rng = rng or random.Random()
    direction = rng.choice(DIRECTIONS)
    long_entry = _random_logic_tree() if direction in ("long_only", "both") else None
    short_entry = _random_logic_tree() if direction in ("short_only", "both") else None
    return StrategyGene(
        long_entry=long_entry,
        short_entry=short_entry,
        direction=direction,
        session_start=rng.randint(6, 10),
        session_end=rng.randint(15, 20),
        cooldown_bars=rng.randint(2, 8),
        max_trades_per_day=rng.randint(2, 5),
        sl_atr_mult=round(rng.uniform(1.0, 2.5), 2),
        atr_period=rng.choice([10, 14, 20]),
    )


def mutate_node(node: Node, rate: float, rng: random.Random) -> Node:
    if rng.random() > rate:
        return copy.deepcopy(node)
    if isinstance(node, ConditionNode):
        if rng.random() < 0.5:
            return _random_condition()
        node = copy.deepcopy(node)
        if not node.right_is_indicator and isinstance(node.right, (int, float)):
            node.right = float(node.right) * rng.uniform(0.85, 1.15)
        return node
    node = copy.deepcopy(node)
    node.op = rng.choice(LOGIC_OPS[:2]) if node.op != "not" else "not"
    if rng.random() < 0.3:
        node.children.append(_random_logic_tree(max_depth=1))
    for j, child in enumerate(node.children):
        node.children[j] = mutate_node(child, rate, rng)
    return node


def mutate_gene(gene: StrategyGene, rate: float, rng: random.Random) -> StrategyGene:
    g = copy.deepcopy(gene)
    if g.long_entry:
        g.long_entry = mutate_node(g.long_entry, rate, rng)
    if g.short_entry:
        g.short_entry = mutate_node(g.short_entry, rate, rng)
    if rng.random() < rate:
        g.session_start = max(0, min(12, g.session_start + rng.randint(-2, 2)))
    if rng.random() < rate:
        g.session_end = max(14, min(23, g.session_end + rng.randint(-2, 2)))
    if rng.random() < rate:
        g.cooldown_bars = max(1, g.cooldown_bars + rng.randint(-2, 2))
    if rng.random() < rate:
        g.sl_atr_mult = round(max(0.8, min(3.0, g.sl_atr_mult + rng.uniform(-0.3, 0.3))), 2)
    return g


def crossover_genes(a: StrategyGene, b: StrategyGene, rng: random.Random) -> StrategyGene:
    child = copy.deepcopy(a)
    if rng.random() < 0.5 and b.long_entry:
        child.long_entry = copy.deepcopy(b.long_entry)
    if rng.random() < 0.5 and b.short_entry:
        child.short_entry = copy.deepcopy(b.short_entry)
    if rng.random() < 0.5:
        child.session_start = b.session_start
        child.session_end = b.session_end
    if rng.random() < 0.5:
        child.sl_atr_mult = b.sl_atr_mult
        child.atr_period = b.atr_period
    return child
