#!/usr/bin/env python3
"""Ask the ForgeBridge EA how far back M15 history really goes.

The 2024-01-01 floor is a config choice (data_start.json / desk yaml), not a
broker limit, and Total R = n x EV means OOS length multiplies n directly. This
sets an early data_start, kicks a forced history sync, and polls the EA status
for ``available_bars`` so the true depth is known before committing to a resync.
"""
from __future__ import annotations

import argparse
import json
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
  ap.add_argument("--from-date", default="2015-01-01 00:00")
  ap.add_argument("--wait", type=int, default=180, help="seconds to poll status")
  ap.add_argument("--probe-only", action="store_true",
                  help="report status without touching data_start")
  args = ap.parse_args()

  cfg = apply_desk_env(args.desk)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)

  from mt5_bridge.history_sync import (
    get_data_start_broker,
    get_history_status,
    set_data_start_broker,
  )

  print(f"data_start hiện tại: {get_data_start_broker()}")
  print(f"status hiện tại: {json.dumps(get_history_status(), ensure_ascii=False)}")
  if args.probe_only:
    return 0

  res = set_data_start_broker(args.from_date, sync=True)
  print(f"đã đặt data_start={res['data_start']} (source={res['source']})")

  last = None
  deadline = time.time() + args.wait
  while time.time() < deadline:
    st = get_history_status()
    key = (st.get("state"), st.get("available_bars"), st.get("received_bars"))
    if key != last:
      last = key
      print(
        f"  [{time.strftime('%H:%M:%S')}] state={st.get('state')} "
        f"available_bars={st.get('available_bars')} "
        f"received={st.get('received_bars')} offset={st.get('offset')} "
        f"err={st.get('error')}",
        flush=True,
      )
      if st.get("available_bars"):
        avail = int(st["available_bars"])
        print(
          f"\n=> EA báo có {avail} bar M15 từ {args.from_date}"
          f" ≈ {avail * 15 / 60 / 24 / 30.4:.1f} tháng dữ liệu giao dịch"
        )
        return 0
    time.sleep(5)
  print("\n=> chưa nhận được available_bars trong thời gian chờ")
  return 1


if __name__ == "__main__":
  raise SystemExit(main())
