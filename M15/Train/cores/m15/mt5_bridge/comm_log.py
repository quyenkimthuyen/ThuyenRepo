"""Append-only communication log between App and MT5 ForgeBridge EA."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mt5_bridge.protocol import BRIDGE_DIR, ensure_bridge_dir

COMM_LOG_NAME = "comm_log.jsonl"
MAX_LINES_DEFAULT = 500


def comm_log_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / COMM_LOG_NAME


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_event(
  direction: str,
  event: str,
  *,
  bridge_dir: Path | None = None,
  payload: dict | None = None,
  summary: str | None = None,
) -> None:
  """
  direction: app_to_ea | ea_to_app | app | system
  event: bar_received | decision_sent | fill_received | status | error | ...
  """
  path = comm_log_path(bridge_dir)
  row = {
    "ts": _now(),
    "direction": direction,
    "event": event,
    "summary": summary or "",
    "payload": payload or {},
  }
  with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def read_events(
  *,
  bridge_dir: Path | None = None,
  limit: int = MAX_LINES_DEFAULT,
) -> list[dict[str, Any]]:
  path = comm_log_path(bridge_dir)
  if not path.exists():
    return []
  lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
  out: list[dict[str, Any]] = []
  for line in lines[-max(1, limit):]:
    line = line.strip()
    if not line:
      continue
    try:
      out.append(json.loads(line))
    except json.JSONDecodeError:
      continue
  return out


def clear_log(bridge_dir: Path | None = None) -> None:
  path = comm_log_path(bridge_dir)
  if path.exists():
    path.write_text("", encoding="utf-8")
