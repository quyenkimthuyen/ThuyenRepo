from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JOB_DIR = Path("output/optimize_jobs")


def _job_path(job_id: str) -> Path:
    return JOB_DIR / f"{job_id}.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_job(job_id: str) -> dict[str, Any] | None:
    path = _job_path(job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_job(job: dict[str, Any]) -> Path:
    JOB_DIR.mkdir(parents=True, exist_ok=True)
    path = _job_path(job["job_id"])
    path.write_text(json.dumps(job, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def list_jobs(limit: int = 8) -> list[dict[str, Any]]:
    if not JOB_DIR.exists():
        return []
    jobs = []
    for path in sorted(JOB_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            jobs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
        if len(jobs) >= limit:
            break
    return jobs


def start_optimize_job(
    *,
    train_years: list[int],
    trade_years: list[int],
    equity: float,
    sl_pct: float,
    min_rr: float,
    advanced_search: bool,
    advanced_runs: int,
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    runs = int(advanced_runs) if advanced_search else 1
    job = {
        "job_id": job_id,
        "status": "queued",
        "created_at": _now(),
        "updated_at": _now(),
        "train_years": [int(y) for y in train_years],
        "trade_years": [int(y) for y in trade_years],
        "equity": float(equity),
        "sl_pct": float(sl_pct),
        "min_rr": float(min_rr),
        "advanced_search": bool(advanced_search),
        "advanced_runs": runs,
        "progress": 0,
        "total": max(1, len(train_years) * runs),
        "message": "Đã tạo job",
        "results": [],
    }
    write_job(job)
    subprocess.Popen(
        [sys.executable, "-m", "systemtrain.ui.optimize_job_runner", "--job-id", job_id],
        cwd=Path.cwd(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return job
