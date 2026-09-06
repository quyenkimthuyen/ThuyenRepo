"""Windows logon autostart for Live: App desk + XM MT5 + Bridge worker.

Start on Live Trade (or Bridge) registers a per-desk Scheduled Task.
Stop removes it — so a Windows restart while Live was running comes back,
and an intentional Stop does not.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_PREFIX = "TrainApp-Live"
BOOT_DELAY = "PT45S"

_ROOT = Path(__file__).resolve().parents[1]


def current_desk() -> str:
  return (os.environ.get("TRAINAPP_DESK") or "").strip().lower()


def task_name(desk: str | None = None) -> str:
  d = (desk or current_desk() or "desk").strip().lower()
  return f"{TASK_PREFIX}-{d}"


def app_root() -> Path:
  env = (os.environ.get("TRAINAPP_ROOT") or "").strip()
  if env:
    return Path(env).resolve()
  return _ROOT.resolve()


def marker_path(desk: str | None = None) -> Path:
  d = (desk or current_desk() or "desk").strip().lower()
  return app_root() / "runtime" / d / "results" / "live_windows_autostart.json"


def boot_script_path() -> Path:
  return app_root() / "scripts" / "live_windows_boot.ps1"


def launcher_cmd_path(desk: str | None = None) -> Path:
  d = (desk or current_desk() or "desk").strip().lower()
  return app_root() / "runtime" / d / "results" / "live_windows_boot.cmd"


def autostart_is_marked(desk: str | None = None) -> bool:
  return marker_path(desk).is_file()


def _ps_quote(value: str) -> str:
  return "'" + str(value).replace("'", "''") + "'"


def launcher_cmd_text(*, desk: str, python_exe: str) -> str:
  boot = boot_script_path()
  py = python_exe or sys.executable
  return (
    "@echo off\r\n"
    f"powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden "
    f"-File {_cmd_quote(str(boot))} -Desk {desk} -Python {_cmd_quote(py)}\r\n"
  )


def _cmd_quote(path: str) -> str:
  return '"' + path.replace('"', "") + '"'


def write_launcher_cmd(*, desk: str, python_exe: str | None = None) -> Path:
  path = launcher_cmd_path(desk)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
    launcher_cmd_text(desk=desk, python_exe=python_exe or sys.executable),
    encoding="ascii",
    newline="\r\n",
  )
  return path


def _write_marker(desk: str, *, task: str) -> None:
  path = marker_path(desk)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
    json.dumps(
      {
        "desk": desk,
        "task": task,
        "enabled_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
      },
      indent=2,
    )
    + "\n",
    encoding="utf-8",
  )


def _clear_marker(desk: str) -> None:
  path = marker_path(desk)
  try:
    path.unlink(missing_ok=True)
  except OSError:
    pass


def _run_powershell(command: str, *, timeout: int = 40) -> tuple[int, str, str]:
  try:
    proc = subprocess.run(
      [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        command,
      ],
      capture_output=True,
      text=True,
      timeout=timeout,
    )
  except (OSError, subprocess.TimeoutExpired) as exc:
    return 1, "", str(exc)
  return proc.returncode, proc.stdout or "", proc.stderr or ""


def _register_task_ps(*, task: str, cmd_path: Path) -> str:
  tn = _ps_quote(task)
  arg = _ps_quote(f'/c "{cmd_path}"')
  delay = _ps_quote(BOOT_DELAY)
  user = _ps_quote(os.environ.get("USERNAME") or "")
  return f"""
$ErrorActionPreference = 'Stop'
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument {arg}
$trigger = New-ScheduledTaskTrigger -AtLogOn -User {user}
$trigger.Delay = {delay}
$principal = New-ScheduledTaskPrincipal -UserId {user} -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName {tn} -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Output 'OK'
"""


def _unregister_task_ps(*, task: str) -> str:
  tn = _ps_quote(task)
  return f"""
$ErrorActionPreference = 'SilentlyContinue'
Unregister-ScheduledTask -TaskName {tn} -Confirm:$false | Out-Null
& schtasks.exe /Delete /TN {tn} /F 2>$null | Out-Null
Write-Output 'OK'
exit 0
"""


def enable_live_autostart(desk: str | None = None) -> tuple[bool, str]:
  """Register logon task: start XM MT5 + this desk app + Live worker."""
  d = (desk or current_desk()).strip().lower()
  if not d:
    return False, "Không rõ desk — không đăng ký auto-start Windows."
  if sys.platform != "win32":
    return False, "Auto-start Windows chỉ chạy trên Windows."
  if not boot_script_path().is_file():
    return False, f"Thiếu script boot: {boot_script_path()}"
  cmd_path = write_launcher_cmd(desk=d, python_exe=sys.executable)
  name = task_name(d)
  code, out, err = _run_powershell(_register_task_ps(task=name, cmd_path=cmd_path))
  if code != 0 or "OK" not in (out or ""):
    tr = f'cmd.exe /c "{cmd_path}"'
    try:
      proc = subprocess.run(
        [
          "schtasks.exe", "/Create", "/TN", name, "/SC", "ONLOGON",
          "/RL", "LIMITED", "/F", "/DELAY", "0000:45", "/TR", tr,
        ],
        capture_output=True,
        text=True,
        timeout=40,
      )
    except (OSError, subprocess.TimeoutExpired) as exc:
      detail = (err or out or str(exc)).strip()
      return False, f"Không đăng ký auto-start Windows: {detail[:400]}"
    if proc.returncode != 0:
      detail = (proc.stderr or proc.stdout or err or out or "schtasks failed").strip()
      return False, f"Không đăng ký auto-start Windows: {detail[:400]}"
  _write_marker(d, task=name)
  return True, name


def disable_live_autostart(desk: str | None = None) -> tuple[bool, str]:
  """Remove logon task and marker so Windows restart does not resume Live."""
  d = (desk or current_desk()).strip().lower()
  if not d:
    return True, "no-desk"
  _clear_marker(d)
  if sys.platform != "win32":
    return True, "not-windows"
  name = task_name(d)
  code, out, err = _run_powershell(_unregister_task_ps(task=name))
  if code != 0 and "OK" not in (out or ""):
    detail = (err or out or "Unregister failed").strip()
    return False, f"Không gỡ auto-start Windows: {detail[:400]}"
  try:
    launcher_cmd_path(d).unlink(missing_ok=True)
  except OSError:
    pass
  return True, name
