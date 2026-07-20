"""SQLite persistence for runs, reports, jobs."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from .contracts import JobEvent, Report, RunSpec
from .paths import DB_PATH, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  spec_json TEXT NOT NULL,
  label TEXT,
  error TEXT
);

CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  pair TEXT,
  timeframe TEXT,
  use_kb INTEGER,
  kb_profile TEXT,
  oos_from TEXT,
  oos_to TEXT,
  win_rate_pct REAL,
  avg_rr REAL,
  total_r REAL,
  n_trades INTEGER,
  report_json TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES runs(id)
);

CREATE TABLE IF NOT EXISTS job_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL,
  current INTEGER,
  total INTEGER,
  message TEXT,
  payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_reports_run ON reports(run_id);
CREATE INDEX IF NOT EXISTS idx_events_job ON job_events(job_id);
"""


def _utc_now() -> str:
  return datetime.now(timezone.utc).isoformat()


class Store:
  def __init__(self, db_path: Path | None = None):
    ensure_dirs()
    self.db_path = Path(db_path or DB_PATH)
    self._init_db()

  def _init_db(self) -> None:
    with self.connect() as con:
      con.executescript(SCHEMA)

  @contextmanager
  def connect(self) -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(self.db_path)
    con.row_factory = sqlite3.Row
    try:
      yield con
      con.commit()
    finally:
      con.close()

  def create_run(self, spec: RunSpec, *, status: str = "queued") -> str:
    run_id = uuid.uuid4().hex[:12]
    now = _utc_now()
    with self.connect() as con:
      con.execute(
        "INSERT INTO runs (id, kind, status, created_at, updated_at, spec_json, label) VALUES (?,?,?,?,?,?,?)",
        (
          run_id,
          spec.kind.value,
          status,
          now,
          now,
          spec.model_dump_json(),
          spec.label,
        ),
      )
    return run_id

  def update_run(self, run_id: str, *, status: str, error: str | None = None) -> None:
    with self.connect() as con:
      con.execute(
        "UPDATE runs SET status=?, updated_at=?, error=? WHERE id=?",
        (status, _utc_now(), error, run_id),
      )

  def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
    with self.connect() as con:
      row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    return dict(row) if row else None

  def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
    with self.connect() as con:
      rows = con.execute(
        "SELECT id, kind, status, created_at, label, error FROM runs ORDER BY created_at DESC LIMIT ?",
        (limit,),
      ).fetchall()
    return [dict(r) for r in rows]

  def save_report(self, run_id: str, report: Report) -> str:
    report_id = report.id or uuid.uuid4().hex[:12]
    report.id = report_id
    oos = report.overall_oos
    with self.connect() as con:
      con.execute(
        """INSERT INTO reports (
          id, run_id, created_at, pair, timeframe, use_kb, kb_profile,
          oos_from, oos_to, win_rate_pct, avg_rr, total_r, n_trades, report_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
          report_id,
          run_id,
          _utc_now(),
          report.spec.instrument.pair,
          report.spec.instrument.timeframe,
          1 if report.spec.use_kb else 0,
          report.spec.kb_profile,
          report.spec.oos_from_str(),
          report.spec.oos_to_str(),
          oos.win_rate_pct if oos else None,
          oos.avg_rr if oos else None,
          oos.total_r if oos else None,
          oos.n_trades if oos else None,
          report.model_dump_json(),
        ),
      )
    return report_id

  def get_report(self, report_id: str) -> Optional[Report]:
    with self.connect() as con:
      row = con.execute("SELECT report_json FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
      return None
    return Report.model_validate_json(row["report_json"])

  def list_reports(self, limit: int = 50) -> list[dict[str, Any]]:
    with self.connect() as con:
      rows = con.execute(
        """SELECT id, run_id, created_at, pair, timeframe, use_kb, kb_profile,
                  oos_from, oos_to, win_rate_pct, avg_rr, total_r, n_trades
           FROM reports ORDER BY created_at DESC LIMIT ?""",
        (limit,),
      ).fetchall()
    return [dict(r) for r in rows]

  def compare_reports(self, report_ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for rid in report_ids:
      with self.connect() as con:
        row = con.execute(
          """SELECT id, use_kb, kb_profile, oos_from, oos_to,
                    win_rate_pct, avg_rr, total_r, n_trades
             FROM reports WHERE id=?""",
          (rid,),
        ).fetchone()
      if row:
        out.append(dict(row))
    return out

  def append_event(self, event: JobEvent) -> None:
    with self.connect() as con:
      con.execute(
        """INSERT INTO job_events (job_id, created_at, status, current, total, message, payload_json)
           VALUES (?,?,?,?,?,?,?)""",
        (
          event.job_id,
          _utc_now(),
          event.status,
          event.current,
          event.total,
          event.message,
          json.dumps(event.payload),
        ),
      )

  def latest_event(self, job_id: str) -> Optional[dict[str, Any]]:
    with self.connect() as con:
      row = con.execute(
        "SELECT * FROM job_events WHERE job_id=? ORDER BY id DESC LIMIT 1",
        (job_id,),
      ).fetchone()
    return dict(row) if row else None
