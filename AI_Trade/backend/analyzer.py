from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text

from .config import STRATEGY_PATH
from .labels import load_setups


def _feature_frame(setups: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for s in setups:
        if s.get("result") not in ("win", "loss"):
            continue
        f = s.get("features") or {}
        rows.append(
            {
                "win": 1 if s["result"] == "win" else 0,
                "direction_long": 1 if s["direction"] == "long" else 0,
                "rsi14": f.get("rsi14", 50),
                "dist_ema50_pips": f.get("dist_ema50_pips", 0),
                "trend_up": 1 if f.get("trend_up") else 0,
                "close_above_ema50": 1 if f.get("close_above_ema50") else 0,
                "close_above_ema200": 1 if f.get("close_above_ema200") else 0,
                "planned_rr": s.get("planned_rr", 2),
            }
        )
    return pd.DataFrame(rows)


def _rule_from_winners(df: pd.DataFrame) -> dict[str, Any]:
  wins = df[df["win"] == 1]
  if wins.empty:
      return {
          "long": {"trend_up": True, "rsi_min": 35, "rsi_max": 65, "close_above_ema50": True},
          "short": {"trend_up": False, "rsi_min": 35, "rsi_max": 65, "close_above_ema50": False},
      }

  def band(series: pd.Series, lo_q=0.25, hi_q=0.75):
      return float(series.quantile(lo_q)), float(series.quantile(hi_q))

  rsi_lo, rsi_hi = band(wins["rsi14"])
  rules: dict[str, Any] = {}
  for direction, mask_val in (("long", 1), ("short", 0)):
      subset = wins[wins["direction_long"] == mask_val]
      if subset.empty:
          subset = wins
      trend = bool(subset["trend_up"].median() >= 0.5)
      above50 = bool(subset["close_above_ema50"].median() >= 0.5)
      rlo, rhi = band(subset["rsi14"]) if len(subset) > 2 else (rsi_lo, rsi_hi)
      rules[direction] = {
          "trend_up": trend if direction == "long" else not trend,
          "rsi_min": round(max(20, rlo - 5), 1),
          "rsi_max": round(min(80, rhi + 5), 1),
          "close_above_ema50": above50 if direction == "long" else not above50,
      }
  return rules


def analyze_patterns(min_setups: int = 5) -> dict[str, Any]:
    setups = load_setups()
    train = [s for s in setups if s.get("period") == "train"]
    df = _feature_frame(train)

    if len(df) < min_setups:
        return {
            "status": "insufficient_data",
            "message": f"Cần ít nhất {min_setups} setup train (win/loss). Hiện có {len(df)}.",
            "setup_count": len(train),
            "labeled_outcomes": len(df),
        }

    win_rate = float(df["win"].mean())
    avg_rr = float(train_df_rr(train))
    rules = _rule_from_winners(df)

    feature_cols = [
        "direction_long",
        "rsi14",
        "dist_ema50_pips",
        "trend_up",
        "close_above_ema50",
        "close_above_ema200",
    ]
    tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=max(2, len(df) // 10))
    tree.fit(df[feature_cols], df["win"])
    tree_rules = export_text(tree, feature_names=feature_cols)

    strategy = {
        "name": "learned_from_labels",
        "source_setups": len(train),
        "win_rate_train": round(win_rate, 3),
        "avg_rr_train": round(avg_rr, 2),
        "rules": rules,
        "risk": {
            "sl_atr_mult": 1.0,
            "tp_atr_mult": 2.0,
            "use_atr_levels": True,
        },
        "tree_summary": tree_rules,
    }

    STRATEGY_PATH.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_PATH.write_text(json.dumps(strategy, indent=2), encoding="utf-8")

    feature_insights = []
    for col in feature_cols:
        if col == "direction_long":
            continue
        w = df[df["win"] == 1][col].mean()
        l = df[df["win"] == 0][col].mean()
        feature_insights.append(
            {"feature": col, "win_avg": round(float(w), 3), "loss_avg": round(float(l), 3)}
        )

    return {
        "status": "ok",
        "setup_count": len(train),
        "labeled_outcomes": len(df),
        "win_rate_train": round(win_rate, 3),
        "avg_rr_train": round(avg_rr, 2),
        "rules": rules,
        "feature_insights": feature_insights,
        "tree_summary": tree_rules,
        "strategy_path": str(STRATEGY_PATH),
    }


def train_df_rr(setups: list[dict[str, Any]]) -> float:
    vals = [s.get("planned_rr", 0) for s in setups if s.get("planned_rr")]
    return float(np.mean(vals)) if vals else 2.0


def load_strategy() -> dict[str, Any] | None:
    if not STRATEGY_PATH.exists():
        return None
    return json.loads(STRATEGY_PATH.read_text(encoding="utf-8"))
