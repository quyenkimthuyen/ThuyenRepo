"""Windows logon autostart for Live: App desk + XM MT5 + Bridge worker.

Start on Live Trade (or Bridge) registers a per-desk Scheduled Task.
Stop removes it — so a Windows restart while Live was running comes back,
and an intentional Stop does not.

Task names are unique per clone folder so copying Train to another directory
does not steal another copy's task. The ``.cmd`` launcher uses ``%~dp0`` so
the file itself stays valid after a copy; Scheduled Task still stores an
absolute path and is rebound by ``ensure_live_autostart_after_move``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_PREFIX = "TrainApp-Live"
BOOT_DELAY = "PT45S"
_PATH_IN_ARGS = re.compile(r'"([^"]+)"')

_ROOT = Path(__file__).resolve().parents[1]


def current_desk() -> str:
  return (os.environ.get("TRAINAPP_DESK") or "").strip().lower()


def _sanitize_token(name: str) -> str:
  out = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in (name or "").strip())
  return (out or "app")[:40]


def clone_root() -> Path:
  """App clone root: ``<clone>/Train`` → ``<clone>``."""
  return app_root().resolve().parent


def clone_task_suffix(root: Path | None = None) -> str:
  resolved = (root or clone_root()).resolve()
  folder = _sanitize_token(resolved.name)
  norm = str(resolved).replace("\\", "/").lower()
  digest = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:8]
  return f"{folder}-{digest}"


def task_name(desk: str | None = None) -> str:
  d = (desk or current_desk() or "desk").strip().lower()
  return f"{TASK_PREFIX}-{clone_task_suffix()}-{d}"


def legacy_task_name(desk: str | None = None) -> str:
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


def launcher_cmd_text(*, desk: str, python_exe: str = "") -> str:
  """Portable launcher: resolve Train root from this file's directory.

  Lives at ``Train/runtime/<desk>/results/live_windows_boot.cmd`` so
  ``%~dp0..\\..\\..`` is Train root. Python is resolved at boot time.
  """
  d = (desk or "desk").strip().lower()
  _ = python_exe  # kept for call-site compatibility; boot script finds python
  return (
    "@echo off\r\n"
    "setlocal\r\n"
    "rem Paths are relative to this file (Train\\runtime\\<desk>\\results)\r\n"
    "set \"APP_ROOT=%~dp0..\\..\\..\"\r\n"
    "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden "
    f"-File \"%APP_ROOT%\\scripts\\live_windows_boot.ps1\" -Desk {d}\r\n"
  )


def write_launcher_cmd(*, desk: str, python_exe: str | None = None) -> Path:
  path = launcher_cmd_path(desk)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
    launcher_cmd_text(desk=desk, python_exe=python_exe or ""),
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
        "clone": clone_task_suffix(),
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
  wd = _ps_quote(str(cmd_path.parent))
  return f"""
$ErrorActionPreference = 'Stop'
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument {arg} -WorkingDirectory {wd}
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


def _task_arguments(task: str) -> str:
  if sys.platform != "win32":
    return ""
  tn = _ps_quote(task)
  code, out, _err = _run_powershell(
    f"""
$t = Get-ScheduledTask -TaskName {tn} -ErrorAction SilentlyContinue
if (-not $t) {{ Write-Output ''; exit 0 }}
Write-Output ((($t.Actions | ForEach-Object {{ $_.Arguments }}) -join ' '))
"""
  )
  if code != 0:
    return ""
  return (out or "").strip()


def _args_point_at(args: str, path: Path) -> bool:
  if not args:
    return False
  needle = str(path.resolve()).lower().replace("/", "\\")
  return needle in args.lower().replace("/", "\\")


def _drop_stale_task(task: str, *, ours: Path) -> None:
  """Unregister a leftover task only if it belongs to this copy or is orphaned."""
  if sys.platform != "win32" or not task:
    return
  args = _task_arguments(task)
  if not args:
    return
  if _args_point_at(args, ours):
    _run_powershell(_unregister_task_ps(task=task))
    return
  for match in _PATH_IN_ARGS.finditer(args):
    p = Path(match.group(1))
    if p.suffix.lower() in {".cmd", ".ps1"} and not p.exists():
      _run_powershell(_unregister_task_ps(task=task))
      return


def enable_live_autostart(desk: str | None = None) -> tuple[bool, str]:
  """Register logon task: start XM MT5 + this desk app + Live worker."""
  d = (desk or current_desk()).strip().lower()
  if not d:
    return False, "Không rõ desk — không đăng ký auto-start Windows."
  if sys.platform != "win32":
    write_launcher_cmd(desk=d)
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
  _drop_stale_task(legacy_task_name(d), ours=app_root())
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
  _drop_stale_task(legacy_task_name(d), ours=app_root())
  if code != 0 and "OK" not in (out or ""):
    detail = (err or out or "Unregister failed").strip()
    return False, f"Không gỡ auto-start Windows: {detail[:400]}"
  try:
    launcher_cmd_path(d).unlink(missing_ok=True)
  except OSError:
    pass
  return True, name


def _desk_ids_with_artifacts() -> list[str]:
  runtime = app_root() / "runtime"
  if not runtime.is_dir():
    d = current_desk()
    return [d] if d else []
  found: list[str] = []
  for child in sorted(runtime.iterdir()):
    if not child.is_dir():
      continue
    d = child.name.strip().lower()
    if autostart_is_marked(d) or launcher_cmd_path(d).is_file():
      found.append(d)
  return found


def ensure_live_autostart_after_move(desk: str | None = None) -> dict[str, str | bool]:
  """Rewrite portable ``.cmd`` launchers and rebind tasks after a folder copy.

  Always rewrites existing launchers (or marked desks). On Windows, re-registers
  the per-clone task when a marker says autostart should still be on.
  """
  desks = [desk.strip().lower()] if (desk or "").strip() else _desk_ids_with_artifacts()
  last_name = ""
  rebound = False
  for d in desks:
    if not d:
      continue
    if autostart_is_marked(d) or launcher_cmd_path(d).is_file():
      write_launcher_cmd(desk=d)
    if sys.platform != "win32" or not autostart_is_marked(d):
      continue
    if not boot_script_path().is_file():
      continue
    cmd_path = launcher_cmd_path(d)
    name = task_name(d)
    last_name = name
    args = _task_arguments(name)
    if _args_point_at(args, cmd_path):
      continue
    ok, last_name = enable_live_autostart(d)
    rebound = rebound or bool(ok)
  return {
    "ok": True,
    "rebound": rebound,
    "task_name": last_name,
    "windows": sys.platform == "win32",
  }
