#!/usr/bin/env python3
"""Drive the EA history export to completion in one foreground loop.

The bridge service only pumps ``process_history_sync`` on its own poll cadence,
which turns a 100k-bar backfill into hours. This drains chunk-by-chunk at EA
timer speed so the longer OOS window is ready in minutes.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env  # noqa: E402


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desk", default="e21")
  ap.add_argument("--chunk", type=int, default=2000, help="EA caps this at 2000")
  ap.add_argument("--timeout", type=int, default=1800)
  ap.add_argument("--restart", action="store_true",
                  help="force a fresh request from offset 0")
  args = ap.parse_args()

  cfg = apply_desk_env(args.desk)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)

  from mt5_bridge.history_sync import (
    get_history_status,
    process_history_sync,
    start_history_sync,
  )

  if args.restart:
    start_history_sync(force=True, chunk_size=args.chunk)
    print("đã gửi request mới từ offset 0")

  t0 = time.time()
  deadline = t0 + args.timeout
  last_report = 0.0
  stalls = 0
  while time.time() < deadline:
    st = process_history_sync(chunk_size=args.chunk)
    state = st.get("state")
    stored = int(st.get("stored_bars") or 0)
    recv = int(st.get("received_bars") or 0)
    avail = int(st.get("available_bars") or 0)

    if state == "completed":
      meta = get_history_status().get("data") or {}
      print(
        f"\nXONG sau {time.time() - t0:.0f}s: stored={stored} "
        f"received={recv} available={avail}"
      )
      print(f"  range: {meta.get('start')} -> {meta.get('end')}")
      print(f"  bars={meta.get('bars')} gaps={meta.get('gap_count')}")
      return 0

    if state == "requesting":
      stalls += 1
      if stalls > 240:
        print("\nEA không trả chunk (kiểm tra EA còn attach chart không)")
        return 1
      time.sleep(0.5)
      continue
    stalls = 0

    now = time.time()
    if now - last_report >= 5:
      last_report = now
      pct = (100.0 * recv / avail) if avail else 0.0
      print(
        f"  [{time.strftime('%H:%M:%S')}] {state} recv={recv}/{avail} "
        f"({pct:.1f}%) stored={stored}",
        flush=True,
      )
    time.sleep(0.05)

  print("\nhết thời gian chờ")
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
