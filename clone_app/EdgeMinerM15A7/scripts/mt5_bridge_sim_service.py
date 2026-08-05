#!/usr/bin/env python3
"""Detached Simulate / HistoryFeed worker (outside Streamlit).

Runs BridgeEngine decide-loop on bridge_sim/ + sim_control poll so the GUI
stays responsive (same idea as mt5_bridge_service.py for Live).

Usage:
  python scripts/mt5_bridge_sim_service.py \\
    --from 2026-01-01 --to 2026-01-14 --delay-ms 100 \\
    --model-id tm_m15_best_2_xxx --risk-pct 1.0
"""
from __future__ import annotations

import argparse
import atexit
import os
import sys
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _register(pid_path: Path, log_path: Path, args) -> None:
  from mt5_bridge.ea_simulator import write_sim_state

  if sys.stdout is None or sys.stderr is None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(log_path, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
      sys.stdout = handle
    if sys.stderr is None:
      sys.stderr = handle

  pid_path.parent.mkdir(parents=True, exist_ok=True)
  pid_path.write_text(str(os.getpid()), encoding="utf-8")
  write_sim_state({
    "status": "running",
    "service_pid": os.getpid(),
    "runtime": "process",
    "model_id": args.model_id,
    "date_from": args.date_from,
    "date_to": args.date_to,
    "delay_ms": args.delay_ms,
    "error": None,
  })

  def _cleanup() -> None:
    try:
      if pid_path.exists() and pid_path.read_text(encoding="utf-8").strip() == str(os.getpid()):
        pid_path.unlink()
    except Exception:
      pass

  atexit.register(_cleanup)


def main() -> int:
  from mt5_bridge.background import _run_sim_bridge_loop
  from mt5_bridge.ea_simulator import SimConfig, run_history_feed_control, write_sim_state
  from mt5_bridge.protocol import BRIDGE_SIM_DIR
  from run_backtest import REPORT_DIR

  ap = argparse.ArgumentParser(description="MT5 Bridge Simulate HistoryFeed service")
  ap.add_argument("--from", dest="date_from", required=True)
  ap.add_argument("--to", dest="date_to", required=True)
  ap.add_argument("--delay-ms", type=int, default=100)
  ap.add_argument("--model-id", default=None)
  ap.add_argument("--risk-pct", type=float, default=1.0)
  ap.add_argument("--bridge-dir", default=str(BRIDGE_SIM_DIR))
  args = ap.parse_args()

  pid_path = REPORT_DIR / "mt5_bridge_sim_service.pid"
  log_path = REPORT_DIR / "mt5_bridge_sim_service.log"
  _register(pid_path, log_path, args)

  stop = threading.Event()
  bridge_dir = Path(args.bridge_dir)
  cfg = SimConfig(
    date_from=args.date_from,
    date_to=args.date_to,
    delay_ms=max(1, int(args.delay_ms)),
    model_id=args.model_id,
    risk_pct=float(args.risk_pct),
    bridge_dir=bridge_dir,
  )

  bridge_thread = threading.Thread(
    target=_run_sim_bridge_loop,
    args=(stop, args.model_id, float(args.risk_pct)),
    name="sim-bridge-decide",
    daemon=True,
  )
  bridge_thread.start()

  try:
    print(
      f"[sim-service] pid={os.getpid()} from={args.date_from} to={args.date_to} "
      f"delay_ms={args.delay_ms} model={args.model_id}",
      flush=True,
    )
    st = run_history_feed_control(cfg, stop_event=stop, pause_event=None)
    print(
      f"[sim-service] finished status={st.get('status')} "
      f"reason={st.get('stop_reason') or st.get('error') or '-'} "
      f"bars={st.get('bars_done')}/{st.get('bars_total')} "
      f"last={st.get('last_bar')}",
      flush=True,
    )
    write_sim_state({
      "status": st.get("status") or "completed",
      "service_pid": None,
      "runtime": "process",
      "error": st.get("error"),
      "stop_reason": st.get("stop_reason"),
      "bars_done": st.get("bars_done"),
      "bars_total": st.get("bars_total"),
      "last_bar": st.get("last_bar"),
    })
    return 0
  except Exception as e:
    traceback.print_exc()
    write_sim_state({"status": "error", "error": str(e), "service_pid": None})
    return 1
  finally:
    stop.set()
    bridge_thread.join(timeout=5.0)
    time.sleep(0.2)


if __name__ == "__main__":
  raise SystemExit(main())
