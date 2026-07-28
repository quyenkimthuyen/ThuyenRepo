"""Deploy all four ForgeBridge EAs (M15/H1 × Live/Sim) via PowerShell."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPLOY_ALL = ROOT / "scripts" / "deploy_all_forgebridge.ps1"

# M15 Live / M15 Sim / H1 Live / H1 Sim
ALL_EA_LABELS = (
  "ForgeBridgeM15",
  "ForgeBridgeM15Sim",
  "ForgeBridgeH1",
  "ForgeBridgeH1Sim",
)


def _powershell_exe() -> str | None:
  for name in ("powershell.exe", "pwsh.exe", "pwsh"):
    found = shutil.which(name)
    if found:
      return found
  # Common Windows path even when PATH is thin (e.g. some remote shells)
  for candidate in (
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    r"C:\Program Files\PowerShell\7\pwsh.exe",
  ):
    if Path(candidate).is_file():
      return candidate
  return None


def deploy_all_eas(
  *,
  attach: bool = True,
  enable_trading: bool = True,
  compile_only: bool = False,
  risk_pct: float = 1.0,
  timeout_sec: int = 1200,
) -> dict:
  """Run ``scripts/deploy_all_forgebridge.ps1``.

  Returns ``{ok, returncode, stdout, stderr, cmd}``.
  Requires Windows + XM Global MT5 (MetaEditor compile / chart attach).
  """
  ps = _powershell_exe()
  if not ps:
    return {
      "ok": False,
      "returncode": -1,
      "stdout": "",
      "stderr": (
        "Không tìm thấy PowerShell. Deploy EA cần Windows + XM Global MT5 "
        "(MetaEditor compile / attach chart)."
      ),
      "cmd": [],
    }
  if not DEPLOY_ALL.is_file():
    return {
      "ok": False,
      "returncode": -1,
      "stdout": "",
      "stderr": f"Thiếu script: {DEPLOY_ALL}",
      "cmd": [],
    }

  cmd = [
    ps,
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", str(DEPLOY_ALL),
    "-RiskPct", str(risk_pct),
  ]
  if compile_only:
    cmd.append("-CompileOnly")
  else:
    if attach:
      cmd.append("-Attach")
    if enable_trading:
      cmd.append("-EnableTrading")

  try:
    res = subprocess.run(
      cmd,
      cwd=str(ROOT),
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
      timeout=timeout_sec,
      check=False,
    )
  except subprocess.TimeoutExpired as e:
    out = (e.stdout or "") if isinstance(e.stdout, str) else ""
    err = (e.stderr or "") if isinstance(e.stderr, str) else ""
    return {
      "ok": False,
      "returncode": -1,
      "stdout": out,
      "stderr": err or f"Deploy timeout sau {timeout_sec}s",
      "cmd": cmd,
    }
  except OSError as e:
    return {
      "ok": False,
      "returncode": -1,
      "stdout": "",
      "stderr": f"Không chạy được PowerShell: {e}",
      "cmd": cmd,
    }

  return {
    "ok": res.returncode == 0,
    "returncode": res.returncode,
    "stdout": res.stdout or "",
    "stderr": res.stderr or "",
    "cmd": cmd,
    "host_is_windows": os.name == "nt",
  }
