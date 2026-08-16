"""Compare AIEdge vs TrainApp on locked test window metrics."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aiapp.config import Desk, load_protocol


def _passes_filter(row: dict, *, wr=50, rr=2.5, total_r=100, dd=10) -> bool:
  try:
    return (
      float(row.get("win_rate_pct") or 0) > wr
      and float(row.get("avg_rr") or 0) > rr
      and float(row.get("total_r") or 0) > total_r
      and float(row.get("max_drawdown_r") or 999) < dd
    )
  except Exception:
    return False


def _robust(total_r: float, dd: float, wr: float) -> float:
  return (total_r / max(dd, 1.0)) - 0.05 * max(0.0, 55.0 - wr)


def stress_metrics(
  metrics: dict,
  *,
  trainapp_spread: float,
  aiedge_spread: float,
  sl_pips_est: float = 18.0,
) -> dict:
  """Haircut TrainApp OOS metrics for extra spread vs AIEdge cost model.

  TrainApp backtests typically assume ~1.0/1.5 pip. AIEdge uses higher realistic
  spreads; without re-simulating genomes we approximate round-trip extra cost in R.
  """
  m = dict(metrics or {})
  n = float(m.get("n_trades") or 0)
  extra = max(0.0, float(aiedge_spread) - float(trainapp_spread))
  # round-trip ≈ 2 * extra pips; convert to R via typical SL width
  penalty = n * (2.0 * extra) / max(sl_pips_est, 1.0)
  tot = float(m.get("total_r") or 0) - penalty
  dd = float(m.get("max_drawdown_r") or 0) + 0.25 * penalty
  wr = float(m.get("win_rate_pct") or 0)
  m["total_r"] = round(tot, 3)
  m["max_drawdown_r"] = round(dd, 3)
  m["robust_score"] = round(_robust(tot, dd, wr), 3)
  m["cost_penalty_r"] = round(penalty, 3)
  m["assumed_trainapp_spread"] = trainapp_spread
  m["aiedge_spread"] = aiedge_spread
  return m


def load_trainapp_baseline(desk: Desk) -> dict[str, Any]:
  root = desk.trainapp_runtime
  latest = root / "results" / "grid_search" / "latest.json"
  models_path = root / "results" / "trade_models.json"
  out: dict[str, Any] = {
    "source": None,
    "label": None,
    "metrics_raw": None,
    "metrics": None,
    "note": "Raw TrainApp OOS + cost-stressed metrics for fairer compare",
  }
  rows: list[dict] = []
  run_id = None
  if latest.exists():
    payload = json.loads(latest.read_text(encoding="utf-8"))
    run_id = payload.get("run_id")
    rows = [r for r in (payload.get("rows") or []) if not r.get("error")]

  hits = [r for r in rows if _passes_filter(r)]
  pool = hits if hits else rows
  if pool:
    best = max(
      pool,
      key=lambda r: _robust(
        float(r.get("total_r") or 0),
        float(r.get("max_drawdown_r") or 1),
        float(r.get("win_rate_pct") or 0),
      ),
    )
    raw = {
      "n_trades": best.get("n_trades"),
      "total_r": best.get("total_r"),
      "win_rate_pct": best.get("win_rate_pct"),
      "avg_rr": best.get("avg_rr"),
      "max_drawdown_r": best.get("max_drawdown_r"),
      "profit_factor": best.get("profit_factor"),
      "robust_score": round(
        _robust(
          float(best.get("total_r") or 0),
          float(best.get("max_drawdown_r") or 1),
          float(best.get("win_rate_pct") or 0),
        ),
        3,
      ),
    }
    ta_spread = 1.5 if "GBP" in desk.pair.upper() else 1.0
    stressed = stress_metrics(
      raw, trainapp_spread=ta_spread, aiedge_spread=desk.spread_pips
    )
    out.update(
      {
        "source": f"grid:{run_id}",
        "label": best.get("label") or best.get("key"),
        "metrics_raw": raw,
        "metrics": stressed,  # primary compare uses stressed
        "filter_hits_in_grid": len(hits),
        "grid_ok_rows": len(rows),
      }
    )

  if models_path.exists():
    raw = json.loads(models_path.read_text(encoding="utf-8"))
    models = raw if isinstance(raw, list) else raw.get("models") or raw.get("trade_models") or []
    filt = [m for m in models if "Filt" in str(m.get("label") or "")]
    out["promoted_filt_count"] = len(filt)
  return out


def decide_winner(ai: dict, baseline: dict) -> dict[str, Any]:
  am = ai or {}
  bm = (baseline or {}).get("metrics") or {}
  a_score = float(am.get("robust_score") or -1e9)
  b_score = float(bm.get("robust_score") or -1e9)
  a_r = float(am.get("total_r") or 0)
  b_r = float(bm.get("total_r") or 0)
  a_dd = float(am.get("max_drawdown_r") or 999)
  b_dd = float(bm.get("max_drawdown_r") or 999)

  reason = []
  if a_score > b_score and a_dd <= b_dd + 2.0:
    winner = "AIEdge"
    reason.append("higher robust_score with DD not materially worse (+2R tolerance)")
  elif a_score > b_score and a_r >= b_r:
    winner = "AIEdge"
    reason.append("higher robust_score and total_r")
  elif b_score > a_score and b_dd <= a_dd + 2.0:
    winner = "TrainApp"
    reason.append("TrainApp higher robust_score with DD tolerance")
  elif a_r > b_r and a_dd <= b_dd:
    winner = "AIEdge"
    reason.append("higher total_r with DD <= baseline")
  elif b_r > a_r and b_dd <= a_dd:
    winner = "TrainApp"
    reason.append("TrainApp higher total_r with DD <= candidate")
  else:
    winner = "AIEdge" if a_score >= b_score else "TrainApp"
    reason.append("fallback robust_score comparison")

  return {
    "winner": winner,
    "reason": "; ".join(reason),
    "aiedge_robust": a_score,
    "trainapp_robust_stressed": b_score,
    "trainapp_robust_raw": float(((baseline or {}).get("metrics_raw") or {}).get("robust_score") or 0),
    "aiedge_total_r": a_r,
    "trainapp_total_r_stressed": b_r,
    "aiedge_dd": a_dd,
    "trainapp_dd_stressed": b_dd,
    "caveat": (
      "Primary TrainApp baseline is cost-stressed to AIEdge spreads. "
      "AIEdge test metrics were not used for selection."
    ),
  }


def compare_desk(desk: Desk, aiedge_model: dict) -> dict[str, Any]:
  baseline = load_trainapp_baseline(desk)
  ai_metrics = aiedge_model.get("test") or {}
  decision = decide_winner(ai_metrics, baseline)
  return {
    "desk": desk.id,
    "pair": desk.pair,
    "tf": desk.tf,
    "aiedge_cost_spread_pips": desk.spread_pips,
    "aiedge": aiedge_model,
    "trainapp_baseline": baseline,
    "decision": decision,
  }
