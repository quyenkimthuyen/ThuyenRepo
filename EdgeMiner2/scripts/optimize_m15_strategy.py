#!/usr/bin/env python3
"""Leakage-aware staged optimization for the native M15 strategy."""
from __future__ import annotations

import hashlib
import json
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_m15
from gui.trade_model import load_active_model_id, load_model_report
from optimizer import reset_kb_cache
from run_backtest import run_walk_forward
from strategy import Trade, compute_metrics
from strategy_miner import mining_search_space_from_dict

OUT_DIR = ROOT / "results" / "research" / "m15_strategy_optimization"
REPORTS_DIR = OUT_DIR / "reports"
RESULT_PATH = OUT_DIR / "latest.json"
SELECT_FROM = pd.Timestamp("2026-01-05")
HOLDOUT_FROM = pd.Timestamp("2026-05-01")

BASE_SPACE = {
  "rr_ratios": [2.5, 3.0],
  "atr_multipliers": [0.9, 1.05],
  "max_hold_bars": [36],
  "min_bars_between": [4],
  "session_ranges": [[7, 20]],
  "session_filters": [True],
  "score_thresholds": [0.6, 1.0, 1.6, 2.2],
  "min_rules_matches": [1, 2],
  "ml_probability_thresholds": [0.36, 0.40, 0.44, 0.48],
  "min_feature_samples": 30,
  "min_threshold_samples": 10,
  "min_binary_samples": 8,
  "include_session_regime_rules": False,
  "target_trades_per_week": 10.0,
  "drawdown_penalty": 0.0,
  "loss_streak_penalty": 0.0,
}


@dataclass(frozen=True)
class Variant:
  name: str
  overrides: dict
  feature_profile: str = "current"

  def space_dict(self) -> dict:
    return {**BASE_SPACE, **self.overrides}


PHASE_ONE = [
  Variant("causal_baseline", {}),
  Variant("hold_64", {"max_hold_bars": [64]}),
  Variant("hold_96", {"max_hold_bars": [96]}),
  Variant("spacing_8", {"min_bars_between": [8]}),
  Variant("spacing_12", {"min_bars_between": [12]}),
  Variant("atr_1_35", {"atr_multipliers": [1.35]}),
  Variant("atr_1_65", {"atr_multipliers": [1.65]}),
  Variant("rr_2_2", {"rr_ratios": [2.2]}),
  Variant("session_08_17", {"session_ranges": [[8, 17]]}),
  Variant("quality_filter", {
    "score_thresholds": [1.0, 1.6, 2.2, 2.8],
    "ml_probability_thresholds": [0.40, 0.44, 0.48, 0.52],
    "target_trades_per_week": 8.0,
    "drawdown_penalty": 2.0,
    "loss_streak_penalty": 3.0,
  }),
  Variant("regime_rules", {
    "include_session_regime_rules": True,
    "min_feature_samples": 100,
    "min_threshold_samples": 30,
    "min_binary_samples": 20,
  }),
  Variant("native_features", {}, "m15_native"),
]


def _trade_from_row(row: dict) -> Trade:
  return Trade(
    pd.Timestamp(row["entry"]), pd.Timestamp(row["exit"]),
    1 if row["dir"] == "LONG" else -1,
    float(row["entry_px"]), float(row["exit_px"]),
    float(row["sl"]), float(row["tp"]),
    float(row["pnl_pips"]), float(row["r"]), row["reason"],
  )


def _pack_metrics(rows: list[dict], start: pd.Timestamp, end: pd.Timestamp) -> dict:
  selected = [
    _trade_from_row(row) for row in rows
    if start <= pd.Timestamp(row["entry"]) < end
  ]
  metrics = compute_metrics(selected)
  weeks = max((end - start).total_seconds() / (7 * 86400), 1)
  total_r = float(metrics["total_r"])
  drawdown = float(metrics["max_drawdown_r"])
  return {
    "n_trades": int(metrics["n_trades"]),
    "trades_per_week": round(int(metrics["n_trades"]) / weeks, 3),
    "win_rate_pct": round(float(metrics["win_rate"]) * 100, 3),
    "avg_rr": round(float(metrics["avg_rr"]), 4),
    "profit_factor": round(float(metrics["profit_factor"]), 4),
    "total_r": round(total_r, 4),
    "max_drawdown_r": round(drawdown, 4),
    "risk_adjusted": round(total_r / max(drawdown, 0.5), 4),
    "max_loss_streak": int(metrics.get("max_loss_streak", 0)),
  }


def _summarize(report: dict, data_end: pd.Timestamp) -> dict:
  rows = report.get("trades") or []
  end = data_end + pd.Timedelta(minutes=15)
  return {
    "selection": _pack_metrics(rows, SELECT_FROM, HOLDOUT_FROM),
    "holdout": _pack_metrics(rows, HOLDOUT_FROM, end),
    "overall": report.get("overall_oos") or {},
  }


