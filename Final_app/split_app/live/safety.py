"""Live safety: flatten, kill-switch, loss-guard config helpers."""
from __future__ import annotations

import json
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import BRIDGE_DIR, RESULTS_DIR
from package_store import load_roster

KILL_SWITCH_PATH = RESULTS_DIR / "kill_switch.json"
CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
PID_PATH = RESULTS_DIR / "mt5_bridge_service.pid"


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
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def _pid_alive(pid: int | None) -> bool:
  if not pid:
    return False
  try:
    os.kill(int(pid), 0)
    return True
  except OSError:
    return False


def write_flatten_command(
  *,
  bridge_dir: Path | None = None,
  reason: str = "live_flatten",
) -> dict:
  """Ask EA to close all roster magics via command.json."""
  bdir = Path(bridge_dir or BRIDGE_DIR)
  bdir.mkdir(parents=True, exist_ok=True)
  payload = {
    "cmd": "close",
    "action": "FLAT",
    "signal_id": f"live_flatten_{int(datetime.now().timestamp())}",
    "reason": reason,
    "updated_at": _now(),
  }
  _write(bdir / "command.json", payload)
  # Also force FLAT decisions so remine won't re-open until next cycle clears
  flat = {
    "action": "FLAT",
    "reason": reason,
    "halt": False,
    "updated_at": _now(),
  }
  _write(bdir / "decision.json", flat)
  dec_dir = bdir / "decisions"
  dec_dir.mkdir(exist_ok=True)
  roster = load_roster()
  for row in roster.get("models") or []:
    mid = row.get("model_id")
    if mid and row.get("enabled"):
      _write(dec_dir / f"{mid}.json", {**flat, "model_id": mid})
  return payload


def arm_kill_switch(*, reason: str = "manual_kill_switch", flatten: bool = True) -> dict:
  """Hard stop: flag file + disable config + SIGTERM bridge + optional flatten."""
  payload = {
    "armed": True,
    "reason": reason,
    "armed_at": _now(),
  }
  _write(KILL_SWITCH_PATH, payload)

  cfg = _read(CONFIG_PATH) or {}
  cfg.update({
    "enabled": False,
    "kill_switch": True,
    "kill_switch_reason": reason,
    "kill_switch_at": payload["armed_at"],
    "last_action": "kill_switch",
    "last_error": reason,
  })
  _write(CONFIG_PATH, cfg)

  pid = cfg.get("service_pid")
  if not pid and PID_PATH.exists():
    try:
      pid = int(PID_PATH.read_text(encoding="utf-8").strip())
    except ValueError:
      pid = None
  if _pid_alive(pid):
    try:
      os.kill(int(pid), signal.SIGTERM)
    except OSError:
      pass

  if flatten:
    write_flatten_command(reason=f"kill_switch:{reason}")

  status = {
    "updated_at": _now(),
    "state": "halted",
    "halt_source": "kill_switch",
    "reason": reason,
  }
  _write(BRIDGE_DIR / "status.json", status)
  return payload


def disarm_kill_switch() -> dict:
  payload = {"armed": False, "disarmed_at": _now()}
  _write(KILL_SWITCH_PATH, payload)
  cfg = _read(CONFIG_PATH) or {}
  cfg.update({
    "kill_switch": False,
    "kill_switch_reason": None,
    "last_action": "kill_switch_disarm",
  })
  _write(CONFIG_PATH, cfg)
  return payload


def is_kill_switch_armed() -> bool:
  data = _read(KILL_SWITCH_PATH) or {}
  return bool(data.get("armed"))


def default_loss_guard_from_roster() -> dict[str, Any]:
  """Conservative defaults; Max DD from package metrics when present."""
  max_day = 3
  max_week = 5
  for row in (load_roster().get("models") or []):
    if not row.get("enabled"):
      continue
    from live_config import INSTALLED_DIR
    install = INSTALLED_DIR / str(row.get("install_id") or "")
    metrics = _read(install / "metrics.json") or {}
    model = _read(install / "model.json") or {}
    dd = metrics.get("max_drawdown_r") or model.get("max_drawdown_r")
    try:
      if dd is not None:
        # Match lab: int(max_dd)+1 as day streak limit floor
        max_day = max(max_day, int(float(dd)) + 1)
    except (TypeError, ValueError):
      pass
  return {
    "loss_guard_enabled": True,
    "loss_guard_max_day": int(max_day),
    "loss_guard_max_week": int(max_week),
    "loss_guard_tripped": False,
    "loss_guard_tripped_at": None,
    "loss_guard_tripped_reason": None,
  }
