"""
Evolution engine — đột biến / lai ghép genomes từ knowledge base.
"""
import copy
import random
from typing import TYPE_CHECKING

import numpy as np

from knowledge_base import KnowledgeBase, rule_key

if TYPE_CHECKING:
  from strategy_miner import MiningSearchSpace

M15_RR_RATIOS = (1.8, 2.2, 2.5, 3.0)
M15_ATR_MULTIPLIERS = (1.05, 1.35, 1.65, 2.0)
M15_MAX_HOLD_BARS = (36, 64, 96, 128)
M15_MIN_BARS_BETWEEN = (4, 8, 12, 16)
M15_SESSION_RANGES = ((7, 20), (8, 17))


def mutate_genome(
  g: dict, rate: float = 0.25, search_space: "MiningSearchSpace | None" = None,
) -> dict:
  """Tạo biến thể mới từ genome."""
  child = copy.deepcopy(g)
  child["name"] = g.get("name", "genome") + "_mut"
  child.setdefault("max_hold_bars", 36)
  child.setdefault("min_bars_between", 4)
  child.setdefault("session_filter", True)
  child.setdefault("session_start_hour", 7)
  child.setdefault("session_end_hour", 20)

  if random.random() < rate:
    child["score_threshold"] = float(np.clip(
      g.get("score_threshold", 2.0) * random.uniform(0.8, 1.2), 0.4, 4.0))
  if random.random() < rate:
    child["ml_prob_min"] = float(np.clip(
      g.get("ml_prob_min", 0.40) + random.uniform(-0.06, 0.06), 0.30, 0.55))
  if random.random() < rate:
    child["rr_ratio"] = random.choice(
      search_space.rr_ratios if search_space else (2.0, 2.5, 3.0)
    )
  if random.random() < rate:
    if search_space:
      child["atr_mult_sl"] = random.choice(search_space.atr_multipliers)
    else:
      child["atr_mult_sl"] = float(np.clip(
        g.get("atr_mult_sl", 0.9) + random.uniform(-0.1, 0.1), 0.7, 1.2,
      ))
  if random.random() < rate:
    child["min_rules_match"] = random.choice([1, 2, 3])
  if random.random() < rate:
    child["exit_mode"] = random.choice(["full", "hybrid", "partial"])
  if search_space is not None:
    if random.random() < rate:
      child["max_hold_bars"] = random.choice(search_space.max_hold_bars)
    if random.random() < rate:
      child["min_bars_between"] = random.choice(search_space.min_bars_between)
    if random.random() < rate:
      child["session_start_hour"], child["session_end_hour"] = random.choice(
        search_space.session_ranges
      )
    if random.random() < rate:
      child["session_filter"] = random.choice(search_space.session_filters)

  for rules_key in ("long_rules", "short_rules"):
    rules = child[rules_key]
    for r in rules:
      if random.random() < rate * 0.5:
        r["weight"] = float(np.clip(r["weight"] * random.uniform(0.7, 1.4), 0.1, 3.0))
      if random.random() < rate * 0.3 and r["op"] != "eq1":
        r["threshold"] *= random.uniform(0.9, 1.1)
    if random.random() < rate * 0.2 and len(rules) > 2:
      rules.pop(random.randint(0, len(rules) - 1))

  return child


def crossover(
  g1: dict, g2: dict, search_space: "MiningSearchSpace | None" = None,
) -> dict:
  """Lai ghép 2 genome cha mẹ."""
  child = copy.deepcopy(g1)
  child["name"] = "crossover"
  child["long_rules"] = copy.deepcopy(
    g1["long_rules"][:len(g1["long_rules"]) // 2] +
    g2["long_rules"][len(g2["long_rules"]) // 2:]
  )
  child["short_rules"] = copy.deepcopy(
    g2["short_rules"][:len(g2["short_rules"]) // 2] +
    g1["short_rules"][len(g1["short_rules"]) // 2:]
  )
  child["score_threshold"] = (g1["score_threshold"] + g2["score_threshold"]) / 2
  child["ml_prob_min"] = (g1["ml_prob_min"] + g2["ml_prob_min"]) / 2
  child["rr_ratio"] = random.choice([g1["rr_ratio"], g2["rr_ratio"]])
  child["atr_mult_sl"] = random.choice([g1["atr_mult_sl"], g2["atr_mult_sl"]])
  child["exit_mode"] = random.choice([g1["exit_mode"], g2["exit_mode"]])
  child["max_hold_bars"] = random.choice([
    g1.get("max_hold_bars", 36), g2.get("max_hold_bars", 36),
  ])
  child["min_bars_between"] = random.choice([
    g1.get("min_bars_between", 4), g2.get("min_bars_between", 4),
  ])
  session = random.choice([
    (g1.get("session_start_hour", 7), g1.get("session_end_hour", 20)),
    (g2.get("session_start_hour", 7), g2.get("session_end_hour", 20)),
  ])
  child["session_start_hour"], child["session_end_hour"] = session
  child["session_filter"] = random.choice([
    g1.get("session_filter", True), g2.get("session_filter", True),
  ])
  if search_space is not None:
    # Projection is applied by the caller after deserialization; keep this
    # function JSON-only and ensure singleton experimental genes are honored.
    if len(search_space.rr_ratios) == 1:
      child["rr_ratio"] = search_space.rr_ratios[0]
    if len(search_space.atr_multipliers) == 1:
      child["atr_mult_sl"] = search_space.atr_multipliers[0]
    if len(search_space.max_hold_bars) == 1:
      child["max_hold_bars"] = search_space.max_hold_bars[0]
    if len(search_space.min_bars_between) == 1:
      child["min_bars_between"] = search_space.min_bars_between[0]
    if len(search_space.session_ranges) == 1:
      child["session_start_hour"], child["session_end_hour"] = search_space.session_ranges[0]
    if len(search_space.session_filters) == 1:
      child["session_filter"] = search_space.session_filters[0]
  return child


def evolve_population(
  kb: KnowledgeBase, n_offspring: int = 12,
  search_space: "MiningSearchSpace | None" = None,
) -> list[dict]:
  """Sinh thế hệ mới từ top genomes."""
  tops = kb.top_genomes(8)
  if not tops:
    return []

  offspring = [copy.deepcopy(tops[0])]

  while len(offspring) < n_offspring:
    r = random.random()
    if r < 0.5 and len(tops) >= 1:
      offspring.append(mutate_genome(random.choice(tops[:4]), search_space=search_space))
    elif r < 0.8 and len(tops) >= 2:
      p1, p2 = random.sample(tops[:6], 2)
      offspring.append(mutate_genome(
        crossover(p1, p2, search_space=search_space), search_space=search_space,
      ))
    else:
      offspring.append(mutate_genome(random.choice(tops), search_space=search_space))

  return offspring[:n_offspring]


def apply_kb_rule_weights(strat, kb: KnowledgeBase, as_of=None):
  """Điều chỉnh weight rules theo kinh nghiệm tích lũy (causal nếu as_of set)."""
  from strategy_miner import Rule
  new_long, new_short = [], []
  for r in strat.long_rules:
    w = r.weight * kb.rule_weight_multiplier(r, as_of=as_of)
    new_long.append(Rule(r.feature, r.direction, r.op, r.threshold, w))
  for r in strat.short_rules:
    w = r.weight * kb.rule_weight_multiplier(r, as_of=as_of)
    new_short.append(Rule(r.feature, r.direction, r.op, r.threshold, w))
  strat.long_rules = new_long
  strat.short_rules = new_short
  return strat
