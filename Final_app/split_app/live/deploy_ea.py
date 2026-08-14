"""Auto-deploy ForgeBridgeLive EAs on Windows for enabled roster books.

Linux / non-Windows: no-op (Simulate does not need MT5 EA).
Called from ``bridge_control.start_bridge`` when ``sim=False``.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from books import bridge_dir, bridge_subdir, group_models_by_book
from chart_validate import read_chart_identity
from live_config import LIVE_ROOT
from package_store import load_roster
from runtime_host import normalize_symbol, normalize_timeframe

DEPLOY_SCRIPT = LIVE_ROOT / "scripts" / "deploy_live_ea.ps1"
SKIP_ENV = "LIVE_SKIP_EA_DEPLOY"
DEFAULT_XM_INSTALL = Path(r"C:\Program Files\XM Global MT5")

# Cache MT5 checks — Live desk calls this on every Streamlit rerun.
_MT5_CACHE: dict[str, Any] = {"at": 0.0, "paths": [], "running": None}
_MT5_CACHE_TTL_SEC = 2.5


def is_windows() -> bool:
  return platform.system().lower().startswith("win")


def _subprocess_kwargs() -> dict[str, Any]:
  """Hide console windows for Win32 subprocess helpers."""
  kw: dict[str, Any] = {}
  if is_windows():
    kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
  return kw


def skip_deploy_requested() -> bool:
  return str(os.environ.get(SKIP_ENV) or "").strip().lower() in (
    "1", "true", "yes", "on",
  )


def _terminal64_paths_via_ctypes() -> list[str]:
  """List executable paths for running terminal64.exe — no console flash."""
  if not is_windows():
    return []
  try:
    import ctypes
    from ctypes import wintypes
  except Exception:
    return []

  TH32CS_SNAPPROCESS = 0x00000002
  PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
  INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

  class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
      ("dwSize", wintypes.DWORD),
      ("cntUsage", wintypes.DWORD),
      ("th32ProcessID", wintypes.DWORD),
      ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
      ("th32ModuleID", wintypes.DWORD),
      ("cntThreads", wintypes.DWORD),
      ("th32ParentProcessID", wintypes.DWORD),
      ("pcPriClassBase", ctypes.c_long),
      ("dwFlags", wintypes.DWORD),
      ("szExeFile", wintypes.WCHAR * 260),
    ]

  kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
  CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
  CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
  CreateToolhelp32Snapshot.restype = wintypes.HANDLE
  Process32FirstW = kernel32.Process32FirstW
  Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
  Process32FirstW.restype = wintypes.BOOL
  Process32NextW = kernel32.Process32NextW
  Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
  Process32NextW.restype = wintypes.BOOL
  OpenProcess = kernel32.OpenProcess
  OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
  OpenProcess.restype = wintypes.HANDLE
  CloseHandle = kernel32.CloseHandle
  CloseHandle.argtypes = [wintypes.HANDLE]
  CloseHandle.restype = wintypes.BOOL
  QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
  QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
  ]
  QueryFullProcessImageNameW.restype = wintypes.BOOL

  snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
  if not snap or snap == INVALID_HANDLE_VALUE:
    return []

  out: list[str] = []
  try:
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    if not Process32FirstW(snap, ctypes.byref(entry)):
      return []
    while True:
      name = (entry.szExeFile or "").lower()
      if name == "terminal64.exe":
        path = "unknown"
        h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, entry.th32ProcessID)
        if h:
          try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buf))
            if QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
              path = buf.value or "unknown"
          finally:
            CloseHandle(h)
        out.append(path)
      if not Process32NextW(snap, ctypes.byref(entry)):
        break
  finally:
    CloseHandle(snap)
  return out


def _terminal64_paths() -> list[str]:
  """Return Path strings for running terminal64.exe (cached; no console flash)."""
  if not is_windows():
    return []
  now = time.time()
  if now - float(_MT5_CACHE.get("at") or 0.0) < _MT5_CACHE_TTL_SEC:
    return list(_MT5_CACHE.get("paths") or [])

  paths = _terminal64_paths_via_ctypes()
  if not paths:
    # Rare fallback — still hide the console window.
    try:
      res = subprocess.run(
        [
          "powershell.exe", "-NoProfile", "-Command",
          "Get-Process -Name 'terminal64' -ErrorAction SilentlyContinue | "
          "ForEach-Object { if ($_.Path) { $_.Path } else { 'unknown' } }",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
        **_subprocess_kwargs(),
      )
      paths = [ln.strip() for ln in (res.stdout or "").splitlines() if ln.strip()]
    except Exception:
      paths = []

  _MT5_CACHE["at"] = now
  _MT5_CACHE["paths"] = list(paths)
  _MT5_CACHE["running"] = None
  return paths


def find_xm_install_path() -> Path | None:
  """Locate XM Global MT5 install folder (running process or default path)."""
  if not is_windows():
    return None
  for p in _terminal64_paths():
    pl = p.lower()
    if "xm global mt5" in pl and pl.endswith("terminal64.exe"):
      return Path(p).resolve().parent
  for candidate in (
    DEFAULT_XM_INSTALL,
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "XM Global MT5",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "XM Global MT5",
  ):
    if (candidate / "terminal64.exe").is_file():
      return candidate
  return None


def is_mt5_running(*, install_path: Path | None = None) -> bool:
  """True if XM Global MT5 terminal64 is running (no console popup)."""
  if not is_windows():
    return False
  now = time.time()
  if (
    _MT5_CACHE.get("running") is not None
    and now - float(_MT5_CACHE.get("at") or 0.0) < _MT5_CACHE_TTL_SEC
    and install_path is None
  ):
    return bool(_MT5_CACHE["running"])

  paths = _terminal64_paths()
  if not paths:
    _MT5_CACHE["running"] = False
    return False
  install = install_path or find_xm_install_path()
  install_s = str(install).lower() if install else ""
  running = False
  for p in paths:
    pl = p.lower()
    if "xm global mt5" in pl:
      running = True
      break
    if install_s and install_s in pl:
      running = True
      break
  if (
    not running
    and any(p == "unknown" for p in paths)
    and install_s
    and "xm global mt5" in install_s
  ):
    running = True
  _MT5_CACHE["running"] = running
  return running


def ensure_mt5_running(*, wait_sec: float = 10.0) -> dict[str, Any]:
  """Start XM Global MT5 terminal if it is not already running."""
  if not is_windows():
    return {"ok": True, "skipped": True, "reason": "not_windows", "started": False, "running": False}
  if is_mt5_running():
    return {
      "ok": True,
      "skipped": False,
      "reason": "already_running",
      "started": False,
      "running": True,
      "install": str(find_xm_install_path() or ""),
    }
  install = find_xm_install_path()
  if install is None:
    return {
      "ok": False,
      "skipped": False,
      "reason": "mt5_install_not_found",
      "started": False,
      "running": False,
      "error": "XM Global MT5 not found (expected under Program Files).",
    }
  exe = install / "terminal64.exe"
  if not exe.is_file():
    return {
      "ok": False,
      "skipped": False,
      "reason": "terminal64_missing",
      "started": False,
      "running": False,
      "error": f"Missing {exe}",
    }
  try:
    # Launch GUI terminal directly (do NOT use CREATE_NO_WINDOW — that can suppress UI).
    subprocess.Popen([str(exe)], cwd=str(install), close_fds=True)
  except Exception as exc:
    return {
      "ok": False,
      "skipped": False,
      "reason": "start_failed",
      "started": False,
      "running": False,
      "error": str(exc),
      "install": str(install),
    }
  # Invalidate cache so wait loop re-checks.
  _MT5_CACHE["at"] = 0.0
  _MT5_CACHE["running"] = None
  deadline = time.time() + max(2.0, float(wait_sec))
  while time.time() < deadline:
    if is_mt5_running(install_path=install):
      return {
        "ok": True,
        "skipped": False,
        "reason": None,
        "started": True,
        "running": True,
        "install": str(install),
      }
    time.sleep(0.5)
  # Process may still be booting UI — treat as started if Start-Process succeeded.
  return {
    "ok": True,
    "skipped": False,
    "reason": "started_waiting",
    "started": True,
    "running": is_mt5_running(install_path=install),
    "install": str(install),
  }


def enabled_books() -> list[dict[str, Any]]:
  """Unique enabled (symbol, timeframe) books with magic/risk hints."""
  roster = load_roster()
  enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
  out: list[dict[str, Any]] = []
  for (sym, tf), rows in group_models_by_book(enabled).items():
    sym_n = normalize_symbol(sym)
    tf_n = normalize_timeframe(tf)
    magic = None
    risk = 1.0
    for r in rows:
      if r.get("magic") is not None:
        try:
          magic = int(r["magic"])
        except (TypeError, ValueError):
          pass
      try:
        risk = float(r.get("risk_pct") or risk)
      except (TypeError, ValueError):
        pass
      if magic is not None:
        break
    out.append({
      "symbol": sym_n,
      "timeframe": tf_n,
      "bridge_subdir": bridge_subdir(sym_n, tf_n, sim=False),
      "bridge_dir": str(bridge_dir(sym_n, tf_n, sim=False)),
      "magic": magic,
      "risk_pct": risk,
      "model_ids": [str(r.get("model_id") or "") for r in rows],
      "n_models": len(rows),
    })
  return out


def _parse_ts(raw: Any) -> datetime | None:
  if raw is None:
    return None
  if isinstance(raw, datetime):
    return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
  s = str(raw).strip()
  if not s:
    return None
  try:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))
  except ValueError:
    return None


def _age_seconds(ts: datetime | None) -> float | None:
  if ts is None:
    return None
  now = datetime.now(timezone.utc)
  if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc)
  return max(0.0, (now - ts.astimezone(timezone.utc)).total_seconds())


def book_ea_status(book: dict[str, Any], *, stale_after: float = 180.0) -> dict[str, Any]:
  bdir = Path(book["bridge_dir"])
  chart = read_chart_identity(bdir)
  conn = {}
  try:
    p = bdir / "connection.json"
    if p.exists():
      conn = json.loads(p.read_text(encoding="utf-8")) or {}
  except (OSError, json.JSONDecodeError):
    conn = {}
  bar = {}
  try:
    p = bdir / "bar.json"
    if p.exists():
      bar = json.loads(p.read_text(encoding="utf-8")) or {}
  except (OSError, json.JSONDecodeError):
    bar = {}
  ts = _parse_ts(
    conn.get("updated_at")
    or conn.get("ts")
    or bar.get("time")
    or bar.get("bar_time")
    or bar.get("updated_at")
  )
  age = _age_seconds(ts)
  if age is None:
    # Fall back to file mtime — missing timestamps used to mark books "online" forever.
    for candidate in (bdir / "connection.json", bdir / "bar.json"):
      try:
        if candidate.exists():
          age = max(0.0, time.time() - candidate.stat().st_mtime)
          break
      except OSError:
        pass
  has_identity = bool(chart.get("symbol") or chart.get("timeframe"))
  sym_ok = (not chart.get("symbol")) or chart.get("symbol") == book["symbol"]
  tf_ok = (not chart.get("timeframe")) or chart.get("timeframe") == book["timeframe"]
  online = bool(has_identity and sym_ok and tf_ok and age is not None and age < stale_after)
  return {
    **book,
    "online": online,
    "age_sec": age,
    "chart": chart,
    "connected": bool(conn.get("connected", True)) if conn else False,
  }


def roster_ea_coverage(*, stale_after: float = 180.0) -> dict[str, Any]:
  books = enabled_books()
  statuses = [book_ea_status(b, stale_after=stale_after) for b in books]
  missing = [s for s in statuses if not s.get("online")]
  return {
    "books": statuses,
    "n_books": len(statuses),
    "n_online": len(statuses) - len(missing),
    "all_online": bool(statuses) and not missing,
    "missing": missing,
  }


def run_deploy_live_from_roster(
  *,
  timeout_sec: float = 240.0,
  enable_trading: bool = True,
) -> dict[str, Any]:
  """Invoke deploy_live_ea.ps1 -FromRoster (all enabled books, one MT5 restart)."""
  if not is_windows():
    return {
      "ok": True,
      "skipped": True,
      "reason": "not_windows",
      "stdout": "",
      "stderr": "",
      "code": 0,
    }
  if not DEPLOY_SCRIPT.is_file():
    return {
      "ok": False,
      "skipped": False,
      "reason": f"missing_script:{DEPLOY_SCRIPT}",
      "stdout": "",
      "stderr": f"Deploy script not found: {DEPLOY_SCRIPT}",
      "code": 2,
    }

  cmd = [
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", str(DEPLOY_SCRIPT),
    "-Mode", "Live",
    "-FromRoster",
    "-SkipBridgeService",
    "-Attach",
  ]
  if enable_trading:
    cmd.append("-EnableTrading")
  else:
    cmd.append("-NoEnableTrading")

  try:
    res = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      check=False,
      cwd=str(LIVE_ROOT),
      timeout=max(60.0, float(timeout_sec)),
      env={**os.environ, SKIP_ENV: "1"},
      **_subprocess_kwargs(),
    )
  except subprocess.TimeoutExpired as e:
    out = e.stdout if isinstance(e.stdout, str) else (
      (e.stdout or b"").decode("utf-8", errors="replace") if e.stdout else ""
    )
    err = e.stderr if isinstance(e.stderr, str) else (
      (e.stderr or b"").decode("utf-8", errors="replace") if e.stderr else ""
    )
    return {
      "ok": False,
      "skipped": False,
      "reason": "timeout",
      "stdout": out or "",
      "stderr": (err + f"\nDeploy timeout after {timeout_sec:.0f}s").strip(),
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

  ok = res.returncode == 0
  return {
    "ok": ok,
    "skipped": False,
    "reason": None if ok else f"exit_{res.returncode}",
    "stdout": res.stdout or "",
    "stderr": res.stderr or "",
    "code": int(res.returncode),
  }


def wait_books_online(
  *,
  wait_sec: float = 60.0,
  poll_sec: float = 2.0,
  stale_after: float = 180.0,
) -> dict[str, Any]:
  deadline = time.time() + float(wait_sec)
  last = roster_ea_coverage(stale_after=stale_after)
  while time.time() < deadline:
    last = roster_ea_coverage(stale_after=stale_after)
    if last["all_online"]:
      return {**last, "waited": True, "timed_out": False}
    time.sleep(max(0.5, float(poll_sec)))
  return {**last, "waited": True, "timed_out": True}


def ensure_live_eas_deployed(
  *,
  force: bool = False,
  wait_online: bool = True,
  wait_sec: float = 60.0,
  deploy_timeout_sec: float = 240.0,
  stale_after: float = 180.0,
) -> dict[str, Any]:
  """Check enabled books; deploy all missing (or force) on Windows.

  Returns a status dict. Raises RuntimeError only when Windows deploy fails
  hard; soft skip on Linux.
  """
  books = enabled_books()
  if not books:
    return {
      "ok": False,
      "skipped": True,
      "reason": "no_enabled_books",
      "deployed": False,
      "coverage": {"n_books": 0, "all_online": False, "books": []},
    }

  if skip_deploy_requested():
    mt5 = ensure_mt5_running() if is_windows() else {"skipped": True}
    cov = roster_ea_coverage(stale_after=stale_after)
    return {
      "ok": True,
      "skipped": True,
      "reason": f"env:{SKIP_ENV}",
      "deployed": False,
      "mt5": mt5,
      "coverage": cov,
      "books": books,
    }

  if not is_windows():
    cov = roster_ea_coverage(stale_after=stale_after)
    return {
      "ok": True,
      "skipped": True,
      "reason": "not_windows",
      "deployed": False,
      "coverage": cov,
      "books": books,
    }

  mt5 = ensure_mt5_running(wait_sec=8.0)
  if not mt5.get("ok"):
    raise RuntimeError(
      "Không khởi động được XM Global MT5.\n"
      f"reason={mt5.get('reason')} {mt5.get('error') or ''}\n"
      "Cài XM MT5 hoặc mở terminal64.exe thủ công rồi Start lại."
    )

  cov_before = roster_ea_coverage(stale_after=stale_after)
  # Fresh MT5 boot (or terminal was down) must re-attach even if stale files look "online".
  mt5_was_down = bool(mt5.get("started"))
  need_deploy = force or mt5_was_down or (not cov_before["all_online"])
  deploy_result = None
  if need_deploy:
    deploy_result = run_deploy_live_from_roster(
      timeout_sec=deploy_timeout_sec,
      enable_trading=True,
    )
    if not deploy_result.get("ok"):
      detail = (deploy_result.get("stderr") or deploy_result.get("stdout") or "").strip()
      raise RuntimeError(
        "Auto-deploy EA thất bại — không Start được Live.\n"
        f"reason={deploy_result.get('reason')} code={deploy_result.get('code')}\n"
        f"{detail[:2000]}"
      )

  cov_after = cov_before
  if wait_online:
    cov_after = wait_books_online(wait_sec=wait_sec, stale_after=stale_after)
    if need_deploy and not cov_after.get("all_online"):
      missing = ", ".join(
        f"{m['symbol']} {m['timeframe']}" for m in (cov_after.get("missing") or [])
      ) or "—"
      raise RuntimeError(
        "Deploy xong nhưng chưa thấy EA heartbeat đủ mọi book.\n"
        f"Missing: {missing}\n"
        "Mở MT5, bật AutoTrading, kiểm tra chart đã gắn ForgeBridgeLive."
      )

  return {
    "ok": True,
    "skipped": False,
    "reason": None if need_deploy else "already_online",
    "deployed": bool(need_deploy),
    "mt5": mt5,
    "deploy": deploy_result,
    "coverage_before": cov_before,
    "coverage": cov_after,
    "books": books,
  }
