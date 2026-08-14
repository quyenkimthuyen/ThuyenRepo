#!/usr/bin/env python3
"""Run Pass2 jobs for one desk in an isolated process."""
from __future__ import annotations
import json, sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

FINAL = Path(__file__).resolve().parent
sys.path.insert(0, str(FINAL))
from _wr_opt_pass2_worker import run_job

def main() -> int:
  jobs_path = Path(sys.argv[1])
  workers = int(sys.argv[2])
  out_path = Path(sys.argv[3])
  jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
  rows = []
  with ProcessPoolExecutor(max_workers=max(1, workers)) as pool:
    futs = {pool.submit(run_job, j): j.get("name") for j in jobs}
    for fut in as_completed(futs):
      rows.append(fut.result())
  # Drop schedule_weekly from file if huge? Keep — needed for promote.
  out_path.write_text(json.dumps(rows, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  print(f"DONE n={len(rows)} ok={sum(1 for r in rows if not r.get('error'))}", flush=True)
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
