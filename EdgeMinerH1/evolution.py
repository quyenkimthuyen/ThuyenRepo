"""
Evolution engine — đột biến / lai ghép genomes từ knowledge base.
"""
import copy
import random

import numpy as np

from knowledge_base import KnowledgeBase, rule_key


def mutate_genome(g: dict, rate: float = 0.25) -> dict:
  """Tạo biến thể mới từ genome."""
  child = copy.deepcopy(g)
  child["name"] = g.get("name", "genome") + "_mut"

  if random.random() < rate:
    child["score_threshold"] = float(np.clip(
      g["score_threshold"] * random.uniform(0.8, 1.2), 0.4, 4.0))
  if random.random() < rate:
    child["ml_prob_min"] = float(np.clip(
      g["ml_prob_min"] + random.uniform(-0.06, 0.06), 0.30, 0.55))
  if random.random() < rate:
    child["rr_ratio"] = random.choice([2.0, 2.5, 3.0])
  if random.random() < rate:
    child["atr_mult_sl"] = float(np.clip(
      g["atr_mult_sl"] + random.uniform(-0.1, 0.1), 0.7, 1.2))
  if random.random() < rate:
    child["min_rules_match"] = random.choice([1, 2, 3])
  if random.random() < rate:
    child["exit_mode"] = random.choice(["full", "hybrid", "partial"])

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


def crossover(g1: dict, g2: dict) -> dict:
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
  child["exit_mode"] = random.choice([g1["exit_mode"], g2["exit_mode"]])
  return child


def evolve_population(kb: KnowledgeBase, n_offspring: int = 12) -> list[dict]:
  """Sinh thế hệ mới từ top genomes."""
  tops = kb.top_genomes(8)
  if not tops:
    return []

  offspring = [copy.deepcopy(tops[0])]

  while len(offspring) < n_offspring:
    r = random.random()
    if r < 0.5 and len(tops) >= 1:
      offspring.append(mutate_genome(random.choice(tops[:4])))
    elif r < 0.8 and len(tops) >= 2:
      p1, p2 = random.sample(tops[:6], 2)
      offspring.append(mutate_genome(crossover(p1, p2)))
    else:
      offspring.append(mutate_genome(random.choice(tops)))

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
