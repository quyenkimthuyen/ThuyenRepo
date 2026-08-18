"""Start/stop Live bridge workers — one worker per chart book (symbol+TF).

Users enable models; this module routes each (symbol,TF) group to its own
bridge dir + remine process. Mixed TF/symbol models run independently.
"""
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

from books import bridge_dir, bridge_subdir, group_models_by_book
from chart_validate import validate_chart_vs_roster
from live_config import BRIDGE_DIR, LIVE_ROOT, RESULTS_DIR
from materialize_models import materialize_enabled
from package_store import load_roster, save_roster
from runtime_host import normalize_symbol, normalize_timeframe
from safety import default_loss_guard_from_roster, is_kill_switch_armed
from sync_bridge_roster import write_models_json
from magic_allocator import assign_magics
from shared.constants import LIVE_BRIDGE_PORT, LIVE_MAGIC_BASE, LIVE_SIM_PORT

CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
WORKERS_PATH = RESULTS_DIR / "live_workers.json"
SIM_WORKERS_PATH = RESULTS_DIR / "sim_workers.json"
WORKERS_DIR = RESULTS_DIR / "workers"
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
  tmp = path.with_name(f"{path.stem}.{os.getpid()}.{time.time_ns()}.tmp")
  payload = json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
  last_exc: OSError | None = None
  for attempt in range(8):
    try:
      tmp.write_text(payload, encoding="utf-8")
      tmp.replace(path)
      return
    except OSError as exc:
      last_exc = exc
      if getattr(exc, "winerror", None) != 32 and getattr(exc, "errno", None) not in (11, 16):
        try:
          tmp.unlink(missing_ok=True)
        except OSError:
          pass
        raise
      time.sleep(0.05 * (attempt + 1))
  try:
    tmp.unlink(missing_ok=True)
  except OSError:
    pass
  if last_exc:
    raise last_exc
  raise OSError(f"cannot write {path}")


def _pid_alive(pid: int | None) -> bool:
  """Return True if process exists and has not exited.

  On Windows prefer OpenProcess/GetExitCodeProcess — more reliable than os.kill
  for workers started with CREATE_NEW_PROCESS_GROUP.
  """
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
      pass

  try:
    os.kill(pid_i, 0)
    return True
  except OSError:
    return False
  except ValueError:
    return False


def _worker_log_tail_since_start(log_path: Path, *, max_lines: int = 20) -> str:
  if not log_path.is_file():
    return ""
  try:
    text = log_path.read_text(encoding="utf-8", errors="replace")
  except OSError:
    return ""
  idx = text.rfind("--- start ")
  chunk = text[idx:] if idx >= 0 else text
  lines = chunk.splitlines()
  return "\n".join(lines[-max_lines:])


def _worker_looks_crashed(log_path: Path) -> bool:
  """True only when the latest start block ends with a hard failure."""
  tail = _worker_log_tail_since_start(log_path, max_lines=40).lower()
  if not tail.strip():
    return False
  fatal = (
    "traceback (most recent call last):",
    "permissionerror:",
    "modulenotfounderror:",
    "systemexit",
  )
  # Progress lines mean the worker got past bootstrap — not an immediate exit.
  progress = (
    "[live-bridge] history bars=",
    "[live-bridge] waiting for history",
    "[bridge] remine week=",
    "[bridge] schedule week=",
    "monitor=http://",
  )
  if any(p in tail for p in progress):
    return False
  return any(f in tail for f in fatal)


def _worker_status_active(bridge_dir: str | Path | None) -> bool:
  if not bridge_dir:
    return False
  try:
    data = _read(Path(bridge_dir) / "status.json") or {}
  except Exception:
    return False
  state = str(data.get("state") or "").lower()
  return state in {
    "starting", "running", "syncing_history", "waiting_history",
    "ready", "idle", "decision",
  }


def load_config() -> dict:
  return _read(CONFIG_PATH) or {}


def save_config(**updates) -> dict:
  cfg = load_config()
  cfg.update(updates)
  cfg["updated_at"] = _now()
  _write(CONFIG_PATH, cfg)
  return cfg


def _workers_path(*, sim: bool = False) -> Path:
  return SIM_WORKERS_PATH if sim else WORKERS_PATH


