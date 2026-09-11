"""Tên genome / strategy dễ đọc cho trader."""
from __future__ import annotations

import hashlib
import re


_EXIT_LABEL = {
  "full": "full",
  "hybrid": "hybrid",
  "partial": "partial",
  "trail": "trail",
}


def _top_features(rules: list[dict], n: int = 2) -> list[str]:
  if not rules:
    return []
  ranked = sorted(rules, key=lambda r: abs(float(r.get("weight", 0) or 0)), reverse=True)
  out: list[str] = []
  for r in ranked:
    feat = str(r.get("feature", ""))
    short = feat.split("_")[0]
    if len(short) > 10:
      short = short[:10]
    if short and short not in out:
      out.append(short)
    if len(out) >= n:
      break
  return out


def genome_signature(g: dict) -> str:
  key = (
    round(float(g.get("rr_ratio") or 0), 2),
    g.get("exit_mode"),
    round(float(g.get("atr_mult_sl") or 0), 2),
    int(g.get("min_rules_match") or 0),
    round(float(g.get("ml_prob_min") or 0), 3),
    len(g.get("long_rules") or []),
    len(g.get("short_rules") or []),
    tuple(_top_features(g.get("long_rules") or [], 3)),
    tuple(_top_features(g.get("short_rules") or [], 3)),
  )
  return hashlib.md5(repr(key).encode()).hexdigest()[:4].upper()


def is_legacy_name(name: str) -> bool:
  if not name:
    return True
  low = name.lower().strip()
  if low in ("genome", "mined_v3", "crossover", "mined"):
    return True
  if low.startswith("v3_"):
    return True
  if "crossover" in low:
    return True
  if "_mut" in low:
    return True
  return False


def describe_genome(g: dict) -> str:
  """
  Ví dụ: Forge RR2.5 trail 5L3S rsi,macd #A3F2
  """
  rr = float(g.get("rr_ratio") or 2.5)
  exit_m = _EXIT_LABEL.get(str(g.get("exit_mode") or "full"), str(g.get("exit_mode") or "full"))
  nl = len(g.get("long_rules") or [])
  ns = len(g.get("short_rules") or [])
  feats = _top_features((g.get("long_rules") or []) + (g.get("short_rules") or []), 2)
  feat_part = "+".join(feats) if feats else "mixed"
  sig = genome_signature(g)
  rr_s = f"{rr:g}".rstrip("0").rstrip(".")
  return f"Forge RR{rr_s} {exit_m} {nl}L{ns}S {feat_part} #{sig}"


def display_name(name: str, g: dict | None = None) -> str:
  if g and is_legacy_name(name):
    return describe_genome(g)
  return name or (describe_genome(g) if g else "?")


def genome_dict_from_strategy(strat) -> dict:
  return {
    "rr_ratio": strat.rr_ratio,
    "exit_mode": strat.exit_mode,
    "atr_mult_sl": strat.atr_mult_sl,
    "min_rules_match": strat.min_rules_match,
    "ml_prob_min": strat.ml_prob_min,
    "long_rules": [{"feature": r.feature, "weight": r.weight} for r in strat.long_rules],
    "short_rules": [{"feature": r.feature, "weight": r.weight} for r in strat.short_rules],
  }


def assign_strategy_name(strat) -> str:
  return describe_genome(genome_dict_from_strategy(strat))
