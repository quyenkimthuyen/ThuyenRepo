"""Shared JSON file protocol between ForgeBridge EA and App service."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DIR = ROOT / "mt5" / "bridge_m15a6"
BRIDGE_SIM_DIR = ROOT / "mt5" / "bridge_sim_m15a6"

BAR_NAME = "bar.json"
BARS_NAME = "bars.json"
CONNECTION_NAME = "connection.json"
HISTORY_REQUEST_NAME = "history_request.json"
HISTORY_CHUNK_NAME = "history_chunk.json"
HISTORY_ACK_NAME = "history_ack.json"
HISTORY_STATUS_NAME = "history_status.json"
DECISION_NAME = "decision.json"
COMMAND_NAME = "command.json"
COMMAND_ACK_NAME = "command_ack.json"
FILL_NAME = "fill.json"
STATUS_NAME = "status.json"
REPLAY_NAME = "replay_decisions.json"
REPLAY_CSV_NAME = "replay_signals.csv"
SIM_CONTROL_NAME = "sim_control.json"

DEFAULT_MODEL_ID = ""
DEFAULT_MAGIC = 20261006
DEFAULT_SIM_MAGIC = 20262006
DEFAULT_TIMEFRAME = "M15"
INSTANCE_ID = "M15A6"


def ensure_bridge_dir(path: Path | None = None) -> Path:
  d = path or BRIDGE_DIR
  d.mkdir(parents=True, exist_ok=True)
  return d


def safe_replace(src: Path, dst: Path, attempts: int = 5, delay: float = 0.05) -> None:
  dst.parent.mkdir(parents=True, exist_ok=True)
  for attempt in range(attempts):
    try:
      src.replace(dst)
      return
    except OSError as err:
      if attempt < attempts - 1:
        time.sleep(delay)
      else:
        try:
          import shutil
          shutil.copy2(src, dst)
          if src.exists():
            src.unlink(missing_ok=True)
          return
        except Exception:
          if src.exists():
            try:
              src.unlink(missing_ok=True)
            except Exception:
              pass
          raise err


def atomic_write_json(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  with open(tmp, "w", encoding="utf-8", newline="\n") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
  try:
    safe_replace(tmp, path)
  except Exception:
    try:
      with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
      if tmp.exists():
        tmp.unlink(missing_ok=True)
    except Exception:
      pass



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


def command_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / COMMAND_NAME


def command_ack_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / COMMAND_ACK_NAME


def fill_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / FILL_NAME


def status_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / STATUS_NAME


def replay_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REPLAY_NAME


def replay_csv_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir) / REPLAY_CSV_NAME


def sim_control_path(bridge_dir: Path | None = None) -> Path:
  return ensure_bridge_dir(bridge_dir or BRIDGE_SIM_DIR) / SIM_CONTROL_NAME


def read_sim_control(bridge_dir: Path | None = None) -> dict[str, Any]:
  data = read_json(sim_control_path(bridge_dir))
  return data if isinstance(data, dict) else {}


def write_sim_control(
  bridge_dir: Path | None = None,
  *,
  merge: bool = True,
  **fields: Any,
) -> dict[str, Any]:
  """Write App→EA history-feed control file (EA updates ea_status/bars_*)."""
  path = sim_control_path(bridge_dir)
  cur: dict[str, Any] = {}
  if merge:
    prev = read_json(path)
    if isinstance(prev, dict):
      cur.update(prev)
  cur.update(fields)
  cur["updated_at"] = utc_now_iso()
  atomic_write_json(path, cur)
  return cur


def utc_now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _manual_signal_id(prefix: str = "manual_test") -> str:
  return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def pip_size_from_quotes(*, digits: int | None = None, point: float | None = None) -> float:
  """Estimate 1 pip in price units (EURUSD 5-digit → 0.0001)."""
  if point is not None and float(point) > 0:
    d = int(digits) if digits is not None else (5 if float(point) < 0.001 else 4)
    return float(point) * (10.0 if d in (3, 5) else 1.0)
  if digits is not None:
    d = int(digits)
    if d in (3, 5):
      return 10.0 ** -(d - 1)
    return 10.0 ** -d
  return 0.0001


def prices_from_pips(
  action: str,
  *,
  bid: float,
  ask: float,
  sl_pips: float,
  tp_pips: float,
  pip_size: float | None = None,
) -> tuple[float, float, float]:
  """Return (entry_ref, sl, tp) for a market test order."""
  act = action.upper()
  pip = float(pip_size) if pip_size and pip_size > 0 else 0.0001
  if act == "BUY":
    entry = float(ask)
    return entry, entry - float(sl_pips) * pip, entry + float(tp_pips) * pip
  if act == "SELL":
    entry = float(bid)
    return entry, entry + float(sl_pips) * pip, entry - float(tp_pips) * pip
  raise ValueError(f"action must be BUY/SELL, got {action!r}")


def write_manual_market_command(
  action: str,
  *,
  sl: float,
  tp: float,
  signal_id: str | None = None,
  bridge_dir: Path | None = None,
  exit_mode: str = "full",
  reason: str = "manual_bridge_test",
  **extra: Any,
) -> dict[str, Any]:
  """App → EA immediate market order via command.json (does not wait for new bar)."""
  act = str(action).upper()
  if act not in ("BUY", "SELL"):
    raise ValueError(f"action must be BUY/SELL, got {action!r}")
  payload: dict[str, Any] = {
    "cmd": "market",
    "action": act,
    "signal_id": signal_id or _manual_signal_id(),
    "sl": float(sl),
    "tp": float(tp),
    "exit_mode": exit_mode,
    "reason": reason,
    "updated_at": utc_now_iso(),
    **extra,
  }
  atomic_write_json(command_path(bridge_dir), payload)
  return payload


def write_manual_close_command(
  *,
  signal_id: str | None = None,
  bridge_dir: Path | None = None,
  reason: str = "manual_bridge_test_close",
  **extra: Any,
) -> dict[str, Any]:
  """App → EA immediate close of positions with bridge magic."""
  payload: dict[str, Any] = {
    "cmd": "close",
    "action": "FLAT",
    "signal_id": signal_id or _manual_signal_id("manual_close"),
    "reason": reason,
    "updated_at": utc_now_iso(),
    **extra,
  }
  atomic_write_json(command_path(bridge_dir), payload)
  return payload


def write_status(bridge_dir: Path | None = None, **fields: Any) -> None:
  payload = {"updated_at": utc_now_iso(), **fields}
  atomic_write_json(status_path(bridge_dir), payload)
