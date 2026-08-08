#!/usr/bin/env python3
"""CLI: start EA HISTORY_FEED control (App writes sim_control; EA sends bars).

Requires ForgeBridgeM15 on chart with InpMode=HISTORY_FEED, InpBridgeSubdir=bridge_sim.
Also run a bridge decision loop on bridge_sim (GUI Start feed, or this script's poll
expects an external BridgeEngine — prefer GUI).

Example:
  python scripts/simulate_ea_bridge.py --from 2026-01-01 --to 2026-01-31 --delay-ms 100
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mt5_bridge.background import _cycle, load_config  # noqa: E402
from mt5_bridge.ea_simulator import (  # noqa: E402
  SimConfig,
  run_history_feed_control,
  stop_history_feed_control,
)
from mt5_bridge.engine import BridgeEngine  # noqa: E402
from mt5_bridge.history_sync import MT5_CACHE_PATH  # noqa: E402
from mt5_bridge.models import load_active_model_id  # noqa: E402
from mt5_bridge.protocol import BRIDGE_SIM_DIR, ensure_bridge_dir  # noqa: E402


def main() -> int:
  ap = argparse.ArgumentParser(
    description="EA History Feed control (sim_control.json) + bridge_sim decisions"
  )
  ap.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
  ap.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
  ap.add_argument("--delay-ms", type=int, default=100)
  ap.add_argument("--model-id", default=None)
  ap.add_argument("--risk-pct", type=float, default=1.0)
  ap.add_argument("--bridge-dir", type=Path, default=BRIDGE_SIM_DIR)
  args = ap.parse_args()

  bridge_dir = ensure_bridge_dir(Path(args.bridge_dir))
  mid = args.model_id or load_active_model_id()
  cfg = SimConfig(
    date_from=args.date_from,
    date_to=args.date_to,
    delay_ms=max(1, int(args.delay_ms)),
    model_id=mid,
    risk_pct=float(args.risk_pct),
    bridge_dir=bridge_dir,
  )

  stop = threading.Event()
  engine = BridgeEngine(model_id=mid, risk_pct=float(args.risk_pct))
  if MT5_CACHE_PATH.exists():
    try:
      engine.ensure_history()
    except Exception as e:
      print(f"[sim] warn ensure_history: {e}", flush=True)

  def _bridge_loop():
    last_bar_fp = last_fill_fp = None
    while not stop.is_set():
      try:
        last_bar_fp, last_fill_fp = _cycle(engine, bridge_dir, last_bar_fp, last_fill_fp)
      except Exception:
        pass
      time.sleep(0.15)

  bt = threading.Thread(target=_bridge_loop, name="sim-bridge", daemon=True)
  bt.start()

  def on_prog(p: dict):
    done = p.get("bars_done") or 0
    total = p.get("bars_total") or 1
    if done == total or done % 50 == 0 or done <= 3:
      print(
        f"[sim] ea={p.get('ea_status')} {done}/{total} {p.get('last_bar')} "
        f"trades={p.get('n_fills')}",
        flush=True,
      )

  try:
    summary = run_history_feed_control(cfg, stop_event=stop, on_progress=on_prog)
  except KeyboardInterrupt:
    stop.set()
    stop_history_feed_control(bridge_dir)
    print("[sim] interrupted", flush=True)
    return 130
  except Exception as e:
    stop.set()
    print(f"[sim] ERROR: {e}", flush=True)
    return 1
  finally:
    stop.set()

  print(
    f"[sim] done status={summary.get('status')} ea={summary.get('ea_status')} "
    f"trades={summary.get('n_fills')}",
    flush=True,
  )
  return 0 if summary.get("status") == "completed" else 1


if __name__ == "__main__":
  raise SystemExit(main())
