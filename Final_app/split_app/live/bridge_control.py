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


def load_workers() -> dict:
  data = _read(WORKERS_PATH)
  if not data:
    return {"updated_at": None, "workers": []}
  return data


def save_workers(workers: list[dict]) -> dict:
  payload = {"updated_at": _now(), "workers": workers}
  _write(WORKERS_PATH, payload)
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


def is_running() -> bool:
  return any(_pid_alive(w.get("pid")) for w in load_workers().get("workers") or [])


def service_pid() -> int | None:
  """Primary worker pid (compat)."""
  for w in load_workers().get("workers") or []:
    if _pid_alive(w.get("pid")):
      return int(w["pid"])
  # legacy single pid
  cfg = load_config()
  pid = cfg.get("service_pid")
  return int(pid) if _pid_alive(pid) else None


def prepare_runtime(
  *,
  require_chart: bool = False,
  poll_sec: float = 2.0,
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

  primary_risk = float(enabled[0].get("risk_pct") or 1.0)
  port = LIVE_SIM_PORT if sim else LIVE_BRIDGE_PORT
  cfg = save_config(
    enabled=False,
    mode="process",
    poll_sec=float(poll_sec),
    model_ids=mat["model_ids"],
    risk_pct=primary_risk,
    monitor_port=port,
    sim=bool(sim),
    **guard,
    last_error=None,
  )
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
  poll_sec: float = 2.0,
  once: bool = False,
  sim: bool = False,
  auto_deploy_ea: bool = True,
) -> dict[str, Any]:
  if is_kill_switch_armed():
    raise RuntimeError("Kill-switch armed — Disarm before Start")
  cfg0 = load_config()
  if cfg0.get("loss_guard_tripped") and not sim:
    raise RuntimeError(
      "Risk guard tripped — clear trip in Setup → Risk limits before Start. "
      f"Reason: {cfg0.get('loss_guard_tripped_reason') or '—'}"
    )
  # Stop prior workers first for clean multi-start
  if is_running() and not once:
    stop_bridge(flatten=False, sync_autostart=False)

  prep = prepare_runtime(require_chart=False, poll_sec=poll_sec, sim=sim)

  deploy_info: dict[str, Any] | None = None
  if (not sim) and auto_deploy_ea:
    from deploy_ea import ensure_live_eas_deployed
    # Windows: check coverage → deploy all enabled books → wait heartbeat.
    # Linux: skipped (no MT5). Env LIVE_SKIP_EA_DEPLOY=1 also skips.
    deploy_info = ensure_live_eas_deployed(
      force=False,
      wait_online=True,
      wait_sec=60.0 if require_chart else 45.0,
      deploy_timeout_sec=240.0,
    )
    if require_chart:
      # Re-validate after deploy so Start fails clearly if a book is still offline
      prep = prepare_runtime(require_chart=True, poll_sec=poll_sec, sim=sim)

  try:
    from debug_log import log_event, prune_old_logs
    prune_old_logs()
    log_event(
      "bridge_start",
      summary=f"start sim={sim} workers={len([g for g in prep.get('groups') or [] if not g.get('skip')])}",
      payload={
        "sim": bool(sim),
        "require_chart": bool(require_chart),
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
    proc = subprocess.Popen(
      cmd,
      cwd=str(LIVE_ROOT),
      stdout=logf,
      stderr=subprocess.STDOUT,
      start_new_session=True,
      close_fds=True,
    )
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
    if once:
      break

  save_workers(workers)
  primary = workers[0] if workers else {}
  save_config(
    enabled=not once,
    mode="process",
    service_pid=primary.get("pid"),
    bridge_dir=primary.get("bridge_dir"),
    model_ids=prep["materialize"]["model_ids"],
    last_action="start_sim" if sim else "start",
    workers=len(workers),
    sim=bool(sim),
    last_deploy=deploy_info,
  )

  autostart_info: dict[str, Any] | None = None
  if (not sim) and (not once) and workers:
    try:
      from windows_autostart import sync_autostart_with_trading
      # Start trading → gắn Scheduled Task (MT5 + app + bridge sau reboot)
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
    except Exception:
      autostart_info = None

  return {
    "pid": primary.get("pid"),
    "workers": workers,
    "n_workers": len(workers),
    "once": once,
    "sim": bool(sim),
    "deploy": deploy_info,
    "autostart": autostart_info,
    **prep,
  }


def stop_bridge(*, flatten: bool = False, sync_autostart: bool = True) -> dict[str, Any]:
  workers = load_workers().get("workers") or []
  pids = []
  for w in workers:
    pid = w.get("pid")
    pids.append(pid)
    _kill_pid(pid)
    bdir = Path(w.get("bridge_dir") or "")
    if bdir:
      _write(bdir / "status.json", {"updated_at": _now(), "state": "stopped"})
      if flatten:
        from safety import write_flatten_command
        write_flatten_command(reason="bridge_stop", bridge_dir=bdir)

  # legacy single-process cleanup
  cfg = load_config()
  _kill_pid(cfg.get("service_pid"))
  legacy_pid = RESULTS_DIR / "mt5_bridge_service.pid"
  if legacy_pid.exists():
    try:
      _kill_pid(int(legacy_pid.read_text().strip()))
      legacy_pid.unlink()
    except Exception:
      pass

  save_workers([])
  save_config(enabled=False, service_pid=None, last_action="stop", workers=0)
  if flatten and not workers:
    from safety import write_flatten_command
    write_flatten_command(reason="bridge_stop", bridge_dir=BRIDGE_DIR)
  _write(BRIDGE_DIR / "status.json", {"updated_at": _now(), "state": "stopped"})
  try:
    from debug_log import log_event
    log_event(
      "bridge_stop",
      summary=f"stop flatten={flatten} pids={pids}",
      payload={"flatten": bool(flatten), "pids": pids},
      source="bridge_control",
    )
  except Exception:
    pass

  autostart_info: dict[str, Any] | None = None
  if sync_autostart:
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

  return {"stopped": True, "pids": pids, "autostart": autostart_info}


def status() -> dict[str, Any]:
  cfg = load_config()
  workers = []
  for w in load_workers().get("workers") or []:
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
    "bridge_status": (alive[0].get("bridge_status") if alive else _read(BRIDGE_DIR / "status.json")) or {},
    "kill_switch": is_kill_switch_armed(),
    "log": str(WORKERS_DIR),
  }
