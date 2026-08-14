#!/usr/bin/env python3
"""Batch Linux replay for full OOS window across all enabled Live books.

Books run in parallel (one subprocess per symbol+TF), matching Live's
one-worker-per-book model. Models within a book stay sequential on each bar.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from books import group_models_by_book  # noqa: E402
from live_config import RESULTS_DIR  # noqa: E402
from magic_allocator import assign_magics  # noqa: E402
from materialize_models import materialize_enabled  # noqa: E402
from package_store import load_roster, save_roster  # noqa: E402

OOS_FROM = os.environ.get("LIVE_REPLAY_FROM") or "2026-01-01"
OOS_TO = os.environ.get("LIVE_REPLAY_TO") or "2026-08-07"
# Cap parallel book workers (default = all books). Override: LIVE_REPLAY_BOOK_WORKERS=2
_WORKERS_ENV = os.environ.get("LIVE_REPLAY_BOOK_WORKERS", "").strip()
PY = sys.executable
REPLAY = LIVE / "scripts" / "run_linux_replay_inline.py"
SEED = LIVE / "scripts" / "seed_mt5_cache.py"
OUT = RESULTS_DIR / "replay_oos_batch.json"


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write_batch(payload: dict) -> None:
  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  tmp = OUT.with_suffix(".json.tmp")
  tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  tmp.replace(OUT)


def _book_last(sym: str, tf: str) -> dict:
  path = RESULTS_DIR / f"replay_last_{sym.lower()}_{tf.lower()}.json"
  if not path.exists():
    # fallback shared file (single-book / legacy)
    path = RESULTS_DIR / "replay_last.json"
  if not path.exists():
    return {}
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return {}
  # Only accept if it matches this book when present
  if data.get("symbol") and data.get("symbol") != sym:
    return {}
  if data.get("timeframe") and data.get("timeframe") != tf:
    return {}
  return data


def main() -> int:
  roster = load_roster()
  enabled = [m for m in (roster.get("models") or []) if m.get("enabled")]
  groups = group_models_by_book(enabled)
  if not groups:
    print("No enabled models", flush=True)
    return 1

  n_books = len(groups)
  max_workers = n_books
  if _WORKERS_ENV:
    try:
      max_workers = max(1, min(n_books, int(_WORKERS_ENV)))
    except ValueError:
      max_workers = n_books

  results: dict = {
    "started_at": _now(),
    "oos_from": OOS_FROM,
    "oos_to": OOS_TO,
    "mode": "live_like",
    "parallel_books": True,
    "max_workers": max_workers,
    "status": "running",
    "books": [],
  }
  print(
    f"==== OOS batch replay {OOS_FROM} -> {OOS_TO} · {n_books} books · "
    f"parallel workers={max_workers} ====",
    flush=True,
  )

  # Shared prepare once (avoid concurrent materialize / roster writes)
  live_rows = assign_magics(roster.get("models") or [], sim=False)
  save_roster(live_rows, active_book=roster.get("active_book"))
  print("## Materialize once (shared)", flush=True)
  materialize_enabled(roster={"models": live_rows})

  book_list = list(groups.items())
  for (sym, tf), rows in book_list:
    print(f"## Seed {sym} {tf}", flush=True)
    subprocess.run(
      [PY, str(SEED), "--symbol", sym, "--timeframe", tf],
      cwd=str(SPLIT),
      check=False,
    )

  _write_batch(results)

  # Launch / wait with a worker pool (default: all books at once)
  pending = [
    {
      "symbol": sym,
      "timeframe": tf,
      "labels": [r.get("label") or r.get("model_id") for r in rows],
    }
    for (sym, tf), rows in book_list
  ]
  running: list[dict] = []
  finished: list[dict] = []

  def _spawn(job: dict) -> dict:
    sym, tf = job["symbol"], job["timeframe"]
    log_path = RESULTS_DIR / f"replay_oos_{sym.lower()}_{tf.lower()}.log"
    logf = open(log_path, "w", encoding="utf-8")
    print(
      f"## Start {sym} {tf} · models={job['labels']} · log={log_path.name}",
      flush=True,
    )
    t0 = time.time()
    proc = subprocess.Popen(
      [
        PY, "-u", str(REPLAY),
        "--symbol", sym, "--timeframe", tf,
        "--from", OOS_FROM, "--to", OOS_TO,
        "--delay-ms", "0",
        "--seed",
        "--skip-materialize",
        "--progress-every", "25",
      ],
      cwd=str(SPLIT),
      stdout=logf,
      stderr=subprocess.STDOUT,
      env=os.environ.copy(),
      start_new_session=True,
    )
    return {
      **job,
      "proc": proc,
      "logf": logf,
      "log_path": str(log_path),
      "pid": proc.pid,
      "t0": t0,
      "status": "running",
    }

  def _finalize(job: dict) -> dict:
    proc = job["proc"]
    rc = proc.poll()
    if rc is None:
      rc = proc.wait()
    try:
      job["logf"].close()
    except Exception:
      pass
    elapsed = round(time.time() - job["t0"], 1)
    last = _book_last(job["symbol"], job["timeframe"])
    entry = {
      "symbol": job["symbol"],
      "timeframe": job["timeframe"],
      "rc": rc,
      "pid": job["pid"],
      "elapsed_sec": elapsed,
      "summary": last,
      "log": job["log_path"],
      "status": "completed" if rc == 0 else "failed",
    }
    arch = RESULTS_DIR / f"replay_oos_{job['symbol'].lower()}_{job['timeframe'].lower()}.json"
    arch.write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
      f"## Done {job['symbol']} {job['timeframe']} rc={rc} "
      f"elapsed={elapsed}s fills={last.get('n_fills')}",
      flush=True,
    )
    return entry

  idx = 0
  while pending or running:
    while pending and len(running) < max_workers:
      running.append(_spawn(pending.pop(0)))
      idx += 1

    # Snapshot progress for UI
    results["books"] = finished + [
      {
        "symbol": j["symbol"],
        "timeframe": j["timeframe"],
        "pid": j["pid"],
        "status": "running",
        "rc": None,
      }
      for j in running
    ]
    results["updated_at"] = _now()
    _write_batch(results)

    alive = []
    for j in running:
      if j["proc"].poll() is None:
        alive.append(j)
      else:
        finished.append(_finalize(j))
    running = alive
    if running or pending:
      time.sleep(1.0)

  results["books"] = finished
  results["finished_at"] = _now()
  results["status"] = "completed"
  results["force_remine"] = os.environ.get("LIVE_REPLAY_FORCE_REMINE", "").strip().lower() in (
    "1", "true", "yes", "on",
  )
  results["ok"] = all(b.get("rc") == 0 for b in results["books"])
  _write_batch(results)
  print(f"\nWrote {OUT}", flush=True)
  try:
    from replay_history import archive_live_like_run
    from replay_control import paper_results_summary
    archive_live_like_run(paper_results_summary())
    print("Archived Live-like run into replay_history/", flush=True)
  except Exception as exc:
    print(f"Archive warn: {exc}", flush=True)
  return 0 if results["ok"] else 1


if __name__ == "__main__":
  raise SystemExit(main())
