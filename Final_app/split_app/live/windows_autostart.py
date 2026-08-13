"""Windows logon autostart for Live app + XM MT5.

Prefs: ``results/autostart_prefs.json``
Installs a per-user Scheduled Task that runs ``boot_autostart_windows.ps1``.
"""
from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import LIVE_ROOT, RESULTS_DIR

PREFS_PATH = RESULTS_DIR / "autostart_prefs.json"
BOOT_SCRIPT = LIVE_ROOT / "scripts" / "boot_autostart_windows.ps1"
INSTALL_SCRIPT = LIVE_ROOT / "scripts" / "install_autostart_windows.ps1"
TASK_NAME = "EdgeMinerLiveBoot"

DEFAULT_PREFS: dict[str, Any] = {
  "enabled": False,
  "start_mt5": True,
  "start_app": True,
  "start_bridge": False,  # trading workers — opt-in (safer after reboot)
  "delay_sec": 45,
  "port": 8601,
}


def is_windows() -> bool:
  return platform.system().lower().startswith("win")


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_prefs() -> dict[str, Any]:
  data = dict(DEFAULT_PREFS)
  if PREFS_PATH.exists():
    try:
      raw = json.loads(PREFS_PATH.read_text(encoding="utf-8"))
      if isinstance(raw, dict):
        data.update(raw)
    except (OSError, json.JSONDecodeError):
      pass
  data["enabled"] = bool(data.get("enabled"))
  data["start_mt5"] = bool(data.get("start_mt5", True))
  data["start_app"] = bool(data.get("start_app", True))
  data["start_bridge"] = bool(data.get("start_bridge", False))
  try:
    data["delay_sec"] = max(5, min(300, int(data.get("delay_sec") or 45)))
  except (TypeError, ValueError):
    data["delay_sec"] = 45
  try:
    data["port"] = int(data.get("port") or 8601)
  except (TypeError, ValueError):
    data["port"] = 8601
  return data


def save_prefs(**updates: Any) -> dict[str, Any]:
  cur = load_prefs()
  cur.update(updates)
  cur["updated_at"] = _now()
  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  PREFS_PATH.write_text(
    json.dumps(cur, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
  )
  return cur


def _run_ps(args: list[str], *, timeout_sec: float = 90.0) -> dict[str, Any]:
  if not is_windows():
    return {
      "ok": False,
      "skipped": True,
      "reason": "not_windows",
      "stdout": "",
      "stderr": "Autostart chỉ hỗ trợ Windows.",
      "code": 0,
    }
  script = INSTALL_SCRIPT
  if not script.is_file():
    return {
      "ok": False,
      "skipped": False,
      "reason": "missing_script",
      "stdout": "",
      "stderr": f"Missing {script}",
      "code": 2,
    }
  cmd = [
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", str(script),
    *args,
  ]
  try:
    res = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      check=False,
      cwd=str(LIVE_ROOT),
      timeout=max(30.0, float(timeout_sec)),
    )
  except subprocess.TimeoutExpired as e:
    return {
      "ok": False,
      "skipped": False,
      "reason": "timeout",
      "stdout": (e.stdout or "") if isinstance(e.stdout, str) else "",
      "stderr": f"Timeout after {timeout_sec:.0f}s",
      "code": 124,
    }
  except FileNotFoundError:
    return {
      "ok": False,
      "skipped": False,
      "reason": "powershell_missing",
      "stdout": "",
      "stderr": "powershell.exe not found",
      "code": 127,
    }
  return {
    "ok": res.returncode == 0,
    "skipped": False,
    "reason": None if res.returncode == 0 else f"exit_{res.returncode}",
    "stdout": res.stdout or "",
    "stderr": res.stderr or "",
    "code": int(res.returncode),
  }


def task_status() -> dict[str, Any]:
  prefs = load_prefs()
  if not is_windows():
    return {
      "windows": False,
      "task_installed": False,
      "prefs": prefs,
      "detail": "not_windows",
    }
  out = _run_ps(["-Action", "Status"], timeout_sec=45.0)
  installed = bool(out.get("ok")) and ("INSTALLED" in (out.get("stdout") or "").upper())
  return {
    "windows": True,
    "task_installed": installed,
    "prefs": prefs,
    "detail": ((out.get("stdout") or "") + "\n" + (out.get("stderr") or "")).strip(),
    "raw": out,
  }


def enable_autostart(
  *,
  start_mt5: bool = True,
  start_app: bool = True,
  start_bridge: bool = False,
  delay_sec: int = 45,
  port: int = 8601,
) -> dict[str, Any]:
  """Save prefs + register Scheduled Task (At logon)."""
  prefs = save_prefs(
    enabled=True,
    start_mt5=bool(start_mt5),
    start_app=bool(start_app),
    start_bridge=bool(start_bridge),
    delay_sec=int(delay_sec),
    port=int(port),
  )
  if not is_windows():
    return {
      "ok": True,
      "skipped": True,
      "reason": "not_windows",
      "prefs": prefs,
      "message": "Prefs saved. Install Scheduled Task on Windows machine.",
    }
  out = _run_ps([
    "-Action", "Install",
    "-DelaySec", str(int(delay_sec)),
    "-Port", str(int(port)),
  ], timeout_sec=90.0)
  return {
    "ok": bool(out.get("ok")),
    "skipped": False,
    "prefs": prefs,
    "task": out,
    "message": (out.get("stdout") or out.get("stderr") or "").strip(),
  }


def disable_autostart() -> dict[str, Any]:
  prefs = save_prefs(enabled=False, start_bridge=False)
  if not is_windows():
    return {
      "ok": True,
      "skipped": True,
      "reason": "not_windows",
      "prefs": prefs,
      "message": "Prefs cleared. Uninstall task on Windows if present.",
    }
  out = _run_ps(["-Action", "Uninstall"], timeout_sec=60.0)
  return {
    "ok": bool(out.get("ok")),
    "skipped": False,
    "prefs": prefs,
    "task": out,
    "message": (out.get("stdout") or out.get("stderr") or "").strip(),
  }


def sync_autostart_with_trading(
  *,
  active: bool,
  delay_sec: int | None = None,
  port: int | None = None,
) -> dict[str, Any]:
  """Default lifecycle: Start trading → install autostart; Stop → uninstall.

  On Start: MT5 + Live app + bridge workers after reboot.
  On Stop / kill: remove Scheduled Task so reboot does not resume.
  Best-effort — never raises to callers. Skip with LIVE_SKIP_AUTOSTART=1.
  """
  import os
  if str(os.environ.get("LIVE_SKIP_AUTOSTART") or "").strip().lower() in (
    "1", "true", "yes", "on",
  ):
    return {"ok": True, "skipped": True, "reason": "env:LIVE_SKIP_AUTOSTART"}

  prefs = load_prefs()
  delay = int(delay_sec if delay_sec is not None else (prefs.get("delay_sec") or 45))
  app_port = int(port if port is not None else (prefs.get("port") or 8601))

  try:
    if active:
      return enable_autostart(
        start_mt5=True,
        start_app=True,
        start_bridge=True,
        delay_sec=delay,
        port=app_port,
      )
    return disable_autostart()
  except Exception as exc:
    return {
      "ok": False,
      "skipped": False,
      "reason": "exception",
      "message": str(exc),
    }
