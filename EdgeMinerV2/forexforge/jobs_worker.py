"""Background worker entry: python -m forexforge.jobs_worker <job_id> <db_path>"""
from __future__ import annotations

import sys

from .jobs import _worker
from .store import Store


def main(argv: list[str] | None = None) -> int:
  argv = list(sys.argv[1:] if argv is None else argv)
  if len(argv) < 1:
    print("usage: python -m forexforge.jobs_worker <job_id> [db_path]", file=sys.stderr)
    return 2
  job_id = argv[0]
  db_path = argv[1] if len(argv) > 1 else None
  store = Store(db_path)
  run = store.get_run(job_id)
  if not run:
    print(f"job not found: {job_id}", file=sys.stderr)
    return 1
  _worker(job_id, run["spec_json"], str(store.db_path))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
