#!/usr/bin/env python3
"""Rebuild the complete Grid Search and activate the best MT5-trained model."""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gui.app_settings import get_settings
from gui.grid_search_engine import build_grid_from_settings, run_single, save_grid_run
from gui.trade_model import create_trade_model, save_model_report
from mt5_bridge.history_sync import get_history_status


def main() -> int:
  history = get_history_status()
  meta = history.get("data") or {}
  if (
    history.get("state") != "completed"
    or meta.get("source") != "mt5_ea"
    or meta.get("timeframe") != "M15"
  ):
    raise RuntimeError("MT5 M15 history sync is not complete.")

  settings = get_settings()
  specs, config = build_grid_from_settings(settings)
  objective = settings.get("grid_objective", "risk_adjusted")

  rows: list[dict] = []
  with ProcessPoolExecutor(max_workers=min(4, len(specs))) as pool:
    pending = {pool.submit(run_single, spec): spec for spec in specs}
    for done, future in enumerate(as_completed(pending), 1):
      spec = pending[future]
      try:
        rows.append(future.result())
      except Exception as exc:
        rows.append({"key": spec.key(), "label": spec.label(), "error": str(exc)})
      print(f"[{done}/{len(specs)}] {spec.label()}", flush=True)
  rows.sort(
    key=lambda row: float(row.get(objective) or row.get("total_r") or 0),
    reverse=True,
  )
  valid = [
    row for row in rows
    if (
      not row.get("error")
      and float(row.get("total_r") or 0) > 0
      and 7.0 <= float(row.get("trades_per_week") or 0) <= 10.0
    )
  ]
  if not valid:
    raise RuntimeError("Grid Search produced no profitable M15 result at 7-10 trades/week.")
  run_id = save_grid_run(
    rows,
    config={**config, "data_source": "mt5_ea", "timeframe": "M15"},
    objective=objective,
  )
  model = create_trade_model(
    valid[0], run_id=run_id, label="M15 Best", set_active=True, build_report=False,
  )
  from data_loader import load_eurusd_m15
  from run_backtest import run_walk_forward, save_backtest_report

  report = run_walk_forward(
    load_eurusd_m15("2025-01-01"),
    use_learning=bool(model.get("use_kb", True)),
    train_weeks=int(model["train_weeks"]),
    spread_pips=float(model.get("spread_pips", 1.0)),
    slippage_pips=float(model.get("slippage_pips", 0.3)),
    holdout_months=0,
    kb_profile=model.get("kb_profile"),
    kb_snapshot=model.get("kb_snapshot"),
    oos_from=model.get("oos_from"),
    oos_to=model.get("oos_to"),
  )
  report.setdefault("config", {})["trade_model_id"] = model["id"]
  save_model_report(model["id"], report)
  save_backtest_report(report)
  print(f"Grid={run_id} model={model['id']} total_r={valid[0].get('total_r')}", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
