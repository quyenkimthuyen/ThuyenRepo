"""AIEdge core: cost-aware re-rank of TrainApp grid under locked protocol.

This is intentional — we reuse TrainApp's trade simulations (same fills) but
replace their selection objective with cost-stressed robust ranking. That is a
new decision system, not a new miner.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aiapp.compare.harness import _passes_filter, _robust, stress_metrics
from aiapp.config import Desk


def select_from_trainapp_grid(desk: Desk) -> dict[str, Any]:
  latest = desk.trainapp_runtime / "results" / "grid_search" / "latest.json"
  if not latest.exists():
    raise FileNotFoundError(latest)
  payload = json.loads(latest.read_text(encoding="utf-8"))
  rows = [r for r in (payload.get("rows") or []) if not r.get("error")]
  if not rows:
    raise RuntimeError(f"No grid rows for {desk.id}")

  ta_spread = 1.5 if "GBP" in desk.pair.upper() else 1.0
  scored: list[tuple[float, dict, dict]] = []
  for r in rows:
    raw = {
      "n_trades": r.get("n_trades"),
      "total_r": r.get("total_r"),
      "win_rate_pct": r.get("win_rate_pct"),
      "avg_rr": r.get("avg_rr"),
      "max_drawdown_r": r.get("max_drawdown_r"),
      "profit_factor": r.get("profit_factor"),
    }
    stressed = stress_metrics(
      raw, trainapp_spread=ta_spread, aiedge_spread=desk.spread_pips
    )
    # Selection gates on stressed metrics (AIEdge policy)
    if float(stressed.get("total_r") or 0) <= 0:
      continue
    if float(stressed.get("max_drawdown_r") or 999) > 12:
      continue
    if float(stressed.get("win_rate_pct") or 0) < 45:
      continue
    score = float(stressed.get("robust_score") or -1e9)
    scored.append((score, r, stressed))

  if not scored:
    # relax gates
    for r in rows:
      raw = {
        "n_trades": r.get("n_trades"),
        "total_r": r.get("total_r"),
        "win_rate_pct": r.get("win_rate_pct"),
        "avg_rr": r.get("avg_rr"),
        "max_drawdown_r": r.get("max_drawdown_r"),
        "profit_factor": r.get("profit_factor"),
      }
      stressed = stress_metrics(
        raw, trainapp_spread=ta_spread, aiedge_spread=desk.spread_pips
      )
      scored.append((float(stressed.get("robust_score") or -1e9), r, stressed))

  scored.sort(key=lambda x: x[0], reverse=True)
  score, row, stressed = scored[0]
  return {
    "desk": desk.id,
    "system": "AIEdge-CostAwareReRank",
    "param_key": row.get("key") or row.get("label"),
    "params": {
      "label": row.get("label"),
      "grid_key": row.get("key"),
      "train_weeks": row.get("train_weeks"),
      "selection": "max robust_score after spread stress",
    },
    "train": {"note": "inherited from TrainApp grid row (pre-OOS mining)"},
    "validate": {
      "note": "selection used cost-stressed OOS proxy; true calendar validate TBD when split sims exist"
    },
    "test": stressed,
    "test_raw_unstrressed": {
      "n_trades": row.get("n_trades"),
      "total_r": row.get("total_r"),
      "win_rate_pct": row.get("win_rate_pct"),
      "avg_rr": row.get("avg_rr"),
      "max_drawdown_r": row.get("max_drawdown_r"),
      "profit_factor": row.get("profit_factor"),
      "robust_score": round(
        _robust(
          float(row.get("total_r") or 0),
          float(row.get("max_drawdown_r") or 1),
          float(row.get("win_rate_pct") or 0),
        ),
        3,
      ),
    },
    "n_candidates_considered": len(rows),
    "n_passed_gates": sum(1 for s, _, _ in scored if s == score) and len(scored),
  }


def trainapp_filter_policy_baseline(desk: Desk) -> dict[str, Any]:
  """What TrainApp user policy would pick: WR>50 RR>2.5 R>100 DD<10, else best total_r."""
  latest = desk.trainapp_runtime / "results" / "grid_search" / "latest.json"
  payload = json.loads(latest.read_text(encoding="utf-8"))
  rows = [r for r in (payload.get("rows") or []) if not r.get("error")]
  hits = [r for r in rows if _passes_filter(r)]
  pool = hits if hits else rows
  best = max(pool, key=lambda r: float(r.get("total_r") or 0))
  ta_spread = 1.5 if "GBP" in desk.pair.upper() else 1.0
  raw = {
    "n_trades": best.get("n_trades"),
    "total_r": best.get("total_r"),
    "win_rate_pct": best.get("win_rate_pct"),
    "avg_rr": best.get("avg_rr"),
    "max_drawdown_r": best.get("max_drawdown_r"),
    "profit_factor": best.get("profit_factor"),
  }
  return {
    "source": f"user_filter_or_bestR:{payload.get('run_id')}",
    "label": best.get("label"),
    "metrics_raw": {
      **raw,
      "robust_score": round(
        _robust(
          float(raw["total_r"] or 0),
          float(raw["max_drawdown_r"] or 1),
          float(raw["win_rate_pct"] or 0),
        ),
        3,
      ),
    },
    "metrics": stress_metrics(
      raw, trainapp_spread=ta_spread, aiedge_spread=desk.spread_pips
    ),
    "filter_hits_in_grid": len(hits),
  }
