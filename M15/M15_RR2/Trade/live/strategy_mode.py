"""Live strategy mode: weekly remine vs frozen genome (no weekly remine).

Prefs: ``live/results/strategy_mode.json``
Override: env ``LIVE_STRATEGY_MODE=weekly|frozen``
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import RESULTS_DIR

PREFS_PATH = RESULTS_DIR / "strategy_mode.json"
MODES = ("weekly", "frozen")
DEFAULT_PREFS: dict[str, Any] = {
  "mode": "weekly",
}


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(f"{path.stem}.{os.getpid()}.{time.time_ns()}.tmp")
  tmp.write_text(
    json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  tmp.replace(path)


def load_prefs() -> dict[str, Any]:
  data = _read(PREFS_PATH) or {}
  out = dict(DEFAULT_PREFS)
  if isinstance(data, dict):
    mode = str(data.get("mode") or "weekly").strip().lower()
    out["mode"] = mode if mode in MODES else "weekly"
    if data.get("updated_at"):
      out["updated_at"] = data["updated_at"]
  return out


def save_prefs(updates: dict[str, Any] | None = None) -> dict[str, Any]:
  prefs = load_prefs()
  if updates:
    prefs.update(updates)
  mode = str(prefs.get("mode") or "weekly").strip().lower()
  prefs["mode"] = mode if mode in MODES else "weekly"
  prefs["updated_at"] = _now()
  _write(PREFS_PATH, prefs)
  return prefs


def strategy_mode() -> str:
  env = str(os.environ.get("LIVE_STRATEGY_MODE") or "").strip().lower()
  if env in MODES:
    return env
  return str(load_prefs().get("mode") or "weekly")


def frozen_enabled() -> bool:
  return strategy_mode() == "frozen"


def week_key(week_start: Any) -> str:
  s = str(week_start or "").strip()
  if hasattr(week_start, "date"):
    try:
      s = str(week_start.date())
    except Exception:
      s = str(week_start)
  return s[:10]


def merge_weekly(
  schedule: dict | None,
  live_weeks: dict | None,
) -> dict[str, dict]:
  """Exact-week lookup order: schedule wins, then live_weeks fill gaps."""
  out: dict[str, dict] = {}
  for payload in (live_weeks, schedule):
    if not isinstance(payload, dict):
      continue
    for row in payload.get("weekly") or []:
      if not isinstance(row, dict) or "strategy" not in row:
        continue
      ws = str(row.get("week_start") or "")[:10]
      if len(ws) >= 10:
        out[ws] = row
  return out


def pick_carry_forward(merged: dict[str, dict], week_start: Any) -> dict | None:
  """Latest freeze with week_start <= requested week (same genome, no remine)."""
  key = week_key(week_start)
  if not key or not merged:
    return None
  eligible = [(ws, row) for ws, row in merged.items() if ws <= key]
  if not eligible:
    return None
  eligible.sort(key=lambda x: x[0])
  return eligible[-1][1]


def carry_forward_week_strategy(
  model_id: str,
  week_start: Any,
  *,
  schedule: dict | None = None,
  live_weeks: dict | None = None,
) -> dict | None:
  """Reuse the newest schedule/live_weeks genome at or before this week."""
  sched = schedule
  live = live_weeks
  if sched is None or live is None:
    try:
      from trade_model_schedule import load_live_weeks, load_model_schedule
    except Exception:
      load_live_weeks = load_model_schedule = None  # type: ignore
    if sched is None and load_model_schedule is not None:
      sched = load_model_schedule(model_id)
    if live is None and load_live_weeks is not None:
      live = load_live_weeks(model_id)
  return pick_carry_forward(merge_weekly(sched, live), week_start)
