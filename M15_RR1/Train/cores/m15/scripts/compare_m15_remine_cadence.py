#!/usr/bin/env python3
"""Compare 1-day, 2-day and current 7-day M15 strategy remine cadence."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import get_train_window_indices, load_eurusd_m15
from feature_engine import FeatureMatrix
from gui.trade_model import get_model_by_id, load_active_model_id
from optimizer import get_knowledge_base, optimize_on_window, reset_kb_cache, set_kb_profile
from strategy import compute_metrics
from strategy_miner import backtest_mined, ensure_label_cache_for_df, generate_signals_mined

OUT = ROOT / "results" / "research" / "m15_remine_cadence.json"


def _periods(start: pd.Timestamp, end: pd.Timestamp, days: int):
  cursor = start
  while cursor < end:
    next_cursor = min(cursor + pd.Timedelta(days=days), end)
    yield cursor, next_cursor
    cursor = next_cursor


def _run_cadence(
  df: pd.DataFrame,
  fm: FeatureMatrix,
  *,
  cadence_days: int,
  train_weeks: int,
  kb,
  spread_pips: float,
  slippage_pips: float,
  oos_start: pd.Timestamp,
  oos_end: pd.Timestamp,
) -> dict:
  candidates = []
  strategy_names: list[str] = []
  periods = list(_periods(oos_start, oos_end, cadence_days))
  for number, (period_start, period_end) in enumerate(periods, 1):
    train_start, train_end = get_train_window_indices(df, period_start, train_weeks)
    if train_start is None:
      continue
    strategy = optimize_on_window(
      fm, train_start, train_end, use_learning=True, as_of=period_start, kb=kb,
    )
    if strategy is None:
      continue
    core_start = int(df.index.searchsorted(period_start, side="left"))
    core_end = int(df.index.searchsorted(period_end, side="left"))
    if core_start >= core_end:
      continue
    signals = generate_signals_mined(fm, strategy, core_start, core_end)
    simulation_end = min(fm.n, core_end + int(strategy.max_hold_bars) + 2)
    segment_trades = backtest_mined(
      fm, strategy, signals, core_start, simulation_end,
      spread_pips=spread_pips, slippage_pips=slippage_pips,
    )
    candidates.extend(
      trade for trade in segment_trades
      if period_start <= pd.Timestamp(trade.entry_time) < period_end
    )
    strategy_names.append(strategy.name)
    print(
      f"cadence={cadence_days}d {number}/{len(periods)} "
      f"start={period_start.date()} trades={len(candidates)}",
      flush=True,
    )

  # Carry the one-position-at-a-time constraint across remine boundaries.
  accepted = []
  last_exit = None
  for trade in sorted(candidates, key=lambda item: item.entry_time):
    if last_exit is not None and trade.entry_time < last_exit:
      continue
    accepted.append(trade)
    last_exit = trade.exit_time

  metrics = compute_metrics(accepted, risk_pct_per_trade=1.0)
  elapsed_weeks = max((oos_end - oos_start).total_seconds() / (7 * 86400), 1)
  total_r = float(metrics["total_r"])
  drawdown = float(metrics["max_drawdown_r"])
  return {
    "cadence_days": cadence_days,
    "remine_count": len(strategy_names),
    "distinct_strategies": len(set(strategy_names)),
    "n_trades": int(metrics["n_trades"]),
    "trades_per_week": round(int(metrics["n_trades"]) / elapsed_weeks, 2),
    "win_rate_pct": round(float(metrics["win_rate"]) * 100, 2),
    "avg_rr": round(float(metrics["avg_rr"]), 3),
    "profit_factor": round(float(metrics["profit_factor"]), 3),
    "total_r": round(total_r, 3),
    "max_drawdown_r": round(drawdown, 3),
    "risk_adjusted": round(total_r / max(drawdown, 0.5), 3),
    "max_win_streak": int(metrics.get("max_win_streak", 0)),
    "max_loss_streak": int(metrics.get("max_loss_streak", 0)),
  }


def main() -> int:
  model_id = load_active_model_id()
  model = get_model_by_id(model_id) if model_id else None
  if not model or model.get("data_timeframe") != "M15":
    raise RuntimeError("Active M15 model is required.")

  df = load_eurusd_m15("2025-01-01")
  fm = FeatureMatrix(df)
  ensure_label_cache_for_df(len(df))
  reset_kb_cache()
  profile = model.get("kb_profile") or "default"
  snapshot = model.get("kb_snapshot")
  set_kb_profile(profile, snapshot)
  kb = get_knowledge_base(profile, snapshot)

  requested_start = pd.Timestamp(model.get("oos_from") or "2026-01-01")
  # Current production cadence starts at the first complete Monday.
  oos_start = requested_start + pd.Timedelta(days=(-requested_start.weekday()) % 7)
  oos_end = min(
    pd.Timestamp(model.get("oos_to") or df.index[-1]) + pd.Timedelta(days=1),
    pd.Timestamp(df.index[-1]) + pd.Timedelta(minutes=15),
  )
  results = [
    _run_cadence(
      df, fm,
      cadence_days=days,
      train_weeks=int(model["train_weeks"]),
      kb=kb,
      spread_pips=float(model.get("spread_pips", 1.0)),
      slippage_pips=float(model.get("slippage_pips", 0.3)),
      oos_start=oos_start,
      oos_end=oos_end,
    )
    for days in (1, 2, 7)
  ]
  valid = [row for row in results if row["total_r"] > 0 and 7 <= row["trades_per_week"] <= 10]
  best = max(valid or results, key=lambda row: row["risk_adjusted"])
  payload = {
    "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "model_id": model_id,
    "data_fingerprint": model.get("data_fingerprint"),
    "timeframe": "M15",
    "train_weeks": int(model["train_weeks"]),
    "kb_profile": profile,
    "kb_snapshot": snapshot,
    "oos_from": str(oos_start),
    "oos_to": str(oos_end),
    "spread_pips": float(model.get("spread_pips", 1.0)),
    "slippage_pips": float(model.get("slippage_pips", 0.3)),
    "selection_rule": "Highest Total R / Max Drawdown with positive R and 7-10 trades/week",
    "results": results,
    "recommended_cadence_days": best["cadence_days"],
  }
  OUT.parent.mkdir(parents=True, exist_ok=True)
  OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
  print(json.dumps(payload, ensure_ascii=False), flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
