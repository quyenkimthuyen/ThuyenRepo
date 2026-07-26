"""Edge improvements: health gate, Live↔OOS feedback, risk governor, search space."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from run_backtest import REPORT_DIR
from strategy_miner import MiningSearchSpace, mining_search_space_to_dict

FEEDBACK_PATH = REPORT_DIR / "live_oos_feedback.json"
PROMOTION_LOG = REPORT_DIR / "model_promotion_log.jsonl"


def improved_mining_search_space() -> MiningSearchSpace:
  """Tighter sessions + regime rules + mild DD/streak penalties (WR/R focus)."""
  return MiningSearchSpace(
    rr_ratios=(2.5, 3.0),
    atr_multipliers=(0.9, 1.05),
    max_hold_bars=(96,),
    min_bars_between=(12, 16),
    session_ranges=((7, 20), (8, 17), (12, 21)),
    session_filters=(True,),
    score_thresholds=(0.6, 1.0, 1.6, 2.2),
    min_rules_matches=(1, 2),
    ml_probability_thresholds=(0.36, 0.40, 0.44, 0.48),
    include_session_regime_rules=True,
    drawdown_penalty=0.15,
    loss_streak_penalty=0.10,
  )


def alternate_mining_search_spaces() -> list[tuple[str, MiningSearchSpace]]:
  """Variants for multi-pass search (session / spacing / ML gate)."""
  base = improved_mining_search_space()
  # Close to current M15 champion (08–17 · spacing_16) + regime/DD
  champion_plus = MiningSearchSpace(
    rr_ratios=(2.5, 3.0),
    atr_multipliers=(0.9, 1.05),
    max_hold_bars=(96,),
    min_bars_between=(16,),
    session_ranges=((8, 17),),
    session_filters=(True,),
    score_thresholds=(0.6, 1.0, 1.6, 2.2),
    min_rules_matches=(1, 2),
    ml_probability_thresholds=(0.36, 0.40, 0.44, 0.48),
    include_session_regime_rules=True,
    drawdown_penalty=0.15,
    loss_streak_penalty=0.10,
  )
  tight = MiningSearchSpace(
    rr_ratios=(2.5, 3.0),
    atr_multipliers=(0.9, 1.05),
    max_hold_bars=(96,),
    min_bars_between=(16, 20),
    session_ranges=((8, 17), (12, 20)),
    session_filters=(True,),
    score_thresholds=(1.0, 1.6, 2.2),
    min_rules_matches=(1, 2),
    ml_probability_thresholds=(0.40, 0.44, 0.48, 0.52),
    include_session_regime_rules=True,
    drawdown_penalty=0.22,
    loss_streak_penalty=0.15,
  )
  london_ny = MiningSearchSpace(
    rr_ratios=(2.5, 3.0),
    atr_multipliers=(0.9, 1.05),
    max_hold_bars=(96,),
    min_bars_between=(12, 16),
    session_ranges=((7, 16), (12, 21)),
    session_filters=(True,),
    score_thresholds=(0.6, 1.0, 1.6, 2.2),
    min_rules_matches=(2,),
    ml_probability_thresholds=(0.36, 0.40, 0.44, 0.48),
    include_session_regime_rules=True,
    drawdown_penalty=0.18,
    loss_streak_penalty=0.12,
  )
  return [
    ("champion_plus_v0", champion_plus),
    ("improved_v1", base),
    ("tight_session_v2", tight),
    ("london_ny_v3", london_ny),
  ]


def improved_search_space_dict() -> dict:
  return mining_search_space_to_dict(improved_mining_search_space())


def assess_model_health(model_id: str | None) -> dict[str, Any]:
  from gui.model_health import assess_monthly_degradation, monthly_oos_from_report
  from gui.trade_model import load_model_report

  if not model_id:
    return {"verdict": "insufficient", "message": "no model"}
  report = load_model_report(model_id)
  monthly = monthly_oos_from_report(report)
  assess = assess_monthly_degradation(monthly, baseline=None)
  overall = (report or {}).get("overall_oos") or {}
  assess["model_id"] = model_id
  assess["total_r"] = overall.get("total_r")
  assess["win_rate_pct"] = overall.get("win_rate_pct")
  assess["n_trades"] = overall.get("n_trades")
  assess["max_drawdown_r"] = overall.get("max_drawdown_r")
  return assess


def risk_pct_for_bridge(
  base_risk_pct: float,
  bridge_dir=None,
  *,
  lookback_trades: int = 40,
) -> float:
  """Scale risk down when recent auto equity is in drawdown (portfolio governor)."""
  base = max(0.1, float(base_risk_pct))
  try:
    from mt5_bridge.trade_journal import MODE_AUTO, filter_trades, load_trades

    trades = filter_trades(load_trades(bridge_dir), mode=MODE_AUTO)
    closed = [t for t in trades if str(t.get("status") or "").upper() == "CLOSED"]
    if len(closed) < 5:
      return base
    recent = closed[-lookback_trades:]
    eq = peak = 0.0
    max_dd = 0.0
    for t in recent:
      r = t.get("r")
      if r is None:
        continue
      eq += float(r)
      peak = max(peak, eq)
      max_dd = min(max_dd, eq - peak)
    # max_dd is ≤ 0
    dd = abs(max_dd)
    if dd >= 12:
      return round(base * 0.4, 3)
    if dd >= 8:
      return round(base * 0.6, 3)
    if dd >= 5:
      return round(base * 0.8, 3)
    return base
  except Exception:
    return base


def build_live_oos_feedback(
  *,
  model_id: str | None = None,
  bridge_dir=None,
  source: str = "live",
) -> dict[str, Any]:
  """Compare journal auto R vs Health OOS weekly_log (same calendar weeks)."""
  from gui.trade_model import get_active_trade_model, load_model_report
  from mt5_bridge.protocol import BRIDGE_DIR, BRIDGE_SIM_DIR
  from mt5_bridge.trade_journal import MODE_AUTO, filter_trades, load_trades

  model = get_active_trade_model() if not model_id else None
  mid = model_id or (model or {}).get("id")
  report = load_model_report(mid) if mid else None
  bdir = bridge_dir or (BRIDGE_SIM_DIR if source == "sim" else BRIDGE_DIR)

  weekly = []
  for w in (report or {}).get("weekly_log") or []:
    if "oos_r" not in w:
      continue
    weekly.append({
      "week_start": str(w.get("week_start"))[:10],
      "oos_r": float(w["oos_r"]),
      "oos_trades": int(w.get("oos_trades") or 0),
      "strategy": w.get("strategy"),
    })

  trades = filter_trades(
    load_trades(bdir), mode=MODE_AUTO, use_exit_time=(source != "sim"),
  )
  closed = [t for t in trades if str(t.get("status") or "").upper() == "CLOSED"]
  by_week: dict[str, list[float]] = {}
  for t in closed:
    et = t.get("entry_time") or t.get("bar_time")
    if not et:
      continue
    try:
      ts = pd.Timestamp(str(et).replace(".", "-", 2) if str(et)[4:5] == "." else et)
      week = str((ts - pd.Timedelta(days=int(ts.weekday()))).date())
    except Exception:
      continue
    r = t.get("r")
    if r is None:
      continue
    by_week.setdefault(week, []).append(float(r))

  rows = []
  for w in weekly:
    ws = w["week_start"]
    live_rs = by_week.get(ws) or []
    live_r = round(sum(live_rs), 3) if live_rs else None
    edge = None if live_r is None else round(live_r - w["oos_r"], 3)
    rows.append({
      **w,
      "live_r": live_r,
      "live_n": len(live_rs),
      "edge_r": edge,
    })

  edges = [r["edge_r"] for r in rows if r.get("edge_r") is not None]
  out = {
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "model_id": mid,
    "source": source,
    "bridge_dir": str(bdir),
    "n_weeks_compared": len(edges),
    "sum_edge_r": round(sum(edges), 3) if edges else None,
    "mean_edge_r": round(sum(edges) / len(edges), 3) if edges else None,
    "suggestions": _suggestions_from_edges(rows),
    "weeks": rows[-16:],
  }
  FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
  FEEDBACK_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  return out


def _suggestions_from_edges(rows: list[dict]) -> list[str]:
  tips: list[str] = []
  weak = [r for r in rows if r.get("edge_r") is not None and r["edge_r"] <= -3]
  if len(weak) >= 3:
    tips.append(
      "≥3 tuần Live/Sim yếu hơn OOS ≥3R — kiểm tra remine parity, session filter, "
      "hoặc Grid lại với KB snapshot khác."
    )
  if any(r.get("live_n", 0) == 0 and (r.get("oos_trades") or 0) > 0 for r in rows[-8:]):
    tips.append("Có tuần OOS có lệnh nhưng journal trống — Bridge service / EA chưa fill.")
  neg_oos = [r for r in rows if (r.get("oos_r") or 0) < -2 and (r.get("live_r") or 0) < -2]
  if len(neg_oos) >= 2:
    tips.append("Nhiều tuần cả OOS lẫn Live âm — cân nhắc siết session / tăng min_bars_between.")
  if not tips:
    tips.append("Chưa có tín hiệu suy giảm rõ từ Live↔OOS — giữ model, theo dõi Health.")
  return tips


def maybe_promote_grid_best(
  *,
  objective: str = "risk_adjusted",
  require_better_than_active: bool = True,
  set_active: bool = True,
) -> dict[str, Any]:
  """Promote latest grid best if healthier / better score than active model."""
  from gui.grid_search_engine import _score, apply_best_to_profile, load_latest_grid_run
  from gui.trade_model import get_active_trade_model, load_model_report

  run = load_latest_grid_run()
  if not run or not (run.get("rows") or run.get("best")):
    return {"ok": False, "reason": "no_grid_best"}

  rows = [r for r in (run.get("rows") or []) if not r.get("error")]
  if not rows and run.get("best") and not run["best"].get("error"):
    rows = [run["best"]]
  if not rows:
    return {"ok": False, "reason": "no_grid_best"}

  # Prefer risk_adjusted winners, but among near-ties pick higher total_r.
  def _pick(rows_in: list[dict]) -> dict:
    scored = []
    for r in rows_in:
      sc = float(_score(r, objective))
      if sc <= -1e11:
        continue
      scored.append((sc, float(r.get("total_r") or 0), r))
    if not scored:
      # Fallback: best total_r with positive R
      pos = [r for r in rows_in if float(r.get("total_r") or 0) > 0]
      return max(pos, key=lambda r: float(r.get("total_r") or 0)) if pos else rows_in[0]
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    top_sc = scored[0][0]
    near = [t for t in scored if t[0] >= top_sc * 0.95]
    near.sort(key=lambda t: t[1], reverse=True)
    return near[0][2]

  best = _pick(rows)
  active = get_active_trade_model()
  active_id = (active or {}).get("id")
  active_rep = load_model_report(active_id) if active_id else None
  active_r = ((active_rep or {}).get("overall_oos") or {}).get("total_r")
  best_r = best.get("total_r")

  active_health = assess_model_health(active_id)
  if require_better_than_active and active_r is not None and best_r is not None:
    better = float(best_r) > float(active_r) + 5
    rescue = active_health.get("verdict") == "degraded" and float(best_r) > 0
    if not better and not rescue:
      return {
        "ok": False,
        "reason": "active_still_competitive",
        "active_id": active_id,
        "active_r": active_r,
        "best_r": best_r,
        "active_verdict": active_health.get("verdict"),
      }

  model = apply_best_to_profile(best, run_id=run.get("run_id"))
  # Stamp search space from grid best (fallback improved)
  try:
    from gui.trade_model import load_models_store, save_models_store
    space = best.get("mining_search_space") or improved_search_space_dict()
    store = load_models_store()
    for m in store["models"]:
      if m.get("id") == model.get("id"):
        m["mining_search_space"] = space
        model = m
        break
    save_models_store(store)
  except Exception:
    pass

  if set_active:
    from gui.trade_model import set_active_trade_model
    set_active_trade_model(model["id"])

  entry = {
    "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "action": "promote_grid_best",
    "model_id": model.get("id"),
    "label": model.get("label"),
    "best_r": best_r,
    "active_before": active_id,
    "run_id": run.get("run_id"),
    "objective": objective,
  }
  PROMOTION_LOG.parent.mkdir(parents=True, exist_ok=True)
  with open(PROMOTION_LOG, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
  return {"ok": True, "model": model, "best": best, "log": entry}


def health_gate_active_model() -> dict[str, Any]:
  """If active model is degraded, try promoting latest grid best."""
  from gui.trade_model import get_active_trade_model

  active = get_active_trade_model()
  health = assess_model_health((active or {}).get("id"))
  out = {"health": health, "promoted": None}
  if health.get("verdict") == "degraded":
    promo = maybe_promote_grid_best(require_better_than_active=False)
    out["promoted"] = promo
  return out
