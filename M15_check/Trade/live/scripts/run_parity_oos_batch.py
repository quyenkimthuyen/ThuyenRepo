#!/usr/bin/env python3
"""Batch schedule-parity OOS replay for all enabled Live books (lab-accurate)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from schedule_parity import run_all_enabled_parity  # noqa: E402


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
      sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  oos_from = os.environ.get("LIVE_REPLAY_FROM") or "2026-01-01"
  oos_to = os.environ.get("LIVE_REPLAY_TO") or "2026-08-07"
  print(f"==== Schedule-parity OOS {oos_from} -> {oos_to} ====", flush=True)
  out = run_all_enabled_parity(oos_from=oos_from, oos_to=oos_to)
  print(json_dumps(out), flush=True)
  return 0 if out.get("ok") else 1


def json_dumps(obj) -> str:
  import json
  return json.dumps(
    {
      "ok": obj.get("ok"),
      "books": [
        {
          "symbol": b.get("symbol"),
          "timeframe": b.get("timeframe"),
          "ok": b.get("ok"),
          "models": [
            {
              "model_id": m.get("model_id"),
              "label": m.get("label"),
              "total_r": m.get("total_r"),
              "lab_total_r": m.get("lab_total_r"),
              "delta_r": m.get("delta_r"),
              "win_rate_pct": m.get("win_rate_pct"),
              "error": m.get("error"),
            }
            for m in (b.get("models") or [])
          ],
        }
        for b in (obj.get("books") or [])
      ],
    },
    indent=2,
  )


if __name__ == "__main__":
  raise SystemExit(main())