def load_workers(*, sim: bool = False) -> dict:
  data = _read(_workers_path(sim=sim))
  if not data:
    return {"updated_at": None, "workers": []}
  return data


def save_workers(workers: list[dict], *, sim: bool = False) -> dict:
  payload = {"updated_at": _now(), "workers": workers}
  _write(_workers_path(sim=sim), payload)
  return payload


def _kill_pid(pid: int | None) -> None:
  if not _pid_alive(pid):
    return
  try:
    os.kill(int(pid), signal.SIGTERM)
  except OSError:
    pass
  for _ in range(40):
    if not _pid_alive(pid):
      return
    time.sleep(0.1)
  try:
    os.kill(int(pid), signal.SIGKILL)
  except OSError:
    pass


def is_running(*, sim: bool = False) -> bool:
  return any(_pid_alive(w.get("pid")) for w in load_workers(sim=sim).get("workers") or [])


def service_pid(*, sim: bool = False) -> int | None:
  """Primary worker pid (compat)."""
  for w in load_workers(sim=sim).get("workers") or []:
    if _pid_alive(w.get("pid")):
      return int(w["pid"])
  if sim:
    return None
  # legacy single pid
  cfg = load_config()
  pid = cfg.get("service_pid")
  return int(pid) if _pid_alive(pid) else None


def prepare_runtime(
  *,
  require_chart: bool = False,
  poll_sec: float = 0.5,
  sim: bool = False,
) -> dict[str, Any]:
  if is_kill_switch_armed():
    raise RuntimeError("Kill-switch armed — disarm before Start")

  roster = load_roster()
  models = assign_magics(roster.get("models") or [], sim=False)
  save_roster(models, active_book=roster.get("active_book"))
  sim_models = assign_magics(models, sim=True)

  enabled = [r for r in models if r.get("enabled")]
  if not enabled:
    raise RuntimeError("No models On — enable at least one model")

  mat = materialize_enabled(roster={"models": models})
  groups = mat.get("groups") or []

  from live_config import BRIDGE_SIM_DIR
  from shared.constants import LIVE_SIM_MAGIC_BASE
  from books import bridge_dir as bdir_fn

  validations = []
  prepared_groups = []
  sim_by_book = {
    (normalize_symbol(r.get("symbol")), normalize_timeframe(r.get("timeframe"))): []
    for r in sim_models
    if r.get("enabled")
  }
  for r in sim_models:
    if not r.get("enabled"):
      continue
    key = (normalize_symbol(r.get("symbol")), normalize_timeframe(r.get("timeframe")))
    sim_by_book.setdefault(key, []).append(r)

  for i, g in enumerate(groups):
    sym, tf = g["symbol"], g["timeframe"]
    bdir = bdir_fn(sym, tf, sim=bool(sim))
    live_bdir = bdir_fn(sym, tf, sim=False)
    sim_bdir = bdir_fn(sym, tf, sim=True)
    write_models_json(live_bdir, g["rows"], base_magic=LIVE_MAGIC_BASE)
    write_models_json(sim_bdir, sim_by_book.get((sym, tf), []), base_magic=LIVE_SIM_MAGIC_BASE)
    if i == 0:
      write_models_json(BRIDGE_DIR, g["rows"], base_magic=LIVE_MAGIC_BASE)
      write_models_json(BRIDGE_SIM_DIR, sim_by_book.get((sym, tf), []), base_magic=LIVE_SIM_MAGIC_BASE)

    check = {"ok": True, "errors": [], "warnings": []}
    if not sim:
      check = validate_chart_vs_roster(
        bridge_dir=live_bdir,
        roster_rows=g["rows"],
        require_ea_online=require_chart,
      )
      if not check["ok"] and i == 0:
        check_legacy = validate_chart_vs_roster(
          bridge_dir=BRIDGE_DIR,
          roster_rows=g["rows"],
          require_ea_online=require_chart,
        )
        if check_legacy["ok"] or (not require_chart and not check_legacy["errors"]):
          check = check_legacy

    validations.append({"symbol": sym, "timeframe": tf, **check})
    if require_chart and not check["ok"] and not sim:
      prepared_groups.append({**g, "bridge_dir": str(bdir), "skip": True, "skip_reason": check["errors"]})
    else:
      prepared_groups.append({**g, "bridge_dir": str(bdir), "skip": False, "sim": bool(sim)})

  runnable = [g for g in prepared_groups if not g.get("skip")]
  if not runnable:
    errs = []
    for v in validations:
      errs.extend(v.get("errors") or [])
    raise RuntimeError("No model group ready: " + ("; ".join(errs) or "chart mismatch"))

  guard = default_loss_guard_from_roster()
  try:
    from risk_prefs import load_risk_prefs
    prefs = load_risk_prefs()
    guard.update(prefs)
  except Exception:
    pass
  # Never auto-clear a live trip on prepare; Start path clears via explicit UI
  existing = load_config()
  if existing.get("loss_guard_tripped"):
    guard["loss_guard_tripped"] = True
    guard["loss_guard_tripped_at"] = existing.get("loss_guard_tripped_at")
    guard["loss_guard_tripped_reason"] = existing.get("loss_guard_tripped_reason")
  else:
    guard["loss_guard_tripped"] = False
    guard["loss_guard_tripped_at"] = None
    guard["loss_guard_tripped_reason"] = None
  guard["loss_guard_halted_models"] = [
    str(x) for x in (existing.get("loss_guard_halted_models") or []) if x
  ]

  primary_risk = float(enabled[0].get("risk_pct") or 1.0)
  port = LIVE_SIM_PORT if sim else LIVE_BRIDGE_PORT
  cfg_payload = {
    "enabled": False,
    "mode": "process",
    "poll_sec": float(poll_sec),
    "model_ids": mat["model_ids"],
    "risk_pct": primary_risk,
    "monitor_port": port,
    "sim": bool(sim),
    **guard,
    "last_error": None,
  }
  if sim:
    # Never write sim flags / trip state into the Live config file.
    cfg_payload["loss_guard_tripped"] = False
    cfg_payload["loss_guard_tripped_at"] = None
    cfg_payload["loss_guard_tripped_reason"] = None
    cfg_payload["loss_guard_halted_models"] = []
    cfg = dict(cfg_payload)
  else:
    cfg = save_config(**cfg_payload)
  return {
    "materialize": mat,
    "groups": prepared_groups,
    "validations": validations,
    "config": cfg,
    "sim": bool(sim),
  }


