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


def is_windows() -> bool:
  return platform.system().lower().startswith("win")


def skip_deploy_requested() -> bool:
  return str(os.environ.get(SKIP_ENV) or "").strip().lower() in (
    "1", "true", "yes", "on",
  )


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
  has_identity = bool(chart.get("symbol") or chart.get("timeframe"))
  sym_ok = (not chart.get("symbol")) or chart.get("symbol") == book["symbol"]
  tf_ok = (not chart.get("timeframe")) or chart.get("timeframe") == book["timeframe"]
  online = bool(has_identity and sym_ok and tf_ok and (age is None or age < stale_after))
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
    cov = roster_ea_coverage(stale_after=stale_after)
    return {
      "ok": True,
      "skipped": True,
      "reason": f"env:{SKIP_ENV}",
      "deployed": False,
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

  cov_before = roster_ea_coverage(stale_after=stale_after)
  need_deploy = force or (not cov_before["all_online"])
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
    "deploy": deploy_result,
    "coverage_before": cov_before,
    "coverage": cov_after,
    "books": books,
  }
