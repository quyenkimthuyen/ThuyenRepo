"""Detached Paper Monitor service lifecycle and persisted runtime settings."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from run_backtest import REPORT_DIR

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = REPORT_DIR / "paper_monitor_config.json"
STATE_PATH = REPORT_DIR / "paper_monitor_state.json"
PID_PATH = REPORT_DIR / "paper_monitor_service.pid"
SERVICE_LOG = REPORT_DIR / "paper_monitor_service.log"
SERVICE_SCRIPT = ROOT / "scripts" / "paper_monitor_service.py"
_lock = threading.RLock()


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8-sig") as handle:
      value = json.load(handle)
    return value if isinstance(value, dict) else None
  except (OSError, json.JSONDecodeError):
    return None


def _write_json(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  with open(tmp, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2, ensure_ascii=False)
  tmp.replace(path)


def load_config() -> dict:
  raw = _read_json(CONFIG_PATH) or {}
  return {
    **raw,
    "enabled": bool(raw.get("enabled", False)),
    "mode": "process",
    "model_id": raw.get("model_id"),
    "risk_pct": float(raw.get("risk_pct", 1.0)),
    "poll_sec": float(raw.get("poll_sec", 2.0)),
    "use_learning": bool(raw.get("use_learning", True)),
    "kb_profile": raw.get("kb_profile") or "default",
    "kb_snapshot": raw.get("kb_snapshot"),
    "spread_pips": float(raw.get("spread_pips", 1.0)),
    "slippage_pips": float(raw.get("slippage_pips", 0.3)),
    "service_pid": raw.get("service_pid"),
  }


def save_config(**updates) -> dict:
  with _lock:
    cfg = load_config()
    nullable = {
      "model_id", "service_pid", "last_error", "last_run_at",
      "last_bar", "last_model_reload_at",
    }
    for key, value in updates.items():
      if value is None and key not in nullable:
        continue
      cfg[key] = value
    cfg.pop("interval_minutes", None)
    cfg.pop("next_run_at", None)
    cfg.pop("running", None)
    cfg["mode"] = "process"
    _write_json(CONFIG_PATH, cfg)
    return cfg


def load_saved_state() -> dict | None:
  return _read_json(STATE_PATH)


def _pid_alive(pid: int | None) -> bool:
  if not pid:
    return False
  if os.name == "nt":
    try:
      import ctypes
      from ctypes import wintypes

      kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
      handle = kernel32.OpenProcess(0x1000, False, int(pid))
      if not handle:
        return False
      try:
        exit_code = wintypes.DWORD()
        return bool(
          kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
          and exit_code.value == 259
        )
      finally:
        kernel32.CloseHandle(handle)
    except (OSError, TypeError, ValueError):
      return False
  try:
    os.kill(int(pid), 0)
    return True
  except (OSError, TypeError, ValueError):
    return False


def _read_pid() -> int | None:
  try:
    return int(PID_PATH.read_text(encoding="utf-8").strip())
  except (OSError, ValueError):
    return None


def _clear_pid() -> None:
  save_config(service_pid=None)
  PID_PATH.unlink(missing_ok=True)


def is_running() -> bool:
  cfg = load_config()
  pid = cfg.get("service_pid") or _read_pid()
  if _pid_alive(pid):
    return True
  if pid or PID_PATH.exists():
    _clear_pid()
  return False


def is_background_enabled() -> bool:
  return bool(load_config().get("enabled"))


def get_status() -> dict:
  cfg = load_config()
  running = is_running()
  pid = cfg.get("service_pid") or _read_pid()
  state = load_saved_state() or {}
  return {
    **cfg,
    "running": running,
    "runtime_mode": "process" if running else "off",
    "service_pid": int(pid) if running and pid else None,
    "updated_at": state.get("updated_at"),
    "last_bar": state.get("last_bar") or cfg.get("last_bar"),
    "strategy_name": (state.get("strategy") or {}).get("name"),
  }


def get_background_status() -> dict:
  """Compatibility alias used by existing UI fragments."""
  return get_status()


def start_worker() -> bool:
  with _lock:
    if is_running():
      save_config(enabled=True)
      return True
    cfg = load_config()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = open(SERVICE_LOG, "a", encoding="utf-8")
    log_handle.write(f"\n--- start {_now_iso()} ---\n")
    log_handle.flush()
    proc = subprocess.Popen(
      [sys.executable, str(SERVICE_SCRIPT)],
      cwd=str(ROOT),
      stdout=log_handle,
      stderr=subprocess.STDOUT,
      start_new_session=True,
      close_fds=True,
    )
    log_handle.close()
    PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    save_config(
      enabled=True,
      service_pid=proc.pid,
      last_error=None,
      started_at=_now_iso(),
    )
    return True


def stop_worker() -> None:
  with _lock:
    cfg = save_config(enabled=False)
    pid = cfg.get("service_pid") or _read_pid()
    if _pid_alive(pid):
      try:
        os.kill(int(pid), signal.SIGTERM)
      except OSError:
        pass
      for _ in range(30):
        if not _pid_alive(pid):
          break
        time.sleep(0.1)
      if _pid_alive(pid):
        try:
          os.kill(int(pid), getattr(signal, "SIGKILL", signal.SIGTERM))
        except OSError:
          pass
    _clear_pid()


def ensure_worker_running() -> None:
  if load_config().get("enabled") and not is_running():
    start_worker()


def run_once_now(*, force_refresh: bool = False) -> dict:
  from paper_background import run_cycle_now

  return run_cycle_now(load_config(), force_refresh=force_refresh)

