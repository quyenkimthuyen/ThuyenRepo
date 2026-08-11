"""One-shot: run grid (KB already trained) then promote top 3 Trade Models."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_kb_then_grid import log, run_grid  # noqa: E402
from scripts.bootstrap_m5_pipeline import promote_top  # noqa: E402


def main() -> int:
  log("=== Resume: grid only + promote ===")
  run_grid()
  created = promote_top(3)
  log(f"=== Promoted {len(created)} Trade Models ===")
  for m in created:
    log(f"  {m.get('id')} · {m.get('label')} · {m.get('total_r')}R · WR {m.get('win_rate_pct')}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