def _run_variant(payload: tuple[Variant, pd.DataFrame, dict, float, float]) -> dict:
  variant, df, model, spread, slippage = payload
  try:
    reset_kb_cache()
    space_dict = variant.space_dict()
    report = run_walk_forward(
      df,
      use_learning=bool(model.get("use_kb", True)),
      train_weeks=int(model.get("train_weeks") or 3),
      spread_pips=spread,
      slippage_pips=slippage,
      holdout_months=0,
      kb_profile=model.get("kb_profile"),
      kb_snapshot=model.get("kb_snapshot"),
      oos_from="2026-01-01",
      oos_to=None,
      feature_profile=variant.feature_profile,
      search_space=mining_search_space_from_dict(space_dict),
      verbose=False,
    )
    return {
      "name": variant.name,
      "feature_profile": variant.feature_profile,
      "overrides": variant.overrides,
      "mining_search_space": space_dict,
      "spread_pips": spread,
      "slippage_pips": slippage,
      "summary": _summarize(report, pd.Timestamp(df.index[-1])),
      "report": report,
      "error": None,
    }
  except Exception as exc:
    return {
      "name": variant.name,
      "feature_profile": variant.feature_profile,
      "overrides": variant.overrides,
      "spread_pips": spread,
      "slippage_pips": slippage,
      "error": f"{type(exc).__name__}: {exc}",
      "traceback": traceback.format_exc(),
    }


def _save_incremental(payload: dict) -> None:
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  RESULT_PATH.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8",
  )


def _run_batch(
  variants: list[Variant], df: pd.DataFrame, model: dict,
  spread: float = 1.0, slippage: float = 0.3,
) -> list[dict]:
  rows = []
  with ProcessPoolExecutor(max_workers=min(4, len(variants))) as pool:
    pending = {
      pool.submit(_run_variant, (variant, df, model, spread, slippage)): variant
      for variant in variants
    }
    for number, future in enumerate(as_completed(pending), 1):
      row = future.result()
      rows.append(row)
      print(
        f"[{number}/{len(variants)}] {row['name']} "
        f"{row.get('summary', {}).get('holdout', {}) or row.get('error')}",
        flush=True,
      )
  return rows


def _selection_score(row: dict) -> float:
  metrics = (row.get("summary") or {}).get("selection") or {}
  if (
    row.get("error")
    or float(metrics.get("total_r") or 0) <= 0
    or not 7 <= float(metrics.get("trades_per_week") or 0) <= 10
  ):
    return -1e12
  return (
    float(metrics.get("risk_adjusted") or 0)
    * (1 + float(metrics.get("win_rate_pct") or 0) / 100)
  )


def _combined_variants(phase_one: list[dict]) -> list[Variant]:
  eligible = [
    row for row in sorted(phase_one, key=_selection_score, reverse=True)
    if row["name"] != "causal_baseline" and _selection_score(row) > -1e11
  ][:3]
  combos: list[Variant] = []
  for left_index, left in enumerate(eligible):
    for right in eligible[left_index + 1:]:
      overlap = set(left["overrides"]) & set(right["overrides"])
      if any(left["overrides"][key] != right["overrides"][key] for key in overlap):
        continue
      profile = (
        "m15_native"
        if "m15_native" in (left["feature_profile"], right["feature_profile"])
        else "current"
      )
      combos.append(Variant(
        f"combo_{left['name']}__{right['name']}",
        {**left["overrides"], **right["overrides"]},
        profile,
      ))
  combos.extend([
    Variant("balanced_current", {
      "rr_ratios": [2.2],
      "atr_multipliers": [1.35],
      "max_hold_bars": [64],
      "min_bars_between": [8],
      "session_ranges": [[8, 17]],
      "score_thresholds": [1.0, 1.6, 2.2],
      "ml_probability_thresholds": [0.40, 0.44, 0.48],
      "include_session_regime_rules": True,
      "min_feature_samples": 100,
      "min_threshold_samples": 30,
      "min_binary_samples": 20,
      "target_trades_per_week": 8.0,
      "drawdown_penalty": 2.0,
      "loss_streak_penalty": 3.0,
    }),
    Variant("balanced_native", {
      "rr_ratios": [2.2],
      "atr_multipliers": [1.35],
      "max_hold_bars": [64],
      "min_bars_between": [8],
      "session_ranges": [[8, 17]],
      "score_thresholds": [1.0, 1.6, 2.2],
      "ml_probability_thresholds": [0.40, 0.44, 0.48],
      "include_session_regime_rules": True,
      "min_feature_samples": 100,
      "min_threshold_samples": 30,
      "min_binary_samples": 20,
      "target_trades_per_week": 8.0,
      "drawdown_penalty": 2.0,
      "loss_streak_penalty": 3.0,
    }, "m15_native"),
  ])
  by_name = {variant.name: variant for variant in combos}
  return list(by_name.values())[:5]


