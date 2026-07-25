#!/usr/bin/env python3
"""CLI: Simulate ForgeBridge EA over a historical window via file protocol.

Example:
  python scripts/simulate_ea_bridge.py --from 2026-01-01 --to 2026-01-31 --delay-ms 0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mt5_bridge.ea_simulator import SimConfig, run_simulation
from mt5_bridge.models import load_active_model_id
from mt5_bridge.protocol import BRIDGE_SIM_DIR


def main() -> int:
  ap = argparse.ArgumentParser(description="Simulate EA Bridge (historical bar→decision→fill)")
  ap.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
  ap.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
  ap.add_argument("--delay-ms", type=int, default=0)
  ap.add_argument("--model-id", default=None)
  ap.add_argument("--risk-pct", type=float, default=1.0)
  ap.add_argument("--bridge-dir", type=Path, default=BRIDGE_SIM_DIR)
  args = ap.parse_args()

  cfg = SimConfig(
    date_from=args.date_from,
    date_to=args.date_to,
    delay_ms=max(0, int(args.delay_ms)),
    model_id=args.model_id or load_active_model_id(),
    risk_pct=float(args.risk_pct),
    bridge_dir=Path(args.bridge_dir),
  )

  def on_prog(p: dict):
    done = p.get("bars_done") or 0
    total = p.get("bars_total") or 1
    if done == total or done % 50 == 0 or done <= 3:
      print(
        f"[sim] {done}/{total} {p.get('last_bar')} "
        f"action={p.get('last_action')} fills={p.get('n_fills')}",
        flush=True,
      )

  try:
    summary = run_simulation(cfg, on_progress=on_prog)
  except Exception as e:
    print(f"[sim] ERROR: {e}", flush=True)
    return 1
  print(f"[sim] done status={summary.get('status')} fills={summary.get('n_fills')}", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
