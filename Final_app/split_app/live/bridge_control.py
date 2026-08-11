"""Start/stop Live MT5 bridge decision service (package remine engine)."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from chart_validate import validate_chart_vs_roster
from live_config import BRIDGE_DIR, LIVE_ROOT, RESULTS_DIR
from materialize_models import materialize_enabled
from package_store import load_roster
from safety import default_loss_guard_from_roster, is_kill_switch_armed
from sync_bridge_roster import write_models_json
from magic_allocator import assign_magics
from shared.constants import LIVE_BRIDGE_PORT, LIVE_MAGIC_BASE

CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
PID_PATH = RESULTS_DIR / "mt5_bridge_service.pid"
SERVICE_LOG = RESULTS_DIR / "mt5_bridge_service.log"
SERVICE_SCRIPT = LIVE_ROOT / "scripts" / "mt5_bridge_service_live.py"


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


def load_config() -> dict:
  return _read(CONFIG_PATH) or {}


def save_config(**updates) -> dict:
  cfg = load_config()
  cfg.update(updates)
  cfg["updated_at"] = _now()
  _write(CONFIG_PATH, cfg)
  return cfg


def service_pid() -> int | None:
  cfg = load_config()
  pid = cfg.get("service_pid")
  if pid and _pid_alive(pid):
    return int(pid)
  if PID_PATH.exists():
    try:
      pid = int(PID_PATH.read_text(encoding="utf-8").strip())
      return pid if _pid_alive(pid) else None
    except ValueError:
      return None
  return None


def is_running() -> bool:
  return service_pid() is not None


def prepare_runtime(
  *,
  require_chart: bool = False,
  poll_sec: float = 2.0,
) -> dict[str, Any]:
  """Materialize packages, sync EA roster, write bridge config."""
  if is_kill_switch_armed():
    raise RuntimeError("Kill-switch armed — disarm before Start")

  roster = load_roster()
  models = roster.get("models") or []
  models = assign_magics(models, sim=False)
  from package_store import save_roster
  save_roster(models)

  mat = materialize_enabled(roster={"models": models})
  write_models_json(BRIDGE_DIR, models, base_magic=LIVE_MAGIC_BASE)

  check = validate_chart_vs_roster(
    bridge_dir=BRIDGE_DIR,
    roster_rows=[r for r in models if r.get("enabled")],
    require_ea_online=require_chart,
  )
  if not check["ok"]:
    raise RuntimeError("Chart/package validation failed: " + "; ".join(check["errors"]))

  guard = default_loss_guard_from_roster()
  primary_risk = 1.0
  for r in models:
    if r.get("enabled"):
      primary_risk = float(r.get("risk_pct") or 1.0)
      break

  cfg = save_config(
    enabled=False,
    mode="process",
    bridge_dir=str(BRIDGE_DIR),
    model_ids=mat["model_ids"],
    model_id=mat["model_ids"][0] if mat["model_ids"] else None,
    risk_pct=primary_risk,
    poll_sec=float(poll_sec),
    symbol=mat["symbol"],
    timeframe=mat["timeframe"],
    monitor_port=LIVE_BRIDGE_PORT,
    **guard,
    last_error=None,
  )
  return {"materialize": mat, "validation": check, "config": cfg}


def start_bridge(
  *,
  require_chart: bool = False,
  poll_sec: float = 2.0,
  once: bool = False,
) -> dict[str, Any]:
  prep = prepare_runtime(require_chart=require_chart, poll_sec=poll_sec)
  if is_running() and not once:
    save_config(enabled=True)
    return {"already_running": True, "pid": service_pid(), **prep}

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  mat = prep["materialize"]
  cfg = prep["config"]
  cmd = [
    sys.executable,
    str(SERVICE_SCRIPT),
    "--bridge-dir", str(BRIDGE_DIR),
    "--symbol", mat["symbol"],
    "--timeframe", mat["timeframe"],
    "--risk-pct", str(cfg.get("risk_pct") or 1.0),
    "--poll", str(poll_sec),
    "--monitor-port", str(LIVE_BRIDGE_PORT),
    "--model-ids", ",".join(mat["model_ids"]),
  ]
  if once:
    cmd.append("--once")

  SERVICE_LOG.parent.mkdir(parents=True, exist_ok=True)
  logf = open(SERVICE_LOG, "a", encoding="utf-8")
  logf.write(f"\n--- start {_now()} ---\n")
  logf.flush()
  proc = subprocess.Popen(
    cmd,
    cwd=str(LIVE_ROOT),
    stdout=logf,
    stderr=subprocess.STDOUT,
    start_new_session=True,
    close_fds=True,
  )
  PID_PATH.write_text(str(proc.pid), encoding="utf-8")
  save_config(enabled=not once, mode="process", service_pid=proc.pid, last_action="start")
  _write(BRIDGE_DIR / "status.json", {
    "updated_at": _now(),
    "state": "starting",
    "pid": proc.pid,
    "model_ids": mat["model_ids"],
  })
  return {"pid": proc.pid, "once": once, **prep}


def stop_bridge(*, flatten: bool = False) -> dict[str, Any]:
  pid = service_pid()
  save_config(enabled=False, last_action="stop")
  if pid:
    try:
      os.kill(int(pid), signal.SIGTERM)
    except OSError:
      pass
    for _ in range(40):
      if not _pid_alive(pid):
        break
      time.sleep(0.1)
    if _pid_alive(pid):
      try:
        os.kill(int(pid), signal.SIGKILL)
      except OSError:
        pass
  if PID_PATH.exists():
    try:
      PID_PATH.unlink()
    except OSError:
      pass
  save_config(service_pid=None)
  if flatten:
    from safety import write_flatten_command
    write_flatten_command(reason="bridge_stop")
  _write(BRIDGE_DIR / "status.json", {"updated_at": _now(), "state": "stopped"})
  return {"stopped": True, "pid": pid}


def status() -> dict[str, Any]:
  cfg = load_config()
  pid = service_pid()
  bridge_status = _read(BRIDGE_DIR / "status.json") or {}
  return {
    "running": pid is not None,
    "pid": pid,
    "config": cfg,
    "bridge_status": bridge_status,
    "kill_switch": is_kill_switch_armed(),
    "log": str(SERVICE_LOG),
  }
