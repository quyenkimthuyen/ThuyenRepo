#!/usr/bin/env python3
"""Backfill / export Trade Model freeze schedule from Health OOS config (M15)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_m15
from gui.trade_model import get_model_by_id, load_model_report, save_model_report
from run_backtest import run_walk_forward
from strategy_miner import mining_search_space_from_dict
from trade_model_schedule import (
  model_schedule_path,
  save_model_schedule,
  schedule_from_walk_forward_result,
)


def main() -> int:
  ap = argparse.ArgumentParser(description="Export M15 Trade Model OOS schedule")
  ap.add_argument("--model-id", default="tm_m15_best_2_49216b56")
  ap.add_argument("--update-report", action="store_true",
                  help="Also rewrite model Health report from this WF run")
  ap.add_argument("--quiet", action="store_true")
  args = ap.parse_args()

  model = get_model_by_id(args.model_id)
  report = load_model_report(args.model_id) or {}
  cfg = dict(report.get("config") or {})

  train_weeks = int(
    (model or {}).get("train_weeks")
    or cfg.get("train_weeks")
    or 3
  )
  use_kb = bool((model or {}).get("use_kb", cfg.get("use_learning_kb", True)))
  kb_profile = (model or {}).get("kb_profile") or cfg.get("kb_profile")
  kb_snapshot = (model or {}).get("kb_snapshot", cfg.get("kb_snapshot"))
  if kb_snapshot in (None, "latest"):
    kb_snapshot = None
  else:
    try:
      kb_snapshot = int(kb_snapshot)
    except (TypeError, ValueError):
      kb_snapshot = None
  oos_from = (model or {}).get("oos_from") or cfg.get("oos_from") or "2026-01-01"
  oos_to = (model or {}).get("oos_to") or cfg.get("oos_to") or "2026-12-31"
  spread = float((model or {}).get("spread_pips") or cfg.get("spread_pips") or 1.0)
  slip = float((model or {}).get("slippage_pips") or cfg.get("slippage_pips") or 0.3)
  feature_profile = (
    (model or {}).get("feature_profile")
    or cfg.get("feature_profile")
    or "current"
  )
  search_payload = (model or {}).get("mining_search_space") or cfg.get("mining_search_space")
  search_space = mining_search_space_from_dict(search_payload) if search_payload else None

  print(
    f"Export schedule {args.model_id} | train={train_weeks}w "
    f"KB={kb_profile}@{kb_snapshot} OOS={oos_from}→{oos_to}"
  )
  df = load_eurusd_m15()
  result = run_walk_forward(
    df,
    use_learning=use_kb,
    train_weeks=train_weeks,
    verbose=not args.quiet,
    spread_pips=spread,
    slippage_pips=slip,
    holdout_months=0,
    kb_profile=kb_profile if use_kb else None,
    kb_snapshot=kb_snapshot if use_kb else None,
    oos_from=oos_from,
    oos_to=oos_to,
    feature_profile=feature_profile,
    search_space=search_space,
  )
  result.setdefault("config", {})["trade_model_id"] = args.model_id

  payload = schedule_from_walk_forward_result(result, args.model_id)
  if not payload:
    print("ERROR: walk-forward produced no schedule_weekly", file=sys.stderr)
    return 1
  path = save_model_schedule(args.model_id, payload)

  overall = result.get("overall_oos") or {}
  print(
    f"Wrote {path} weeks={payload['meta']['n_weeks']} "
    f"trades={overall.get('n_trades')} total_r={overall.get('total_r')}"
  )

  old_log = {
    str(w.get("week_start"))[:10]: w.get("strategy")
    for w in (report.get("weekly_log") or [])
    if isinstance(w, dict) and w.get("strategy")
  }
  if old_log:
    same = diff = 0
    for row in payload.get("weekly") or []:
      ws = str(row.get("week_start"))[:10]
      name = (row.get("strategy") or {}).get("name")
      old = old_log.get(ws)
      if not old:
        continue
      if old == name or str(old).rsplit("#", 1)[0] == str(name).rsplit("#", 1)[0]:
        same += 1
      else:
        diff += 1
    print(f"vs report weekly_log: same={same} diff={diff}")

  if args.update_report:
    save_model_report(args.model_id, result)
    print(f"Updated Health report for {args.model_id}")

  assert model_schedule_path(args.model_id).exists()
  data = json.loads(model_schedule_path(args.model_id).read_text(encoding="utf-8"))
  assert len(data.get("weekly") or []) > 0
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
