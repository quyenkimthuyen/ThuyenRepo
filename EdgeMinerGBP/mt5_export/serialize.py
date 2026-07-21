"""Serialize MinedStrategy + MLScorer for MT5 export."""
from __future__ import annotations

from typing import Any

from ml_scorer import ML_FEATURES, MLScorer
from strategy_miner import MinedStrategy, Rule


def _rules_to_list(rules: list[Rule]) -> list[dict]:
  return [
    {
      "feat": r.feature,
      "op": r.op,
      "thr": round(float(r.threshold), 6),
      "w": round(float(r.weight), 6),
    }
    for r in rules
  ]


def strategy_to_export_dict(strat: MinedStrategy) -> dict[str, Any]:
  return {
    "name": strat.name,
    "exit_mode": strat.exit_mode,
    "ml_prob_min": float(strat.ml_prob_min),
    "score_threshold": float(strat.score_threshold),
    "rr": float(strat.rr_ratio),
    "atr_mult": float(strat.atr_mult_sl),
    "min_rules_match": int(strat.min_rules_match),
    "min_bars_between": int(strat.min_bars_between),
    "max_trades_per_week": int(strat.max_trades_per_week),
    "max_hold_bars": int(strat.max_hold_bars),
    "session_filter": bool(strat.session_filter),
    "partial_pct": float(strat.partial_pct),
    "partial_at_r": float(strat.partial_at_r),
    "trail_activate_r": float(strat.trail_activate_r),
    "trail_distance_r": float(strat.trail_distance_r),
    "long_rules": _rules_to_list(strat.long_rules),
    "short_rules": _rules_to_list(strat.short_rules),
  }


def ml_scorer_to_export_dict(scorer: MLScorer | None) -> dict[str, Any]:
  if scorer is None:
    return {"enabled": False, "features": ML_FEATURES}

  out: dict[str, Any] = {
    "enabled": True,
    "features": list(scorer.feat_names),
    "mean": [],
    "scale": [],
    "long": None,
    "short": None,
  }
  if hasattr(scorer.scaler, "mean_") and scorer.scaler.mean_ is not None:
    out["mean"] = [float(x) for x in scorer.scaler.mean_]
    out["scale"] = [float(x) for x in scorer.scaler.scale_]

  if scorer.long_model is not None:
    out["long"] = {
      "coef": [float(x) for x in scorer.long_model.coef_[0]],
      "intercept": float(scorer.long_model.intercept_[0]),
    }
  if scorer.short_model is not None:
    out["short"] = {
      "coef": [float(x) for x in scorer.short_model.coef_[0]],
      "intercept": float(scorer.short_model.intercept_[0]),
    }
  return out


def build_export_payload(strat: MinedStrategy, meta: dict[str, Any]) -> dict[str, Any]:
  return {
    "format": "forexforge_mt5_v1",
    "meta": meta,
    "strategy": strategy_to_export_dict(strat),
    "ml": ml_scorer_to_export_dict(strat.ml_scorer),
  }
