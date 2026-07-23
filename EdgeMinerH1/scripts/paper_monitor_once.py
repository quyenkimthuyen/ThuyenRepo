"""Run one Paper Monitor cycle outside the Streamlit process."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from paper_background import load_config, run_cycle_now


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--force-refresh", action="store_true")
  args = parser.parse_args()
  try:
    run_cycle_now(load_config(), force_refresh=args.force_refresh)
    return 0
  except Exception:
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
