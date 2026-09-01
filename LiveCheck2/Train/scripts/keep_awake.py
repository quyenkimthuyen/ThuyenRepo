#!/usr/bin/env python3
"""Hold a system power request so long grid runs are not frozen by Modern Standby.

This laptop only exposes "Standby (S0 Low Power Idle)", where the classic
``powercfg /change standby-timeout-ac 0`` knob does nothing: the box drops into
S0 idle whenever nobody touches it and the grid workers stop accumulating CPU
(measured 7% efficiency over 8.5h, 94% while interactive). ES_SYSTEM_REQUIRED
keeps the CPU scheduled without keeping the display on.

Run it alongside the pipeline; killing it releases the request immediately.
"""
from __future__ import annotations

import argparse
import ctypes
import sys
import time
from datetime import datetime

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--hours", type=float, default=48.0)
  ap.add_argument("--report-min", type=float, default=15.0)
  args = ap.parse_args()

  if not sys.platform.startswith("win"):
    print("chỉ dùng trên Windows")
    return 1

  kernel32 = ctypes.windll.kernel32
  if kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) == 0:
    print("SetThreadExecutionState thất bại")
    return 1
  print(f"keep-awake ON ({args.hours}h) — display vẫn được phép tắt", flush=True)

  deadline = time.time() + args.hours * 3600.0
  try:
    while time.time() < deadline:
      time.sleep(args.report_min * 60.0)
      print(f"[{datetime.now():%H:%M:%S}] keep-awake còn "
            f"{(deadline - time.time()) / 3600:.1f}h", flush=True)
  except KeyboardInterrupt:
    pass
  finally:
    kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    print("keep-awake OFF", flush=True)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
