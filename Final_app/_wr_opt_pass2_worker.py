#!/usr/bin/env python3
"""Picklable Pass2 walk-forward worker for optimize_live_roster_wr.py."""
from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

OOS_FROM, OOS_TO = "2026-01-01", "2026-08-07"


def run_job(job: dict) -> dict:
  desk = Path(job["desk_path"])
  sys.path.insert(0, str(desk))
  os.chdir(desk)
  started = time.time()
  try:
    from mining_presets import get_preset
    from optimizer import reset_kb_cache
    from run_backtest import run_walk_forward
    from strategy_miner import mining_search_space_from_dict

    try:
      from data_loader import load_eurusd_m15 as load_df
    except ImportError:
      from data_loader import load_gbpusd_m15 as load_df  # type: ignore

    space_dict = dict(get_preset(job["preset"]) or {})
    if not space_dict:
      return {**job, "error": f"unknown_preset:{job['preset']}", "elapsed_sec": 0}
    space = mining_search_space_from_dict(space_dict)
    reset_kb_cache()
    df = load_df("2025-01-01")
    feature = job.get("feature_profile") or (
      "m5_parity" if job.get("timeframe") == "M5" else "current"
    )
    report = run_walk_forward(
      df,
      use_learning=True,
      train_weeks=int(job["train_weeks"]),
      spread_pips=float(job.get("spread_pips") or 1.0),
      slippage_pips=float(job.get("slippage_pips") or 0.3),
      holdout_months=0,
      kb_profile=job.get("kb_profile"),
      oos_from=OOS_FROM,
      oos_to=OOS_TO,
      feature_profile=feature,
      search_space=space,
      verbose=False,
    )
    oos = report.get("overall_oos") or {}
    # Drop huge unused fields for IPC — keep schedule for promote
    return {
      **{k: job[k] for k in job if k != "baseline"},
      "baseline": job.get("baseline"),
      "total_r": oos.get("total_r"),
      "win_rate_pct": oos.get("win_rate_pct"),
      "profit_factor": oos.get("profit_factor"),
      "n_trades": oos.get("n_trades"),
      "max_drawdown_r": oos.get("max_drawdown_r"),
      "trades_per_week": oos.get("trades_per_week"),
      "schedule_weekly": report.get("schedule_weekly"),
      "report_config": report.get("config"),
      "data_source": report.get("data_source"),
      "overall_oos": oos,
      "error": None,
      "elapsed_sec": round(time.time() - started, 1),
    }
  except Exception as exc:
    return {
      **job,
      "error": f"{type(exc).__name__}: {exc}",
      "traceback": traceback.format_exc(),
      "elapsed_sec": round(time.time() - started, 1),
    }
