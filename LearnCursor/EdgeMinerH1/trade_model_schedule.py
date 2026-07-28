"""Trade Model weekly schedule — freeze OOS genomes for Live/Simulate parity.

Health/OOS walks produce ``{model_id}_schedule.json``. BridgeEngine prefers
those weekly genomes over re-mining. Unseen future weeks remine once and append
to ``{model_id}_live_weeks.json``.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pandas as pd

from strategy_miner import MinedStrategy, Rule, _label_outcomes

REPORT_DIR = Path(__file__).resolve().parent / "results"
MODELS_DIR = REPORT_DIR / "trade_models"
_lock = threading.RLock()


def model_schedule_path(model_id: str) -> Path:
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  return MODELS_DIR / f"{model_id}_schedule.json"


def model_live_weeks_path(model_id: str) -> Path:
  MODELS_DIR.mkdir(parents=True, exist_ok=True)
  return MODELS_DIR / f"{model_id}_live_weeks.json"


def full_strategy_dict(s: MinedStrategy) -> dict:
  """Serialize full genome (no rounding) for reproducible hydrate."""
  def rules_to_list(rules: list[Rule]) -> list[dict]:
    return [
      {
        "feat": r.feature,
        "direction": r.direction,
        "op": r.op,
        "thr": float(r.threshold),
        "w": float(r.weight),
      }
      for r in rules
    ]

  return {
    "name": s.name,
    "exit_mode": s.exit_mode,
    "ml_prob_min": float(s.ml_prob_min),
    "rr": float(s.rr_ratio),
    "atr_mult": float(s.atr_mult_sl),
    "score_threshold": float(s.score_threshold),
    "atr_mult_sl": float(s.atr_mult_sl),
    "rr_ratio": float(s.rr_ratio),
    "min_rules_match": int(s.min_rules_match),
    "max_trades_per_week": int(s.max_trades_per_week),
    "min_bars_between": int(s.min_bars_between),
    "max_hold_bars": int(s.max_hold_bars),
    "partial_pct": float(s.partial_pct),
    "partial_at_r": float(s.partial_at_r),
    "trail_activate_r": float(s.trail_activate_r),
    "trail_distance_r": float(s.trail_distance_r),
    "session_filter": bool(s.session_filter),
    "long_rules": rules_to_list(s.long_rules),
    "short_rules": rules_to_list(s.short_rules),
  }


def strategy_from_dict(g: dict) -> MinedStrategy:
  """Hydrate MinedStrategy from schedule / report genome (ml_scorer=None)."""
  def des_rules(rules: list | None, default_dir: str) -> list[Rule]:
    out: list[Rule] = []
    for r in rules or []:
      feat = r.get("feat", r.get("feature"))
      op = r.get("op")
      thr = float(r.get("thr", r.get("threshold", 0.0)))
      w = float(r.get("w", r.get("weight", 1.0)))
      direction = str(r.get("direction") or default_dir)
      out.append(Rule(str(feat), direction, str(op), thr, w))
    return out

  rr = float(g.get("rr_ratio", g.get("rr", 2.5)))
  atr = float(g.get("atr_mult_sl", g.get("atr_mult", 0.9)))
  return MinedStrategy(
    long_rules=des_rules(g.get("long_rules"), "long"),
    short_rules=des_rules(g.get("short_rules"), "short"),
    score_threshold=float(g.get("score_threshold", 2.0)),
    atr_mult_sl=atr,
    rr_ratio=rr,
    max_hold_bars=int(g.get("max_hold_bars", 36)),
    min_bars_between=int(g.get("min_bars_between", 4)),
    min_rules_match=int(g.get("min_rules_match", 2)),
    max_trades_per_week=int(g.get("max_trades_per_week", 2)),
    ml_prob_min=float(g.get("ml_prob_min", 0.40)),
    exit_mode=str(g.get("exit_mode", "hybrid")),
    partial_pct=float(g.get("partial_pct", 0.4)),
    partial_at_r=float(g.get("partial_at_r", 1.2)),
    trail_activate_r=float(g.get("trail_activate_r", 1.8)),
    trail_distance_r=float(g.get("trail_distance_r", 0.6)),
    session_filter=bool(g.get("session_filter", True)),
    ml_scorer=None,
    name=str(g.get("name", "scheduled")),
  )


def attach_ml_scorer(
  strat: MinedStrategy,
  fm,
  train_start: int,
  train_end: int,
  *,
  kb=None,
  as_of=None,
) -> MinedStrategy:
  """Retrain ML on the week train window and attach (matches meta_learner path)."""
  from meta_learner import _fit_ml_with_experience
  from knowledge_base import KnowledgeBase

  rr, atr_m = float(strat.rr_ratio), float(strat.atr_mult_sl)
  if kb is not None and getattr(kb, "genomes", None):
    try:
      top = kb.top_genomes(1)[0]
      rr = float(top.get("rr_ratio", rr))
      atr_m = float(top.get("atr_mult_sl", atr_m))
    except Exception:
      pass

  long_wins, short_wins = _label_outcomes(fm, train_start, train_end, rr, atr_m)
  if isinstance(kb, KnowledgeBase):
    ml = _fit_ml_with_experience(
      fm, train_start, train_end, long_wins, short_wins, kb, as_of=as_of,
    )
  else:
    from ml_scorer import MLScorer
    ml = MLScorer()
    ml.fit(fm, train_start, train_end, long_wins, short_wins)

  strat.ml_scorer = ml
  return strat


def build_schedule_payload(
  *,
  model_id: str | None,
  weekly_entries: list[dict],
  config: dict | None,
  data_fingerprint: str | None = None,
  overall: dict | None = None,
  source: str = "walk_forward",
) -> dict:
  return {
    "meta": {
      "source": source,
      "model_id": model_id,
      "data_fingerprint": data_fingerprint,
      "config": dict(config or {}),
      "n_weeks": len(weekly_entries),
      "overall": overall,
    },
    "weekly": weekly_entries,
  }


def week_entry_from_strategy(
  *,
  week_start,
  week_end=None,
  strat: MinedStrategy,
  train_start_idx: int,
  train_end_idx: int,
  oos_trades: int | None = None,
  oos_r: float | None = None,
  oos_wr: float | None = None,
) -> dict:
  ws = str(pd.Timestamp(week_start).date())
  entry: dict[str, Any] = {
    "week_start": ws,
    "strategy": full_strategy_dict(strat),
    "train_start_idx": int(train_start_idx),
    "train_end_idx": int(train_end_idx),
  }
  if week_end is not None:
    entry["week_end"] = str(pd.Timestamp(week_end).date())
  if oos_trades is not None:
    entry["oos_trades"] = int(oos_trades)
  if oos_r is not None:
    entry["oos_r"] = float(oos_r)
  if oos_wr is not None:
    entry["oos_wr"] = float(oos_wr)
  return entry


def _read_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as handle:
      data = json.load(handle)
    return data if isinstance(data, dict) else None
  except Exception:
    return None


def _write_json(path: Path, data: dict) -> Path:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2, ensure_ascii=False)
  tmp.replace(path)
  return path


def save_model_schedule(model_id: str, payload: dict) -> Path:
  meta = dict(payload.get("meta") or {})
  meta["model_id"] = model_id
  out = dict(payload)
  out["meta"] = meta
  return _write_json(model_schedule_path(model_id), out)


def load_model_schedule(model_id: str) -> dict | None:
  return _read_json(model_schedule_path(model_id))


def load_live_weeks(model_id: str) -> dict | None:
  return _read_json(model_live_weeks_path(model_id))


def _index_weekly(payload: dict | None) -> dict[str, dict]:
  if not payload:
    return {}
  out: dict[str, dict] = {}
  for row in payload.get("weekly") or []:
    if not isinstance(row, dict):
      continue
    ws = row.get("week_start")
    if not ws or "strategy" not in row:
      continue
    out[str(ws)[:10]] = row
  return out


def lookup_week_strategy(model_id: str, week_start) -> dict | None:
  """Return schedule week entry (OOS schedule first, then live_weeks)."""
  key = str(pd.Timestamp(week_start).date())
  sched = _index_weekly(load_model_schedule(model_id))
  if key in sched:
    return sched[key]
  live = _index_weekly(load_live_weeks(model_id))
  return live.get(key)


def append_live_week(model_id: str, week_entry: dict) -> Path:
  """Append or replace a future week genome without touching OOS schedule."""
  with _lock:
    path = model_live_weeks_path(model_id)
    data = _read_json(path) or {"meta": {"model_id": model_id, "source": "live_remine"}, "weekly": []}
    weekly = list(data.get("weekly") or [])
    ws = str(week_entry.get("week_start") or "")[:10]
    weekly = [w for w in weekly if str(w.get("week_start") or "")[:10] != ws]
    weekly.append(week_entry)
    weekly.sort(key=lambda w: str(w.get("week_start") or ""))
    data["weekly"] = weekly
    data["meta"] = {
      **(data.get("meta") or {}),
      "model_id": model_id,
      "source": "live_remine",
      "n_weeks": len(weekly),
    }
    return _write_json(path, data)


def schedule_from_walk_forward_result(result: dict, model_id: str | None = None) -> dict | None:
  """Extract schedule payload embedded in a walk-forward result."""
  weekly = result.get("schedule_weekly")
  if not weekly:
    return None
  cfg = result.get("config") or {}
  mid = model_id or cfg.get("trade_model_id")
  return build_schedule_payload(
    model_id=mid,
    weekly_entries=list(weekly),
    config=cfg,
    data_fingerprint=(result.get("data_source") or {}).get("fingerprint")
    or cfg.get("data_fingerprint"),
    overall=result.get("overall_oos"),
    source="walk_forward",
  )
