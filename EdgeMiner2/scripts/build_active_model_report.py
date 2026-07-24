#!/usr/bin/env python3
"""Build and store the full report for the active M15 Trade Model."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_m15
from gui.trade_model import get_model_by_id, load_active_model_id, save_model_report
from run_backtest import run_walk_forward, save_backtest_report


def main() -> int:
  model_id = load_active_model_id()
  model = get_model_by_id(model_id) if model_id else None
  if not model or model.get("data_timeframe") != "M15":
    raise RuntimeError("No active M15 Trade Model.")
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
  report.setdefault("config", {})["trade_model_id"] = model_id
  save_model_report(model_id, report)
  save_backtest_report(report)
  print(f"report={model_id} total_r={report['overall_oos']['total_r']}", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