def _promotion_gates(
  candidate: dict, baseline: dict, frozen: dict, stress: dict | None,
) -> dict:
  holdout = candidate["summary"]["holdout"]
  base_holdout = baseline["summary"]["holdout"]
  frozen_holdout = frozen["holdout"]
  wr_floor = max(
    float(base_holdout["win_rate_pct"]), float(frozen_holdout["win_rate_pct"]),
  ) + 2.0
  r_floor = max(
    float(base_holdout["total_r"]), float(frozen_holdout["total_r"]),
  )
  dd_ceiling = max(
    float(base_holdout["max_drawdown_r"]), float(frozen_holdout["max_drawdown_r"]),
  ) * 1.10
  risk_floor = max(
    float(base_holdout["risk_adjusted"]), float(frozen_holdout["risk_adjusted"]),
  )
  stress_h = (stress or {}).get("summary", {}).get("holdout", {})
  gates = {
    "frequency_7_to_10": 7 <= float(holdout["trades_per_week"]) <= 10,
    "win_rate_plus_2pp": float(holdout["win_rate_pct"]) >= wr_floor,
    "total_r_above_baseline": float(holdout["total_r"]) > r_floor,
    "drawdown_within_10pct": float(holdout["max_drawdown_r"]) <= dd_ceiling,
    "risk_adjusted_not_worse": float(holdout["risk_adjusted"]) >= risk_floor,
    "stress_profitable": float(stress_h.get("total_r") or 0) > 0,
    "stress_frequency_7_to_10": 7 <= float(stress_h.get("trades_per_week") or 0) <= 10,
  }
  return {
    "thresholds": {
      "win_rate_pct": round(wr_floor, 3),
      "total_r": round(r_floor, 3),
      "max_drawdown_r": round(dd_ceiling, 3),
      "risk_adjusted": round(risk_floor, 3),
    },
    "checks": gates,
    "passed": all(gates.values()),
  }


def main() -> int:
  model_id = load_active_model_id()
  model_report = load_model_report(model_id)
  if not model_id or not model_report:
    raise RuntimeError("An active M15 model and report are required.")
  model = {
    "id": model_id,
    "train_weeks": model_report["config"]["train_weeks"],
    "use_kb": model_report["config"]["use_learning_kb"],
    "kb_profile": model_report["config"]["kb_profile"],
    "kb_snapshot": model_report["config"]["kb_snapshot"],
  }
  df = load_eurusd_m15("2025-01-01").copy()
  data_end = pd.Timestamp(df.index[-1])
  fingerprint = hashlib.sha256(
    pd.util.hash_pandas_object(df, index=True).values.tobytes(),
  ).hexdigest()
  frozen = _summarize(model_report, pd.Timestamp(model_report["trades"][-1]["exit"]))
  payload = {
    "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "status": "running",
    "active_model_id": model_id,
    "data_fingerprint": fingerprint,
    "data_end": str(data_end),
    "selection_window": [str(SELECT_FROM), str(HOLDOUT_FROM)],
    "holdout_window": [str(HOLDOUT_FROM), str(data_end)],
    "frozen_active": frozen,
    "phase_one": [],
    "phase_two": [],
  }
  _save_incremental(payload)

  phase_one = _run_batch(PHASE_ONE, df, model)
  payload["phase_one"] = [{k: v for k, v in row.items() if k != "report"} for row in phase_one]
  _save_incremental(payload)

  phase_two_variants = _combined_variants(phase_one)
  phase_two = _run_batch(phase_two_variants, df, model)
  payload["phase_two"] = [{k: v for k, v in row.items() if k != "report"} for row in phase_two]
  _save_incremental(payload)

  successful = [row for row in phase_one + phase_two if not row.get("error")]
  baseline = next(row for row in phase_one if row["name"] == "causal_baseline")
  candidates = [row for row in successful if row["name"] != "causal_baseline"]
  # The holdout remains untouched: final candidate selection uses Jan-Apr only.
  candidates.sort(key=_selection_score, reverse=True)
  winner = candidates[0] if candidates else baseline
  winner_variant = Variant(
    winner["name"], winner["overrides"], winner["feature_profile"],
  )
  stress = _run_batch([winner_variant], df, model, spread=1.5, slippage=0.5)[0]
  gates = _promotion_gates(winner, baseline, frozen, stress)

  REPORTS_DIR.mkdir(parents=True, exist_ok=True)
  for row in (baseline, winner, stress):
    if row.get("report"):
      suffix = "stress" if row is stress else "base"
      (REPORTS_DIR / f"{row['name']}_{suffix}.json").write_text(
        json.dumps(row["report"], indent=2, ensure_ascii=False), encoding="utf-8",
      )

  payload.update({
    "status": "completed",
    "completed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "recommended": {k: v for k, v in winner.items() if k != "report"},
    "stress": {k: v for k, v in stress.items() if k != "report"},
    "promotion": gates,
  })
  _save_incremental(payload)
  print(json.dumps({
    "recommended": winner["name"],
    "holdout": winner["summary"]["holdout"],
    "promotion": gates,
  }, ensure_ascii=False, indent=2), flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