def start_bridge(
  *,
  require_chart: bool = False,
  poll_sec: float = 0.5,
  once: bool = False,
  sim: bool = False,
  auto_deploy_ea: bool = True,
  skip_preflight: bool = False,
) -> dict[str, Any]:
  t0 = time.time()
  preflight_mode = "none"
  # If LiveCheck was moved, rewrite stale absolute paths before workers spawn.
  try:
    import runpy
    from pathlib import Path as _Path

    heal = _Path(__file__).resolve().parents[2] / "scripts" / "heal_after_move.py"
    # LiveCheck/Trade/live/bridge_control.py → parents[2] = LiveCheck
    if heal.is_file():
      ns = runpy.run_path(str(heal))
      fn = ns.get("maybe_heal_on_boot")
      if callable(fn):
        summary = fn()
        if summary and int(summary.get("replacements") or 0) > 0:
          print(
            f"[heal] remapped {summary.get('replacements')} paths "
            f"in {summary.get('files_touched')} files "
            f"(prev={summary.get('previous_root')})",
            flush=True,
          )
  except Exception as exc:
    print(f"[heal] skipped: {exc}", flush=True)
  if is_kill_switch_armed():
    raise RuntimeError("Kill-switch armed — Disarm before Start")
  cfg0 = load_config()
  if cfg0.get("loss_guard_tripped") and not sim:
    raise RuntimeError(
      "Risk guard tripped — clear trip in Setup → Risk limits before Start. "
      f"Reason: {cfg0.get('loss_guard_tripped_reason') or '—'}"
    )
  # Stop prior workers of the SAME lane only — sim must not kill Live.
  if is_running(sim=sim) and not once:
    stop_bridge(flatten=False, sync_autostart=False, sim=sim)

  preflight: dict[str, Any] | None = None
  preflight_t0 = time.time()
  if (not sim) and (not skip_preflight) and (not once):
    from preflight_live import preflight_enabled_books, preflight_packages_ready
    # Reuse a fresh OK preflight to avoid multi-minute remine behind the UI spinner.
    cached = _read(RESULTS_DIR / "live_preflight.json") or {}
    cached_ok = bool(cached.get("ok"))
    cached_age = None
    try:
      from datetime import datetime
      ts = cached.get("updated_at")
      if ts:
        cached_age = (datetime.now().astimezone() - datetime.fromisoformat(str(ts))).total_seconds()
    except Exception:
      cached_age = None
    if cached_ok and cached_age is not None and cached_age < 20 * 60:
      preflight = {**cached, "skipped_reuse": True, "age_sec": cached_age}
      preflight_mode = "reuse"
      print(f"[start] reuse preflight ok age={cached_age:.0f}s", flush=True)
    else:
      # Default: packages + OHLC only. Full decide/remine hangs Start with 12 models.
      # Set LIVE_FULL_PREFLIGHT=1 to force decide_for_bar gate.
      full = str(os.environ.get("LIVE_FULL_PREFLIGHT") or "").strip().lower() in (
        "1", "true", "yes", "on",
      )
      if full:
        preflight_mode = "full"
        print("[start] running live preflight (decide_for_bar)…", flush=True)
        preflight = preflight_enabled_books(sim=False)
      else:
        preflight_mode = "fast"
        print("[start] running fast preflight (packages + OHLC)…", flush=True)
        preflight = preflight_packages_ready(sim=False)
      if not preflight.get("ok"):
        raise RuntimeError(
          "Live preflight failed — decision path broken before Start.\n"
          f"{preflight.get('error') or 'see live/results/live_preflight.json'}\n"
          "Fix packages/schedule/OHLC, or run Replay · Live-like first."
        )
  elif skip_preflight:
    preflight_mode = "skip"
  preflight_sec = round(time.time() - preflight_t0, 2)

  prep = prepare_runtime(require_chart=False, poll_sec=poll_sec, sim=sim)

  deploy_info: dict[str, Any] | None = None
  if (not sim) and auto_deploy_ea:
    from deploy_ea import ensure_live_eas_deployed
    # Windows: ensure MT5 running → check coverage → deploy all enabled books → wait heartbeat.
    # Linux: skipped (no MT5). Env LIVE_SKIP_EA_DEPLOY=1 also skips (but still tries to open MT5).
    deploy_info = ensure_live_eas_deployed(
      force=False,
      wait_online=True,
      wait_sec=60.0 if require_chart else 45.0,
      deploy_timeout_sec=240.0,
      stale_after=45.0,
    )
    if require_chart:
      # Re-validate after deploy so Start fails clearly if a book is still offline
      prep = prepare_runtime(require_chart=True, poll_sec=poll_sec, sim=sim)
  elif (not sim) and os.name == "nt":
    # Deploy skipped, but still boot terminal if user closed MT5.
    try:
      from deploy_ea import ensure_mt5_running
      mt5 = ensure_mt5_running()
      deploy_info = {
        "ok": bool(mt5.get("ok")),
        "skipped": True,
        "reason": "deploy_skipped_mt5_only",
        "deployed": False,
        "mt5": mt5,
      }
      if not mt5.get("ok"):
        raise RuntimeError(
          "Không khởi động được XM Global MT5.\n"
          f"{mt5.get('error') or mt5.get('reason') or ''}"
        )
    except RuntimeError:
      raise
    except Exception:
      pass

  try:
    from debug_log import log_event, prune_old_logs
    prune_old_logs()
    books_planned = [
      {"symbol": g.get("symbol"), "timeframe": g.get("timeframe"), "model_ids": g.get("model_ids")}
      for g in (prep.get("groups") or [])
      if not g.get("skip")
    ]
    log_event(
      "bridge_start",
      summary=(
        f"start sim={sim} preflight={preflight_mode} "
        f"books={len(books_planned)} preflight_sec={preflight_sec}"
      ),
      payload={
        "sim": bool(sim),
        "require_chart": bool(require_chart),
        "preflight_mode": preflight_mode,
        "preflight_sec": preflight_sec,
        "preflight_ok": (preflight or {}).get("ok") if preflight is not None else None,
        "preflight_age_sec": (preflight or {}).get("age_sec") if preflight else None,
        "books": books_planned,
        "n_books": len(books_planned),
        "deploy": {
          "skipped": (deploy_info or {}).get("skipped"),
          "deployed": (deploy_info or {}).get("deployed"),
          "reason": (deploy_info or {}).get("reason"),
        } if deploy_info else None,
        "model_ids": (prep.get("materialize") or {}).get("model_ids"),
      },
      source="bridge_control",
    )
  except Exception:
    pass

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  WORKERS_DIR.mkdir(parents=True, exist_ok=True)

  workers: list[dict] = []
  started = []
  base_port = LIVE_SIM_PORT if sim else LIVE_BRIDGE_PORT
  for i, g in enumerate(prep["groups"]):
    if g.get("skip"):
      continue
    sym, tf = g["symbol"], g["timeframe"]
    bdir = Path(g["bridge_dir"])
    if sim and not bdir.name.startswith("bridge_sim_live"):
      raise RuntimeError(f"EA Simulate refused live bridge dir: {bdir.name}")
    if (not sim) and bdir.name.startswith("bridge_sim_live"):
      raise RuntimeError(f"Live refused sim bridge dir: {bdir.name}")
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "decisions").mkdir(exist_ok=True)
    key = f"{sym}_{tf}".lower()
    port = int(base_port) + i
    log_path = WORKERS_DIR / (f"sim_{key}.log" if sim else f"{key}.log")
    pid_path = WORKERS_DIR / (f"sim_{key}.pid" if sim else f"{key}.pid")
    risk = 1.0
    for r in g.get("rows") or []:
      risk = float(r.get("risk_pct") or 1.0)
      break
    cmd = [
      sys.executable,
      str(SERVICE_SCRIPT),
      "--bridge-dir", str(bdir),
      "--symbol", sym,
      "--timeframe", tf,
      "--risk-pct", str(risk),
      "--poll", str(poll_sec),
      "--monitor-port", str(port),
      "--model-ids", ",".join(g["model_ids"]),
    ]
    if sim:
      cmd.append("--sim")
    if once:
      cmd.append("--once")

    logf = open(log_path, "a", encoding="utf-8")
    logf.write(f"\n--- start {_now()} sim={sim} ---\n")
    logf.flush()
    # Stagger multi-book starts so materialize + heavy imports don't stampede.
    if started:
      time.sleep(0.8)
    popen_kwargs: dict[str, Any] = {
      "cwd": str(LIVE_ROOT),
      "stdout": logf,
      "stderr": subprocess.STDOUT,
      "close_fds": False if os.name == "nt" else True,
    }
    if os.name == "nt":
      # New process group + no console flash when Streamlit starts workers.
      popen_kwargs["creationflags"] = (
        subprocess.CREATE_NEW_PROCESS_GROUP
        | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
      )
    else:
      popen_kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **popen_kwargs)
    pid_path.write_text(str(proc.pid), encoding="utf-8")
    w = {
      "key": key,
      "symbol": sym,
      "timeframe": tf,
      "bridge_dir": str(bdir),
      "bridge_subdir": bridge_subdir(sym, tf, sim=sim),
      "model_ids": g["model_ids"],
      "pid": proc.pid,
      "monitor_port": port,
      "log": str(log_path),
      "sim": bool(sim),
    }
    workers.append(w)
    started.append(w)
    _write(bdir / "status.json", {
      "updated_at": _now(),
      "state": "starting",
      "pid": proc.pid,
      "model_ids": g["model_ids"],
      "sim": bool(sim),
    })
    try:
      from debug_log import log_event
      log_event(
        "worker_spawn",
        summary=f"spawn {sym} {tf} pid={proc.pid}",
        payload={
          "pid": proc.pid,
          "monitor_port": port,
          "model_ids": g["model_ids"],
          "log": str(log_path),
          "sim": bool(sim),
        },
        symbol=sym,
        timeframe=tf,
        bridge_dir=bdir,
        source="bridge_control",
      )
    except Exception:
      pass
    if once:
      break

  save_workers(workers, sim=sim)
  primary = workers[0] if workers else {}
  if not sim:
    save_config(
      enabled=not once,
      mode="process",
      service_pid=primary.get("pid"),
      bridge_dir=primary.get("bridge_dir"),
      model_ids=prep["materialize"]["model_ids"],
      last_action="start",
      workers=len(workers),
      sim=False,
      last_deploy=deploy_info,
    )

  # Confirm workers stay up. Bootstrap/remine is slow — poll PIDs up to 20s.
  # Only fail when every worker pid is dead AND logs show a hard crash (not progress).
  if workers and not once:
    deadline = time.time() + 20.0
    alive_pids: list[dict] = []
    while time.time() < deadline:
      alive_pids = [w for w in workers if _pid_alive(w.get("pid"))]
      if len(alive_pids) >= max(1, len(workers) // 2):
        break
      time.sleep(0.5)

    if not alive_pids:
      soft_ok = []
      for w in workers:
        logp = Path(w.get("log") or "")
        if not logp.is_file():
          continue
        if _worker_looks_crashed(logp):
          continue
        tail = _worker_log_tail_since_start(logp, max_lines=40)
        if "[live-bridge]" in tail or "[bridge]" in tail or _worker_status_active(w.get("bridge_dir")):
          soft_ok.append(w)
      if soft_ok:
        alive_pids = soft_ok
      else:
        tails: list[str] = []
        for w in workers[:4]:
          chunk = _worker_log_tail_since_start(Path(w.get("log") or ""), max_lines=16)
          if chunk:
            tails.append(f"[{w.get('key')}]\n{chunk}")
        detail = "\n\n".join(tails) if tails else "no worker logs"
        raise RuntimeError(
          "Start failed — bridge workers exited immediately.\n"
          "Xem log worker trong live/results/workers/.\n"
          f"{detail}"
        )

    for w in workers:
      w["alive"] = _pid_alive(w.get("pid"))
    save_workers(workers, sim=sim)

  autostart_info: dict[str, Any] | None = None
  if (not sim) and (not once) and workers:
    try:
      if str(os.environ.get("LIVE_SKIP_AUTOSTART") or "").strip().lower() in (
        "1", "true", "yes", "on",
      ):
        autostart_info = {"ok": True, "skipped": True, "reason": "env:LIVE_SKIP_AUTOSTART"}
      else:
        from windows_autostart import sync_autostart_with_trading
        # Keep this best-effort and short — never block Start for long.
        autostart_info = sync_autostart_with_trading(active=True)
      try:
        from debug_log import log_event
        log_event(
          "autostart_attach",
          summary=str((autostart_info or {}).get("message") or (autostart_info or {}).get("reason") or ""),
          payload=autostart_info,
          source="bridge_control",
        )
      except Exception:
        pass
    except Exception as exc:
      autostart_info = {"ok": False, "skipped": False, "reason": f"error:{exc}"}

  alive_n = sum(1 for w in workers if _pid_alive(w.get("pid"))) if workers else 0
  duration_sec = round(time.time() - t0, 2)
  try:
    from debug_log import log_event
    log_event(
      "bridge_start_done",
      summary=(
        f"done preflight={preflight_mode} alive={alive_n}/{len(workers)} "
        f"duration_sec={duration_sec}"
      ),
      payload={
        "preflight_mode": preflight_mode,
        "preflight_sec": preflight_sec,
        "duration_sec": duration_sec,
        "n_workers": len(workers),
        "alive": alive_n,
        "books": [
          {
            "key": w.get("key"),
            "symbol": w.get("symbol"),
            "timeframe": w.get("timeframe"),
            "pid": w.get("pid"),
            "alive": _pid_alive(w.get("pid")),
            "model_ids": w.get("model_ids"),
          }
          for w in workers
        ],
        "sim": bool(sim),
      },
      source="bridge_control",
    )
  except Exception:
    pass
  return {
    "pid": primary.get("pid"),
    "workers": workers,
    "n_workers": alive_n or len(workers),
    "once": once,
    "sim": bool(sim),
    "deploy": deploy_info,
    "autostart": autostart_info,
    "preflight_mode": preflight_mode,
    "preflight_sec": preflight_sec,
    "duration_sec": duration_sec,
    **prep,
  }


def stop_bridge(
  *,
  flatten: bool = False,
  sync_autostart: bool = True,
  sim: bool = False,
) -> dict[str, Any]:
  if sim:
    flatten = False
    sync_autostart = False
  workers = load_workers(sim=sim).get("workers") or []
  pids = []
  for w in workers:
    pid = w.get("pid")
    pids.append(pid)
    try:
      from debug_log import log_event
      log_event(
        "worker_kill",
        summary=f"kill {w.get('symbol')} {w.get('timeframe')} pid={pid} sim={sim}",
        payload={"pid": pid, "flatten": bool(flatten), "key": w.get("key"), "sim": bool(sim)},
        symbol=w.get("symbol"),
        timeframe=w.get("timeframe"),
        bridge_dir=w.get("bridge_dir"),
        source="bridge_control",
      )
    except Exception:
      pass
    _kill_pid(pid)
    bdir = Path(w.get("bridge_dir") or "")
    if bdir:
      _write(bdir / "status.json", {"updated_at": _now(), "state": "stopped", "sim": bool(sim)})
      if sim and bdir.name.startswith("bridge_sim_live"):
        try:
          ctrl = _read(bdir / "sim_control.json") or {}
          if isinstance(ctrl, dict):
            ctrl["enabled"] = False
            ctrl["ea_status"] = "idle"
            ctrl["updated_at"] = _now()
            _write(bdir / "sim_control.json", ctrl)
        except Exception:
          pass

  if not sim:
    # legacy single-process cleanup (Live lane only)
    cfg = load_config()
    _kill_pid(cfg.get("service_pid"))
    legacy_pid = RESULTS_DIR / "mt5_bridge_service.pid"
    if legacy_pid.exists():
      try:
        _kill_pid(int(legacy_pid.read_text().strip()))
        legacy_pid.unlink()
      except Exception:
        pass

  save_workers([], sim=sim)
  if not sim:
    save_config(enabled=False, service_pid=None, last_action="stop", workers=0)
  if flatten and not sim:
    # BUG-13: full discovery (roster + workers + disk). Passing a single
    # bridge_dir skips orphan books that are no longer in live_workers.json.
    from safety import write_flatten_command
    write_flatten_command(reason="bridge_stop")
  if not sim:
    _write(BRIDGE_DIR / "status.json", {"updated_at": _now(), "state": "stopped"})
  try:
    from debug_log import log_event
    log_event(
      "bridge_stop",
      summary=f"stop flatten={flatten} sim={sim} pids={pids}",
      payload={"flatten": bool(flatten), "sim": bool(sim), "pids": pids},
      source="bridge_control",
    )
  except Exception:
    pass

  autostart_info: dict[str, Any] | None = None
  if sync_autostart and not sim:
    try:
      from windows_autostart import sync_autostart_with_trading
      # Stop trading → gỡ Scheduled Task (reboot không tự resume)
      autostart_info = sync_autostart_with_trading(active=False)
      try:
        from debug_log import log_event
        log_event(
          "autostart_detach",
          summary=str((autostart_info or {}).get("message") or (autostart_info or {}).get("reason") or ""),
          payload=autostart_info,
          source="bridge_control",
        )
      except Exception:
        pass
    except Exception:
      autostart_info = None

  return {"stopped": True, "pids": pids, "autostart": autostart_info, "sim": bool(sim)}


def status(*, sim: bool = False) -> dict[str, Any]:
  cfg = load_config() if not sim else {}
  workers = []
  for w in load_workers(sim=sim).get("workers") or []:
    w = dict(w)
    w["alive"] = _pid_alive(w.get("pid"))
    w["bridge_status"] = _read(Path(w["bridge_dir"]) / "status.json") if w.get("bridge_dir") else {}
    workers.append(w)
  alive = [w for w in workers if w.get("alive")]
  return {
    "running": bool(alive),
    "pid": alive[0]["pid"] if alive else None,
    "config": cfg,
    "workers": workers,
    "n_workers": len(alive),
    "bridge_status": (alive[0].get("bridge_status") if alive else {}) or {},
    "kill_switch": is_kill_switch_armed(),
    "log": str(WORKERS_DIR),
    "sim": bool(sim),
  }
