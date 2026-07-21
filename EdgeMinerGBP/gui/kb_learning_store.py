"""Lưu trữ lịch sử báo cáo huấn luyện KB — không mất khi chạy era mới."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from run_backtest import REPORT_DIR

HISTORY_DIR = REPORT_DIR / "kb_learning"
INDEX_PATH = HISTORY_DIR / "index.json"


def _read_json(path: Path) -> dict | list | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path: Path, data):
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
  tmp.replace(path)


def load_history_index() -> list[dict]:
  data = _read_json(INDEX_PATH)
  if isinstance(data, list):
    return data
  if isinstance(data, dict) and isinstance(data.get("runs"), list):
    return data["runs"]
  return []


def save_history_index(runs: list[dict]):
  _write_json(INDEX_PATH, {"runs": runs})


def archive_learning_report(report: dict, *, note: str = "") -> str:
  """Lưu bản sao báo cáo + cập nhật index. Trả về run_id."""
  HISTORY_DIR.mkdir(parents=True, exist_ok=True)
  ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
  profile = str(report.get("kb_profile") or "unknown")
  run_id = f"lr_{profile}_{ts}"
  payload = dict(report)
  payload["run_id"] = run_id
  payload["archived_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  if note:
    payload["note"] = note

  _write_json(HISTORY_DIR / f"{run_id}.json", payload)

  hist = report.get("epoch_history") or []
  last = hist[-1] if hist else {}
  entry = {
    "run_id": run_id,
    "archived_at": payload["archived_at"],
    "kb_profile": profile,
    "kb_name": report.get("kb_name") or profile,
    "epochs": report.get("epochs"),
    "trained_from": report.get("trained_from"),
    "trained_to": report.get("trained_to"),
    "last_total_r": last.get("total_r"),
    "last_win_rate_pct": last.get("win_rate_pct"),
    "genomes": (report.get("kb_summary") or {}).get("genomes"),
  }
  runs = load_history_index()
  runs.insert(0, entry)
  runs = runs[:50]
  save_history_index(runs)
  return run_id


def load_archived_report(run_id: str) -> dict | None:
  data = _read_json(HISTORY_DIR / f"{run_id}.json")
  return data if isinstance(data, dict) else None


def history_for_profile(profile_id: str) -> list[dict]:
  return [r for r in load_history_index() if r.get("kb_profile") == profile_id]
