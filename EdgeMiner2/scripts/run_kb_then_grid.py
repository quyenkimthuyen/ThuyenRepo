#!/usr/bin/env python3
"""Huấn luyện KB theo Cài đặt → chạy Grid Search."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

LOG = ROOT / "results" / "pipeline_run.log"


def log(msg: str):
  line = f"[{datetime.now().isoformat(timespec='seconds')}] {msg}"
  print(line, flush=True)
  LOG.parent.mkdir(parents=True, exist_ok=True)
  with open(LOG, "a", encoding="utf-8") as f:
    f.write(line + "\n")


def run_learning(profile_id: str, name: str, from_date: str, until_date: str, epochs: int):
  log(f"=== Học KB: {profile_id} ({epochs} vòng) ===")
  cmd = [
    sys.executable, str(ROOT / "run_learning.py"),
    "--epochs", str(epochs),
    "--reset",
    "--kb-profile", profile_id,
    "--kb-name", name,
    "--from-date", from_date,
    "--until-date", until_date,
  ]
  subprocess.run(cmd, cwd=str(ROOT), check=True)


def run_grid():
  from gui.app_settings import get_settings
  from gui.grid_search_engine import (
    build_grid_from_settings,
    grid_readiness,
    run_grid,
    save_grid_run,
  )

  r = grid_readiness()
  log(f"Grid readiness: {r['ready_combos']}/{r['expected_combos']} kb_complete={r['kb_complete']}")
  if not r["kb_complete"]:
    raise RuntimeError(f"KB chưa đủ: {r}")

  specs, config = build_grid_from_settings()
  objective = get_settings().get("grid_objective", "total_r")
  log(f"=== Grid Search: {len(specs)} combo · mục tiêu {objective} ===")

  def on_prog(done, total, label):
    log(f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog)
  rid = save_grid_run(rows, config=config, objective=objective)
  ok = [x for x in rows if not x.get("error")]
  log(f"Grid xong: {rid} · {len(ok)}/{len(rows)} combo OK")
  if ok:
    best = ok[0]
    log(f"Best: {best.get('label')} · {best.get('total_r')}R")


def main():
  from gui.app_settings import get_settings, resolve_learning_eras

  # Dọn job GUI kẹt
  job_path = ROOT / "results" / "jobs" / "long_task_state.json"
  if job_path.exists():
    try:
      data = json.loads(job_path.read_text(encoding="utf-8"))
      if data.get("status") == "running":
        data["status"] = "interrupted"
        data["error"] = "Thay bằng pipeline CLI"
        job_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log("Đã đánh dấu job GUI cũ là interrupted")
    except Exception:
      pass

  s = get_settings()
  loops = int(s.get("learning_loops") or 4)
  eras = resolve_learning_eras(s)
  log(f"Settings: {[e['kb_profile'] for e in eras]} · {loops} vòng · OOS {s.get('backtest_from')}–{s.get('backtest_to')}")

  for era in eras:
    run_learning(
      era["kb_profile"],
      era["label"],
      era["learn_from"],
      era["learn_until"],
      loops,
    )

  run_grid()
  log("=== HOÀN TẤT ===")
  return 0


if __name__ == "__main__":
  sys.exit(main())
