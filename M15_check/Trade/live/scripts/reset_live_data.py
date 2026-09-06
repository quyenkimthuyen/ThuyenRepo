#!/usr/bin/env python3
"""CLI: reset Live runtime data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from reset_data import reset_live_data  # noqa: E402


def main() -> int:
  ap = argparse.ArgumentParser(description="Reset Live journal / sim / cache / packages")
  ap.add_argument("--yes", action="store_true", help="Skip confirm")
  ap.add_argument("--keep-packages", action="store_true",
                  help="Keep installed_models + roster")
  ap.add_argument("--no-reseed", action="store_true", help="Do not re-seed OHLC after wipe")
  ap.add_argument("--no-stop", action="store_true", help="Do not stop bridge/replay first")
  args = ap.parse_args()
  if not args.yes:
    print("This wipes Live journals, parity, bridge state, OHLC cache"
          + (" and packages/roster" if not args.keep_packages else "")
          + ".")
    ans = input("Type RESET to confirm: ").strip()
    if ans != "RESET":
      print("Aborted")
      return 1
  out = reset_live_data(
    stop_services=not args.no_stop,
    include_packages=not args.keep_packages,
    reseed_ohlc=not args.no_reseed and args.keep_packages,
  )
  print(json.dumps(out, indent=2, default=str))
  return 0 if out.get("ok") else 1


if __name__ == "__main__":
  raise SystemExit(main())
