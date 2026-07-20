"""Simple process job runner — GUI-safe background execution without Celery."""
from __future__ import annotations

import multiprocessing as mp
import traceback
from dataclasses import dataclass
from typing import Callable, Optional

from .contracts import JobEvent, JobKind, Report, RunSpec
from .data_loader import load_eurusd_h1
from .paths import ensure_dirs
from .store import Store
from .wf_runner import execute_run

# In-process registry for local CLI; GUI can poll Store events.
_CANCEL = set()


@dataclass
class JobHandle:
  job_id: str
  process: object | None = None


def _worker(job_id: str, spec_json: str, db_path: str) -> None:
  store = Store(db_path)
  try:
    store.update_run(job_id, status="running")
    store.append_event(JobEvent(job_id=job_id, status="running", message="started"))
    spec = RunSpec.model_validate_json(spec_json)

    start = (spec.data_from or spec.oos_from)
    start_s = start.isoformat() if start else "2022-01-01"
    end_s = spec.data_to.isoformat() if spec.data_to else None
    df = load_eurusd_h1(start_s, end_s, use_cache=True, force_refresh=False)

    def on_progress(cur: int, total: int, week_start):
      if job_id in _CANCEL:
        raise KeyboardInterrupt("cancelled")
      store.append_event(
        JobEvent(
          job_id=job_id,
          status="progress",
          current=cur,
          total=total,
          message=str(getattr(week_start, "date", lambda: week_start)()),
        )
      )

    report: Report = execute_run(df, spec, on_progress=on_progress, verbose=False)
    report_id = store.save_report(job_id, report)
    store.update_run(job_id, status="done")
    store.append_event(
      JobEvent(
        job_id=job_id,
        status="done",
        current=1,
        total=1,
        message="completed",
        payload={"report_id": report_id},
      )
    )
  except KeyboardInterrupt:
    store.update_run(job_id, status="cancelled", error="cancelled")
    store.append_event(JobEvent(job_id=job_id, status="cancelled", message="cancelled"))
  except Exception as exc:
    store.update_run(job_id, status="failed", error=str(exc))
    store.append_event(
      JobEvent(
        job_id=job_id,
        status="failed",
        message=str(exc),
        payload={"traceback": traceback.format_exc()},
      )
    )


def submit_job(spec: RunSpec, store: Store | None = None, *, background: bool = True) -> JobHandle:
  ensure_dirs()
  store = store or Store()
  job_id = store.create_run(spec, status="queued")
  store.append_event(JobEvent(job_id=job_id, status="queued", message="queued"))

  if not background:
    _worker(job_id, spec.model_dump_json(), str(store.db_path))
    return JobHandle(job_id=job_id)

  # Prefer subprocess over multiprocessing spawn (more reliable on Windows + Streamlit)
  import subprocess
  import sys
  from pathlib import Path
  root = Path(__file__).resolve().parent.parent
  proc = subprocess.Popen(
    [sys.executable, "-m", "forexforge.jobs_worker", job_id, str(store.db_path)],
    cwd=str(root),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
  )
  return JobHandle(job_id=job_id, process=proc)



def cancel_job(job_id: str, handle: JobHandle | None = None) -> None:
  _CANCEL.add(job_id)
  if handle and handle.process and handle.process.is_alive():
    handle.process.terminate()


def run_sync(spec: RunSpec, store: Store | None = None) -> tuple[str, Report | None]:
  """Foreground run — useful for CLI and tests."""
  store = store or Store()
  handle = submit_job(spec, store, background=False)
  run = store.get_run(handle.job_id)
  report = None
  if run and run["status"] == "done":
    reports = [r for r in store.list_reports(20) if r["run_id"] == handle.job_id]
    if reports:
      report = store.get_report(reports[0]["id"])
  return handle.job_id, report
