"""Start/stop/status for Linux OOS replay (visible on Live UI)."""
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

from books import bridge_dir, group_models_by_book
from live_config import LIVE_ROOT, RESULTS_DIR
from package_store import load_roster

PID_PATH = RESULTS_DIR / "replay_oos_batch.pid"
LOG_PATH = RESULTS_DIR / "replay_oos_batch.log"
STATE_PATH = RESULTS_DIR / "replay_oos_batch.json"
OOS_PREFS_PATH = RESULTS_DIR / "oos_prefs.json"
# Default: schedule-parity (lab-accurate). Set LIVE_REPLAY_MODE=paper for EA-path smoke.
SCRIPT_PARITY = LIVE_ROOT / "scripts" / "run_parity_oos_batch.py"
SCRIPT_PAPER = LIVE_ROOT / "scripts" / "run_oos_replay_batch.py"
INLINE = LIVE_ROOT / "scripts" / "run_linux_replay_inline.py"
OOS_FROM = "2026-01-01"
OOS_TO = "2026-08-07"


def load_oos_prefs() -> dict[str, str]:
  data = _read(OOS_PREFS_PATH) or {}
  return {
    "from": str(data.get("from") or OOS_FROM)[:10],
    "to": str(data.get("to") or OOS_TO)[:10],
  }


def save_oos_prefs(*, date_from: str, date_to: str) -> dict[str, str]:
  payload = {
    "from": str(date_from)[:10],
    "to": str(date_to)[:10],
    "updated_at": _now(),
  }
  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  OOS_PREFS_PATH.write_text(
    json.dumps(payload, indent=2) + "\n", encoding="utf-8",
  )
  return {"from": payload["from"], "to": payload["to"]}


def _normalize_oos_range(date_from: str, date_to: str) -> tuple[str, str]:
  a = str(date_from or OOS_FROM).strip()[:10]
  b = str(date_to or OOS_TO).strip()[:10]
  if a > b:
    a, b = b, a
  return a, b


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _pid_alive(pid: int | None) -> bool:
  if not pid:
    return False
  try:
    pid_i = int(pid)
  except (TypeError, ValueError):
    return False
  if pid_i <= 0:
    return False
  if os.name == "nt":
    try:
      import ctypes
      from ctypes import wintypes

      PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
      STILL_ACTIVE = 259
      handle = ctypes.windll.kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid_i,
      )
      if not handle:
        return False
      try:
        code = wintypes.DWORD()
        if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) == 0:
          return False
        return int(code.value) == STILL_ACTIVE
      finally:
        ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
      return False
  try:
    os.kill(pid_i, 0)
    return True
  except OSError:
    return False


def _kill_tree(pid: int | None) -> None:
  if not _pid_alive(pid):
    return
  if os.name == "nt":
    try:
      subprocess.run(
        ["taskkill", "/PID", str(int(pid)), "/T", "/F"],
        check=False,
        capture_output=True,
      )
    except Exception:
      pass
    return
  try:
    os.killpg(int(pid), signal.SIGTERM)
  except OSError:
    try:
      os.kill(int(pid), signal.SIGTERM)
    except OSError:
      return
  for _ in range(40):
    if not _pid_alive(pid):
      return
    time.sleep(0.1)
  try:
    os.killpg(int(pid), signal.SIGKILL)
  except OSError:
    try:
      os.kill(int(pid), signal.SIGKILL)
    except OSError:
      pass


def is_replay_running() -> bool:
  pid = None
  if PID_PATH.exists():
    try:
      pid = int(PID_PATH.read_text().strip())
    except ValueError:
      pid = None
  if _pid_alive(pid):
    return True
  if os.name == "nt":
    return False
  try:
    out = subprocess.check_output(
      ["pgrep", "-f", "run_linux_replay_inline.py|run_oos_replay_batch.py|run_parity_oos_batch.py|schedule_parity"],
      text=True,
    )
    return bool(out.strip())
  except Exception:
    return False


def stop_replay() -> dict[str, Any]:
  pid = None
  if PID_PATH.exists():
    try:
      pid = int(PID_PATH.read_text().strip())
    except ValueError:
      pid = None
  _kill_tree(pid)
  if os.name != "nt":
    try:
      subprocess.run(
        ["pkill", "-f", "run_linux_replay_inline.py|run_oos_replay_batch.py|run_parity_oos_batch.py"],
        check=False,
      )
    except Exception:
      pass
  if PID_PATH.exists():
    try:
      PID_PATH.unlink()
    except OSError:
      pass
  return {"stopped": True, "at": _now()}


