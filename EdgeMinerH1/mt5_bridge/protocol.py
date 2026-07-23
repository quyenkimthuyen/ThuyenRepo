"""Shared JSON file protocol between ForgeBridge EA and App service."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DIR = ROOT / "mt5" / "bridge"

BAR_NAME = "bar.json"
BARS_NAME = "bars.json"
CONNECTION_NAME = "connection.json"
HISTORY_REQUEST_NAME = "history_request.json"
HISTORY_CHUNK_NAME = "history_chunk.json"
HISTORY_ACK_NAME = "history_ack.json"
HISTORY_STATUS_NAME = "history_status.json"
DECISION_NAME = "decision.json"
FILL_NAME = "fill.json"
STATUS_NAME = "status.json"
REPLAY_NAME = "replay_decisions.json"
REPLAY_CSV_NAME = "replay_signals.csv"

DEFAULT_MODEL_ID = ""
DEFAULT_MAGIC = 20260724


def ensure_bridge_dir(path: Path | None = None) -> Path:
  d = path or BRIDGE_DIR
  d.mkdir(parents=True, exist_ok=True)
  return d


def atomic_write_json(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  with open(tmp, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
  tmp.replace(path)


def read_json(path: Path) -> dict | list | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except (OSError, json.JSONDecodeError):
    return None


def bar_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / BAR_NAME


def bars_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / BARS_NAME


def connection_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / CONNECTION_NAME


def history_request_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_REQUEST_NAME


def history_chunk_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_CHUNK_NAME


def history_ack_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_ACK_NAME


def history_status_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / HISTORY_STATUS_NAME


def decision_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / DECISION_NAME


def fill_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / FILL_NAME


def status_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / STATUS_NAME


def replay_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REPLAY_NAME


def replay_csv_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REPLAY_CSV_NAME


def utc_now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_status(bridge_dir: Path | None = None, **fields: Any) -> None:
  payload = {"updated_at": utc_now_iso(), **fields}
  atomic_write_json(status_path(bridge_dir), payload)
