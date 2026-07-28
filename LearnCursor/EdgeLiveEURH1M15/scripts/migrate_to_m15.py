#!/usr/bin/env python3
"""Archive all H1-era artifacts before the greenfield EURUSD M15 rebuild."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = ROOT / "results" / "m15_migration.json"

ARCHIVE_TARGETS = (
  "data/mt5_eurusd_h1.parquet",
  "data/mt5_eurusd_h1_meta.json",
  "data/mt5_eurusd_m15.parquet",
  "data/mt5_eurusd_m15_meta.json",
  "learning/kb_profiles",
  "results/app_settings.json",
  "results/grid_search",
  "results/trade_models",
  "results/trade_models.json",
  "results/active_trade_model.json",
  "results/active_workspace.json",
  "results/backtest_report.json",
  "results/learning_report.json",
  "results/reports",
  "results/jobs/long_task_state.json",
  "results/paper_monitor_state.json",
  "results/live_workflow.json",
  "results/oos_trades.csv",
  "mt5/bridge/history_request.json",
  "mt5/bridge/history_chunk.json",
  "mt5/bridge/history_ack.json",
  "mt5/bridge/history_status.json",
)


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--force", action="store_true")
  args = parser.parse_args()
  if MARKER.exists() and not args.force:
    print(f"M15 migration already completed: {MARKER}")
    return 0

  stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
  archive = ROOT / "archive" / f"h1_legacy_{stamp}"
  moved: list[str] = []
  for relative in ARCHIVE_TARGETS:
    source = ROOT / relative
    if not source.exists():
      continue
    destination = archive / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    moved.append(relative)

  (ROOT / "learning" / "kb_profiles").mkdir(parents=True, exist_ok=True)
  (ROOT / "results" / "grid_search").mkdir(parents=True, exist_ok=True)
  payload = {
    "migrated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "source": "mt5_ea",
    "symbol": "EURUSD",
    "timeframe": "M15",
    "data_start": "2025-01-01",
    "archive": str(archive),
    "moved": moved,
  }
  MARKER.parent.mkdir(parents=True, exist_ok=True)
  MARKER.write_text(json.dumps(payload, indent=2), encoding="utf-8")
  print(f"Archived {len(moved)} H1 artifacts to {archive}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
