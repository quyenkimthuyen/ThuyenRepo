#!/usr/bin/env python3
"""CLI: preflight all enabled Live books (materialize + decide_for_bar)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from preflight_live import preflight_enabled_books  # noqa: E402


def main() -> int:
  out = preflight_enabled_books(sim=False)
  print(json.dumps(out, indent=2, ensure_ascii=False, default=str), flush=True)
  return 0 if out.get("ok") else 1


if __name__ == "__main__":
  raise SystemExit(main())