def start_oos_replay(
  *,
  date_from: str | None = None,
  date_to: str | None = None,
  restart: bool = True,
  mode: str | None = None,
) -> dict[str, Any]:
  prefs = load_oos_prefs()
  date_from, date_to = _normalize_oos_range(
    date_from or prefs["from"],
    date_to or prefs["to"],
  )
  save_oos_prefs(date_from=date_from, date_to=date_to)

  if restart and is_replay_running():
    stop_replay()
    time.sleep(0.5)

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  env = os.environ.copy()
  env["LIVE_REPLAY_FROM"] = date_from
  env["LIVE_REPLAY_TO"] = date_to
  # Windows consoles default to cp1252 — force UTF-8 for batch prints.
  env.setdefault("PYTHONUTF8", "1")
  env.setdefault("PYTHONIOENCODING", "utf-8")
  mode = (mode or env.get("LIVE_REPLAY_MODE") or "parity").strip().lower()
  script = SCRIPT_PAPER if mode in ("paper", "ea", "inline") else SCRIPT_PARITY
  logf = open(LOG_PATH, "a", encoding="utf-8")
  logf.write(f"\n==== UI start {_now()} mode={mode} {date_from}->{date_to} ====\n")
  logf.flush()
  popen_kwargs: dict[str, Any] = {
    "cwd": str(LIVE_ROOT.parent),
    "stdout": logf,
    "stderr": subprocess.STDOUT,
    "env": env,
  }
  if os.name == "nt":
    popen_kwargs["creationflags"] = (
      subprocess.CREATE_NEW_PROCESS_GROUP
      | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    )
  else:
    popen_kwargs["start_new_session"] = True
  proc = subprocess.Popen(
    [sys.executable, "-u", str(script)],
    **popen_kwargs,
  )
  PID_PATH.write_text(str(proc.pid), encoding="utf-8")
  return {
    "started": True,
    "pid": proc.pid,
    "mode": mode,
    "script": str(script),
    "log": str(LOG_PATH),
    "from": date_from,
    "to": date_to,
    "at": _now(),
  }


def load_sim_progress() -> dict[str, Any]:
  """Aggregate sim progress: parity summaries + optional paper sim_control."""
  roster = load_roster()
  enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
  books = []
  parity_batch = _read(RESULTS_DIR / "parity_oos_batch.json") or {}
  parity_by_book = {
    (b.get("symbol"), b.get("timeframe")): b
    for b in (parity_batch.get("books") or [])
  }
  for (sym, tf), rows in group_models_by_book(enabled).items():
    bdir = bridge_dir(sym, tf, sim=True)
    sc = _read(bdir / "sim_control.json") or {}
    bar = _read(bdir / "bar.json") or {}
    status = _read(bdir / "status.json") or {}
    parity = parity_by_book.get((sym, tf)) or _read(
      RESULTS_DIR / f"parity_{sym.lower()}_{tf.lower()}.json"
    ) or {}
    done = int(sc.get("bars_done") or 0)
    total = int(sc.get("bars_total") or 0)
    models = parity.get("models") or []
    tot_r = sum(float(m.get("total_r") or 0) for m in models if m.get("ok"))
    books.append({
      "symbol": sym,
      "timeframe": tf,
      "bridge_dir": str(bdir),
      "mode": "parity" if models else (sc.get("source") or "paper"),
      "ea_status": (
        "completed" if models and parity.get("ok") is not None
        else (sc.get("ea_status") or "idle")
      ),
      "bars_done": done,
      "bars_total": total,
      "pct": (
        100.0 if models
        else (round(100.0 * done / total, 1) if total else 0.0)
      ),
      "last_bar": sc.get("last_bar") or bar.get("bar_time"),
      "n_fills": sc.get("n_fills") or sum(int(m.get("n_trades") or 0) for m in models),
      "n_signals": sc.get("n_signals"),
      "parity_total_r": round(tot_r, 2) if models else None,
      "parity_models": [
        {
          "id": m.get("model_id"),
          "R": m.get("total_r"),
          "lab_R": m.get("lab_total_r"),
          "dR": m.get("delta_r"),
          "err": m.get("error"),
        }
        for m in models
      ],
      "close": bar.get("close"),
      "updated_at": parity.get("updated_at") or sc.get("updated_at") or status.get("updated_at"),
      "n_models": len(rows),
    })
  batch = _read(STATE_PATH) or parity_batch or {}
  prefs = load_oos_prefs()
  last = batch if batch.get("oos_from") else parity_batch
  return {
    "running": is_replay_running(),
    "pid": int(PID_PATH.read_text().strip()) if PID_PATH.exists() and is_replay_running() else None,
    "log": str(LOG_PATH),
    "books": books,
    "batch": batch,
    "oos_from": last.get("oos_from") or prefs["from"],
    "oos_to": last.get("oos_to") or prefs["to"],
  }


def sim_bridge_dirs() -> list[Path]:
  roster = load_roster()
  enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
  dirs: list[Path] = []
  seen = set()
  for (sym, tf), _ in group_models_by_book(enabled).items():
    p = bridge_dir(sym, tf, sim=True)
    if str(p) not in seen:
      dirs.append(p)
      seen.add(str(p))
  return dirs
