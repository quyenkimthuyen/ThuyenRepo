"""
Persistent knowledge base — tích lũy kinh nghiệm qua nhiều lần chạy.

Mỗi epoch walk-forward cập nhật:
  - rule_stats: rule nào giúp thắng/thua
  - genomes: chiến lược tốt nhất (DNA)
  - ml_experience: mẫu feature → outcome để train ML
  - epoch_history: tiến bộ qua các lần chạy
"""
from __future__ import annotations

import json
import copy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from genome_naming import describe_genome, display_name, is_legacy_name

LEARNING_DIR = Path(__file__).parent / "learning"
KNOWLEDGE_PATH = LEARNING_DIR / "knowledge.json"
MAX_GENOMES = 40
MAX_ML_SAMPLES = 8000
MAX_RULE_EVENTS = 12000


def rule_key(feature: str, direction: str, op: str, threshold: float) -> str:
  return f"{direction}|{feature}|{op}|{round(threshold, 4)}"


def _default_rule_stat() -> dict:
  return {"wins": 0, "losses": 0, "total_r": 0.0, "uses": 0}


class KnowledgeBase:
  def __init__(self, path: Path = KNOWLEDGE_PATH):
    self.path = path
    self.epoch_count = 0
    self.rule_stats: dict[str, dict] = {}
    self.genomes: list[dict] = []
    self.ml_experience: list[dict] = []
    self.rule_events: list[dict] = []
    self.epoch_history: list[dict] = []
    self.best_fitness_ever = -1e9
    self._load()

  def _load(self):
    if not self.path.exists():
      return
    with open(self.path, encoding="utf-8") as f:
      data = json.load(f)
    self.epoch_count = data.get("epoch_count", 0)
    self.rule_stats = data.get("rule_stats", {})
    self.genomes = data.get("genomes", [])
    self.ml_experience = data.get("ml_experience", [])
    self.rule_events = data.get("rule_events", [])
    self.epoch_history = data.get("epoch_history", [])
    self.best_fitness_ever = data.get("best_fitness_ever", -1e9)

  def save(self):
    self.path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.path, "w", encoding="utf-8") as f:
      json.dump({
        "epoch_count": self.epoch_count,
        "rule_stats": self.rule_stats,
        "genomes": self.genomes[:MAX_GENOMES],
        "ml_experience": self.ml_experience[-MAX_ML_SAMPLES:],
        "rule_events": self.rule_events[-MAX_RULE_EVENTS:],
        "epoch_history": self.epoch_history,
        "best_fitness_ever": self.best_fitness_ever,
        "updated_at": datetime.now(timezone.utc).isoformat(),
      }, f, indent=2, ensure_ascii=False)

  def _stats_from_events(self, as_of=None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ev in self.rule_events:
      if as_of is not None:
        t = pd.Timestamp(ev.get("entry_time", 0))
        if t >= pd.Timestamp(as_of):
          continue
      key = ev["key"]
      st = out.setdefault(key, _default_rule_stat())
      st["uses"] += 1
      st["total_r"] += ev["r"]
      if ev["r"] > 0:
        st["wins"] += 1
      else:
        st["losses"] += 1
    return out

  def rule_weight_multiplier(self, r, as_of=None) -> float:
    """Nhân weight rule dựa trên kinh nghiệm lịch sử (chỉ trước as_of nếu có)."""
    key = rule_key(r.feature, r.direction, r.op, r.threshold)
    if as_of is not None and self.rule_events:
      st = self._stats_from_events(as_of).get(key)
    else:
      st = self.rule_stats.get(key)
    if not st or st["uses"] < 3:
      return 1.0
    wr = st["wins"] / st["uses"]
    avg_r = st["total_r"] / st["uses"]
    mult = 1.0 + (wr - 0.35) * 2.0 + avg_r * 0.15
    return float(np.clip(mult, 0.3, 2.5))

  def record_rule_outcomes(self, matched_keys: list[str], r_multiple: float, entry_time=None):
    won = r_multiple > 0
    ts = str(entry_time) if entry_time is not None else None
    for key in matched_keys:
      st = self.rule_stats.setdefault(key, _default_rule_stat())
      st["uses"] += 1
      st["total_r"] += r_multiple
      if won:
        st["wins"] += 1
      else:
        st["losses"] += 1
      if ts:
        self.rule_events.append({"key": key, "entry_time": ts, "r": float(r_multiple)})
    if len(self.rule_events) > MAX_RULE_EVENTS:
      self.rule_events = self.rule_events[-MAX_RULE_EVENTS:]

  def add_ml_sample(self, features: dict[str, float], long_win: int, short_win: int, entry_time=None):
    self.ml_experience.append({
      "features": {k: round(v, 6) for k, v in features.items()},
      "long_win": int(long_win),
      "short_win": int(short_win),
      "entry_time": str(entry_time) if entry_time is not None else None,
    })
    if len(self.ml_experience) > MAX_ML_SAMPLES:
      self.ml_experience = self.ml_experience[-MAX_ML_SAMPLES:]

  def ml_samples_before(self, as_of) -> list[dict]:
    cutoff = pd.Timestamp(as_of)
    out = []
    for s in self.ml_experience:
      ts = s.get("entry_time")
      if ts is None:
        continue
      if pd.Timestamp(ts) < cutoff:
        out.append(s)
    return out[-2000:]

  def genome_to_dict(self, strat, fitness: float) -> dict:
    from strategy_miner import Rule
    def ser_rules(rules: list[Rule]):
      return [{"feature": r.feature, "direction": r.direction, "op": r.op,
               "threshold": r.threshold, "weight": r.weight} for r in rules]
    return {
      "fitness": fitness,
      "name": strat.name,
      "long_rules": ser_rules(strat.long_rules),
      "short_rules": ser_rules(strat.short_rules),
      "score_threshold": strat.score_threshold,
      "atr_mult_sl": strat.atr_mult_sl,
      "rr_ratio": strat.rr_ratio,
      "min_rules_match": strat.min_rules_match,
      "ml_prob_min": strat.ml_prob_min,
      "exit_mode": strat.exit_mode,
      "partial_pct": strat.partial_pct,
      "partial_at_r": strat.partial_at_r,
      "trail_activate_r": strat.trail_activate_r,
      "trail_distance_r": strat.trail_distance_r,
      "max_trades_per_week": strat.max_trades_per_week,
    }

  def dict_to_strategy(self, g: dict):
    from config import DEFAULT_TRAIL_ACTIVATE_R, DEFAULT_TRAIL_DISTANCE_R
    from strategy_miner import MinedStrategy, Rule
    def des_rules(rules):
      return [Rule(r["feature"], r["direction"], r["op"], r["threshold"], r["weight"]) for r in rules]
    name = display_name(g.get("name", "genome"), g)
    return MinedStrategy(
      long_rules=des_rules(g["long_rules"]),
      short_rules=des_rules(g["short_rules"]),
      score_threshold=g["score_threshold"],
      atr_mult_sl=g["atr_mult_sl"],
      rr_ratio=g["rr_ratio"],
      min_rules_match=g.get("min_rules_match", 1),
      ml_prob_min=g.get("ml_prob_min", 0.40),
      exit_mode=g.get("exit_mode", "full"),
      partial_pct=g.get("partial_pct", 0.4),
      partial_at_r=g.get("partial_at_r", 1.5),
      trail_activate_r=g.get("trail_activate_r", DEFAULT_TRAIL_ACTIVATE_R),
      trail_distance_r=g.get("trail_distance_r", DEFAULT_TRAIL_DISTANCE_R),
      max_trades_per_week=g.get("max_trades_per_week", 2),
      name=name,
    )

  def add_genome(self, strat, fitness: float):
    g = self.genome_to_dict(strat, fitness)
    if is_legacy_name(g.get("name", "")):
      g["name"] = describe_genome(g)
      strat.name = g["name"]
    self.genomes.append(g)
    self.genomes.sort(key=lambda x: x["fitness"], reverse=True)
    self.genomes = self.genomes[:MAX_GENOMES]
    if fitness > self.best_fitness_ever:
      self.best_fitness_ever = fitness

  def top_genomes(self, n: int = 8) -> list[dict]:
    return self.genomes[:n]

  def record_epoch(self, epoch: int, metrics: dict):
    self.epoch_count = epoch
    self.epoch_history.append({
      "epoch": epoch,
      "timestamp": datetime.now(timezone.utc).isoformat(),
      **metrics,
    })

  def improvement_summary(self) -> str:
    if len(self.epoch_history) < 2:
      return "Chưa đủ epoch để so sánh tiến bộ."
    first, last = self.epoch_history[0], self.epoch_history[-1]
    lines = [
      f"Epoch 1 → {last['epoch']}:",
      f"  Win Rate: {first.get('win_rate_pct')}% → {last.get('win_rate_pct')}%",
      f"  RR:       {first.get('avg_rr')} → {last.get('avg_rr')}",
      f"  Total R:  {first.get('total_r')} → {last.get('total_r')}",
      f"  Genomes:  {len(self.genomes)} | Rules tracked: {len(self.rule_stats)}",
    ]
    return "\n".join(lines)
