"""Background worker — MT5 bridge decision service (GUI-controllable).

Default Start = detached OS process (`scripts/mt5_bridge_service.py`) so it
survives Streamlit tab switches and page refresh. Thread mode is fallback only.

Dual-TF: every public function accepts an optional ``tf=`` ("M15"|"H1"). When
omitted it resolves to ``config.get_active_tf()`` (M15 by default), so
existing single-TF callers keep working unchanged. Config/PID/log files live
under each TF's own ``results/{tf}/`` dir, and live vs sim use distinct
filenames, so all 4 workers (M15 live/sim, H1 live/sim) run independently.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from config import get_active_tf
from mt5_bridge.comm_log import append_event
from mt5_bridge.engine import BridgeEngine
from mt5_bridge.history_sync import cache_path_for, process_history_sync, start_history_sync
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  DEFAULT_MODEL_ID,
  atomic_write_json,
  bar_path,
  bridge_dir_for,
  decision_path,
  ensure_bridge_dir,
  fill_path,
  read_json,
  write_status,
)
from mt5_bridge.trade_journal import process_fill
from runtime_profiles import get_tf_defaults

ROOT = Path(__file__).resolve().parents[1]
SERVICE_SCRIPT = ROOT / "scripts" / "mt5_bridge_service.py"
SIM_SERVICE_SCRIPT = ROOT / "scripts" / "mt5_bridge_sim_service.py"


def _tf(tf: str | None = None) -> str:
  return str(tf or get_active_tf()).upper()


def _report_dir(tf: str | None = None) -> Path:
  return get_tf_defaults(_tf(tf)).report_dir


def config_path(tf: str | None = None) -> Path:
  return _report_dir(tf) / "mt5_bridge_config.json"


def pid_path(tf: str | None = None) -> Path:
  return _report_dir(tf) / "mt5_bridge_service.pid"


def service_log_path(tf: str | None = None) -> Path:
  return _report_dir(tf) / "mt5_bridge_service.log"


def sim_pid_path(tf: str | None = None) -> Path:
  return _report_dir(tf) / "mt5_bridge_sim_service.pid"


def sim_service_log_path(tf: str | None = None) -> Path:
  return _report_dir(tf) / "mt5_bridge_sim_service.log"


# Back-compat module-level aliases — resolve for the *active* TF at import
# time (M15 by default). Prefer the tf-aware functions above in new code.
CONFIG_PATH = config_path()
PID_PATH = pid_path()
SERVICE_LOG = service_log_path()
SIM_PID_PATH = sim_pid_path()
SIM_SERVICE_LOG = sim_service_log_path()

_lock = threading.Lock()
_threads: dict[str, threading.Thread] = {}
_stops: dict[str, threading.Event] = {}
_engines: dict[str, BridgeEngine] = {}


def _stop_event(tf: str) -> threading.Event:
  return _stops.setdefault(tf, threading.Event())


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _engine_status_fields(engine: BridgeEngine, **extra) -> dict:
  """Status fields shared with Health (same Trade Model conditions fingerprint)."""
  return {
    "model_id": engine.model_id,
    "conditions_fp": engine.conditions_fp,
    "run_conditions": engine.describe_conditions(),
    **extra,
  }


def _read_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path: Path, data: dict) -> None:
  atomic_write_json(path, data)


def load_config(tf: str | None = None) -> dict:
  t = _tf(tf)
  data = _read_json(config_path(t)) or {}
  default_dir = bridge_dir_for(t, "live")
  bridge_dir = data.get("bridge_dir") or str(default_dir)
  # Config may come from the old Linux/Docker deployment. On native Windows
  # that path is invalid and causes a failed service restart on every rerun.
  if os.name == "nt" and str(bridge_dir).startswith("/"):
    bridge_dir = str(default_dir)
  # Reject foreign-repo / legacy folder names (bridge, not bridge_m15/h1)
  try:
    bd = Path(bridge_dir).resolve()
    expected = default_dir.resolve()
    under_root = ROOT.resolve() in bd.parents or bd == expected
    if (not under_root) or bd.name not in (
      "bridge_m15", "bridge_h1", "bridge_sim_m15", "bridge_sim_h1",
    ):
      bridge_dir = str(default_dir)
  except Exception:
    bridge_dir = str(default_dir)
  return {
    "tf": t,
    "enabled": bool(data.get("enabled", False)),
    "model_id": data.get("model_id") or DEFAULT_MODEL_ID,
    "risk_pct": float(data.get("risk_pct", 1.0)),
    "poll_sec": float(data.get("poll_sec", 2.0)),
    "bridge_dir": bridge_dir,
    "mode": data.get("mode") or "process",
    "service_pid": data.get("service_pid"),
    "last_run_at": data.get("last_run_at"),
    "last_error": data.get("last_error"),
    "last_action": data.get("last_action"),
    "last_bar": data.get("last_bar"),
  }


def save_config(*, tf: str | None = None, **updates) -> dict:
  t = _tf(tf)
  cfg = load_config(t)
  # Allow clearing nullable fields with None (e.g. service_pid)
  nullable = {"service_pid", "last_error", "last_action", "last_bar", "last_run_at"}
  for k, v in updates.items():
    if k == "tf":
      continue
    if v is None and k not in nullable:
      continue
    cfg[k] = v
  cfg["tf"] = t
  _write_json(config_path(t), cfg)
  return cfg


def _pid_alive(pid: int | None) -> bool:
  if not pid:
    return False
  if os.name == "nt":
    try:
      import ctypes
      from ctypes import wintypes

      process_query_limited_information = 0x1000
      still_active = 259
      kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
      handle = kernel32.OpenProcess(
        process_query_limited_information, False, int(pid),
      )
      if not handle:
        return False
      try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
          return False
        return exit_code.value == still_active
      finally:
        kernel32.CloseHandle(handle)
    except (OSError, TypeError, ValueError):
      return False
  try:
    os.kill(int(pid), 0)
    return True
  except (OSError, TypeError, ValueError):
    return False


def _read_pid_file(tf: str | None = None) -> int | None:
  path = pid_path(tf)
  if not path.exists():
    return None
  try:
    return int(path.read_text(encoding="utf-8").strip())
  except (OSError, ValueError):
    return None


def _clear_pid(tf: str | None = None) -> None:
  t = _tf(tf)
  save_config(tf=t, service_pid=None)
  try:
    path = pid_path(t)
    if path.exists():
      path.unlink()
  except OSError:
    pass


def is_process_running(tf: str | None = None) -> bool:
  t = _tf(tf)
  cfg = load_config(t)
  pid = cfg.get("service_pid") or _read_pid_file(t)
  if _pid_alive(pid):
    return True
  if cfg.get("service_pid") or pid_path(t).exists():
    _clear_pid(t)
  return False


def is_thread_running(tf: str | None = None) -> bool:
  t = _tf(tf)
  thr = _threads.get(t)
  return thr is not None and thr.is_alive() and not _stop_event(t).is_set()


def is_running(tf: str | None = None) -> bool:
  t = _tf(tf)
  return is_process_running(t) or is_thread_running(t)


def get_status(tf: str | None = None) -> dict:
  t = _tf(tf)
  cfg = load_config(t)
  proc = is_process_running(t)
  thr = is_thread_running(t)
  pid = cfg.get("service_pid") or _read_pid_file(t)
  if proc:
    mode = "process"
  elif thr:
    mode = "thread"
  else:
    mode = "off"
  return {
    **cfg,
    "running": proc or thr,
    "thread_alive": thr,
    "process_alive": proc,
    "service_pid": int(pid) if proc and pid else None,
    "runtime_mode": mode,
  }


def _bar_fp(bar: dict | None) -> str | None:
  if not isinstance(bar, dict):
    return None
  return str(bar.get("time") or bar.get("bar_time") or bar.get("time_msc") or "")


def _fill_fp(fill: dict | None) -> str | None:
  if not isinstance(fill, dict):
    return None
  return (
    str(fill.get("signal_id") or "")
    + "|"
    + str(fill.get("time") or fill.get("bar_time") or "")
    + "|"
    + str(fill.get("event") or fill.get("detail") or "")
    + "|"
    + str(fill.get("ticket") or "")
    + "|"
    + str(fill.get("reason") or "")
    + "|"
    + str(fill.get("price") or fill.get("exit_px") or "")
    + "|"
    + str(fill.get("sl") or "")
    + "|"
    + str(fill.get("tp") or "")
    + "|"
    + str(fill.get("manual") or "")
  )


def _is_sim_dir(bridge_dir: Path) -> bool:
  from mt5_bridge.protocol import BRIDGE_SIM_DIR, BRIDGE_SIM_H1_DIR

  resolved = Path(bridge_dir).resolve()
  return resolved in (BRIDGE_SIM_DIR.resolve(), BRIDGE_SIM_H1_DIR.resolve())


def _cycle(engine: BridgeEngine, bridge_dir: Path, last_bar_fp: str | None, last_fill_fp: str | None):
  is_sim = _is_sim_dir(bridge_dir)
  seen_fills: set[str] = set()
  if isinstance(last_fill_fp, str) and last_fill_fp.startswith("["):
    try:
      seen_fills = set(json.loads(last_fill_fp))
    except Exception:
      seen_fills = {last_fill_fp} if last_fill_fp else set()
  elif last_fill_fp:
    seen_fills = {last_fill_fp}

  def _ingest_fill(fill: dict) -> None:
    nonlocal seen_fills
    fp_fill = _fill_fp(fill)
    if not fp_fill or fp_fill in seen_fills:
      return
    if not is_sim:
      append_event(
        "ea_to_app",
        "fill_received",
        bridge_dir=bridge_dir,
        payload=fill,
        summary=(
          f"fill {fill.get('event') or fill.get('action')} ok={fill.get('ok')} "
          f"sid={fill.get('signal_id')} detail={fill.get('detail')}"
        ),
      )
    last_decision = engine._last_decision if engine else None
    process_fill(
      fill,
      bridge_dir=bridge_dir,
      decision=last_decision if isinstance(last_decision, dict) else None,
      model_id=engine.model_id if engine else None,
    )
    seen_fills.add(fp_fill)
    if not is_sim:
      save_config(tf=engine.tf, last_run_at=_now_iso())

  # HistoryFeed: drain append-only queue (open+close can land within 1ms)
  fills_q = ensure_bridge_dir(bridge_dir) / "ea_fills.jsonl"
  if fills_q.exists():
    try:
      raw = fills_q.read_text(encoding="utf-8-sig")
      if raw.strip():
        for line in raw.splitlines():
          line = line.strip()
          if not line:
            continue
          try:
            payload = json.loads(line)
          except Exception:
            continue
          if isinstance(payload, dict):
            _ingest_fill(payload)
        # Truncate so we do not re-read a growing file every 30ms
        fills_q.write_text("", encoding="utf-8")
    except Exception:
      pass

  fill = read_json(fill_path(bridge_dir))
  if isinstance(fill, dict):
    _ingest_fill(fill)

  last_fill_fp = json.dumps(sorted(seen_fills)[-80:], ensure_ascii=False)

  bar = read_json(bar_path(bridge_dir))
  if not isinstance(bar, dict):
    return last_bar_fp, last_fill_fp

  fp = _bar_fp(bar)
  if not fp:
    return last_bar_fp, last_fill_fp

  if fp == last_bar_fp:
    # Idle wait — do not rewrite status.json every ~30ms (GUI + antivirus lag)
    return last_bar_fp, last_fill_fp

  if not is_sim:
    append_event(
      "ea_to_app",
      "bar_received",
      bridge_dir=bridge_dir,
      payload={
        "symbol": bar.get("symbol"),
        "time": bar.get("time") or bar.get("bar_time"),
        "close": bar.get("close"),
        "account": bar.get("account"),
      },
      summary=f"bar {bar.get('symbol')} {bar.get('time') or bar.get('bar_time')} c={bar.get('close')}",
    )

  decision = engine.decide_for_bar(bar)
  atomic_write_json(decision_path(bridge_dir), decision)
  action_u = str(decision.get("action") or "").upper()
  if not is_sim or action_u in ("BUY", "SELL"):
    append_event(
      "app_to_ea",
      "decision_sent",
      bridge_dir=bridge_dir,
      payload={
        "action": decision.get("action"),
        "bar_time": decision.get("bar_time"),
        "signal_id": decision.get("signal_id"),
        "reason": decision.get("reason"),
        "entry": decision.get("entry"),
        "sl": decision.get("sl"),
        "tp": decision.get("tp"),
        "strategy_name": decision.get("strategy_name"),
      },
      summary=(
        f"decision {decision.get('action')} bar={decision.get('bar_time')} "
        f"reason={decision.get('reason')}"
      ),
    )
  write_status(
    bridge_dir,
    state="decided",
    last_bar=fp,
    last_action=decision.get("action"),
    reason=decision.get("reason"),
    week_start=decision.get("week_start"),
    strategy_name=decision.get("strategy_name"),
    error=None,
    **_engine_status_fields(engine),
  )
  if not is_sim:
    save_config(
      tf=engine.tf,
      last_run_at=_now_iso(),
      last_action=decision.get("action"),
      last_bar=fp,
      last_error=None,
    )
  return fp, last_fill_fp


def _worker(tf: str):
  stop = _stop_event(tf)
  cfg = load_config(tf)
  bridge_dir = ensure_bridge_dir(Path(cfg["bridge_dir"]))
  cache_path = cache_path_for(tf)
  append_event("system", "service_start", bridge_dir=bridge_dir, summary=f"bridge thread started tf={tf}")
  start_history_sync(bridge_dir, tf=tf)
  try:
    engine = BridgeEngine(
      model_id=cfg["model_id"], risk_pct=cfg["risk_pct"], bridge_dir=bridge_dir, tf=tf,
    )
    _engines[tf] = engine
    if cache_path.exists():
      engine.ensure_history()
    write_status(
      bridge_dir,
      state="running",
      error=None,
      runtime="thread",
      **_engine_status_fields(engine),
    )
  except Exception as e:
    save_config(tf=tf, last_error=str(e), enabled=False)
    append_event(
      "system", "error", bridge_dir=bridge_dir, summary=str(e),
      payload={"tb": traceback.format_exc()[-1500:]},
    )
    write_status(bridge_dir, state="error", model_id=cfg["model_id"], error=str(e))
    return

  last_bar_fp = None
  last_fill_fp = None
  while not stop.is_set():
    cfg = load_config(tf)
    if not cfg.get("enabled"):
      break
    poll = max(0.3, float(cfg.get("poll_sec") or 2.0))
    engine = _engines.get(tf)
    try:
      process_history_sync(bridge_dir, tf=tf)
      if not cache_path.exists():
        stop.wait(poll)
        continue
      if engine and (
        engine.model_id != cfg["model_id"]
        or abs(engine.risk_pct - float(cfg["risk_pct"])) > 1e-9
      ):
        engine = BridgeEngine(
          model_id=cfg["model_id"], risk_pct=float(cfg["risk_pct"]), bridge_dir=bridge_dir, tf=tf,
        )
        _engines[tf] = engine
        engine.ensure_history()
        append_event(
          "system", "engine_reload", bridge_dir=bridge_dir,
          summary=f"model={cfg['model_id']} risk={cfg['risk_pct']} fp={engine.conditions_fp}",
        )
      elif engine and engine.refresh_model():
        # Same model_id but mining/KB/spread changed on disk — keep Bridge = Health.
        append_event(
          "system", "engine_reload", bridge_dir=bridge_dir,
          summary=f"conditions_fp={engine.conditions_fp} (model params updated)",
          payload=engine.describe_conditions(),
        )
      last_bar_fp, last_fill_fp = _cycle(engine, bridge_dir, last_bar_fp, last_fill_fp)
    except Exception as e:
      save_config(tf=tf, last_error=str(e), last_run_at=_now_iso())
      append_event(
        "system", "error", bridge_dir=bridge_dir,
        summary=str(e), payload={"tb": traceback.format_exc()[-1500:]},
      )
      write_status(bridge_dir, state="error", model_id=cfg["model_id"], error=str(e))
    stop.wait(poll)

  append_event("system", "service_stop", bridge_dir=bridge_dir, summary=f"bridge thread stopped tf={tf}")
  write_status(bridge_dir, state="stopped", model_id=cfg.get("model_id"), error=None)


def start_thread_worker(tf: str | None = None) -> bool:
  t = _tf(tf)
  with _lock:
    if is_process_running(t) or is_thread_running(t):
      return True
    save_config(tf=t, enabled=True, mode="thread")
    _stop_event(t).clear()
    thread = threading.Thread(target=_worker, args=(t,), name=f"mt5-bridge-{t.lower()}", daemon=True)
    _threads[t] = thread
    thread.start()
    return True


def start_process_worker(tf: str | None = None) -> bool:
  """Detached CLI process — survives GUI tab switch / page refresh."""
  t = _tf(tf)
  with _lock:
    if is_process_running(t):
      save_config(tf=t, enabled=True, mode="process")
      return True
    _stop_event(t).set()
    cfg = load_config(t)
    report_dir = _report_dir(t)
    report_dir.mkdir(parents=True, exist_ok=True)
    default_dir = bridge_dir_for(t, "live")
    cmd = [
      sys.executable,
      str(SERVICE_SCRIPT),
      "--tf", t,
      "--model-id", str(cfg.get("model_id") or DEFAULT_MODEL_ID),
      "--risk-pct", str(cfg.get("risk_pct") or 1.0),
      "--poll", str(cfg.get("poll_sec") or 2.0),
      "--bridge-dir", str(cfg.get("bridge_dir") or default_dir),
    ]
    log_path = service_log_path(t)
    logf = open(log_path, "a", encoding="utf-8")
    logf.write(f"\n--- start {_now_iso()} tf={t} ---\n")
    logf.flush()
    proc = subprocess.Popen(
      cmd,
      cwd=str(ROOT),
      stdout=logf,
      stderr=subprocess.STDOUT,
      start_new_session=True,
      close_fds=True,
    )
    pid_path(t).write_text(str(proc.pid), encoding="utf-8")
    save_config(tf=t, enabled=True, mode="process", service_pid=proc.pid, last_error=None)
    append_event(
      "system", "service_start",
      summary=f"detached process pid={proc.pid} tf={t}",
      payload={"pid": proc.pid, "tf": t},
    )
    write_status(
      Path(cfg.get("bridge_dir") or default_dir),
      state="running",
      model_id=cfg.get("model_id"),
      runtime="process",
      pid=proc.pid,
      error=None,
    )
    return True


def start_worker(*, tf: str | None = None, detached: bool = True) -> bool:
  """Default: detached process (safe across Streamlit refresh)."""
  if detached:
    return start_process_worker(tf)
  return start_thread_worker(tf)


def stop_worker(tf: str | None = None) -> None:
  t = _tf(tf)
  with _lock:
    save_config(tf=t, enabled=False)
    _stop_event(t).set()
    pid = load_config(t).get("service_pid") or _read_pid_file(t)
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
          os.kill(int(pid), signal.SIGKILL)
        except OSError:
          pass
      append_event("system", "service_stop", summary=f"killed process pid={pid} tf={t}")
    _clear_pid(t)
    write_status(bridge_dir_for(t, "live"), state="stopped", error=None)


def ensure_worker_running(tf: str | None = None) -> None:
  """On each GUI load — restart detached process if enabled but dead."""
  t = _tf(tf)
  cfg = load_config(t)
  if not cfg.get("enabled"):
    return
  if is_running(t):
    return
  if (cfg.get("mode") or "process") == "thread":
    start_thread_worker(t)
  else:
    start_process_worker(t)


def process_once_now(tf: str | None = None) -> dict | None:
  t = _tf(tf)
  cfg = load_config(t)
  bridge_dir = ensure_bridge_dir(Path(cfg["bridge_dir"]))
  engine = BridgeEngine(
    model_id=cfg["model_id"], risk_pct=float(cfg["risk_pct"]), bridge_dir=bridge_dir, tf=t,
  )
  process_history_sync(bridge_dir, tf=t)
  engine.ensure_history()
  _cycle(engine, bridge_dir, None, None)
  return engine._last_decision


# --- Simulate EA worker: detached process (like Live) so Streamlit stays smooth ---

_sim_threads: dict[str, threading.Thread] = {}
_sim_bridge_threads: dict[str, threading.Thread] = {}
_sim_stops: dict[str, threading.Event] = {}
_sim_pauses: dict[str, threading.Event] = {}
_sim_lock = threading.Lock()


def _sim_stop_event(tf: str) -> threading.Event:
  return _sim_stops.setdefault(tf, threading.Event())


def _sim_pause_event(tf: str) -> threading.Event:
  return _sim_pauses.setdefault(tf, threading.Event())


def _read_sim_pid(tf: str | None = None) -> int | None:
  path = sim_pid_path(tf)
  if not path.exists():
    return None
  try:
    return int(path.read_text(encoding="utf-8").strip())
  except Exception:
    return None


def _clear_sim_pid(tf: str | None = None) -> None:
  try:
    path = sim_pid_path(tf)
    if path.exists():
      path.unlink()
  except Exception:
    pass


def is_sim_process_running(tf: str | None = None) -> bool:
  return _pid_alive(_read_sim_pid(tf))


def is_sim_thread_running(tf: str | None = None) -> bool:
  t = _tf(tf)
  thr = _sim_threads.get(t)
  return thr is not None and thr.is_alive()


def is_sim_running(tf: str | None = None) -> bool:
  t = _tf(tf)
  return is_sim_process_running(t) or is_sim_thread_running(t)


def get_sim_status(tf: str | None = None) -> dict:
  from mt5_bridge.ea_simulator import load_sim_state, sync_state_from_ea

  t = _tf(tf)
  sim_dir = bridge_dir_for(t, "sim")

  # Short TTL cache — Streamlit fragments must not hammer disk every redraw
  now = time.time()
  cache = getattr(get_sim_status, "_cache", None) or {}
  cached = cache.get(t)
  if isinstance(cached, tuple) and (now - cached[0]) < 0.4:
    return dict(cached[1])

  # Always mirror sim_control.json (EA updates bars_done/last_bar even if PID
  # detection briefly lags after Start — otherwise UI looks frozen until Refresh).
  try:
    st = sync_state_from_ea(sim_dir, persist=False)
  except Exception:
    st = load_sim_state(sim_dir)
  st["running"] = is_sim_running(t)
  # Brief PID lag after Start: EA already wrote enabled/running to sim_control
  ea_st = str(st.get("ea_status") or "")
  if not st["running"] and (ea_st == "running" or bool(st.get("enabled"))):
    st["running"] = True
  st["runtime"] = "process" if is_sim_process_running(t) else (
    "thread" if is_sim_thread_running(t) else st.get("runtime")
  )
  st["service_pid"] = _read_sim_pid(t) if is_sim_process_running(t) else st.get("service_pid")
  # Pause = sim_control.enabled false while process still alive
  try:
    from mt5_bridge.protocol import read_sim_control
    ctrl = read_sim_control(sim_dir) or {}
    st["paused"] = bool(st["running"] and not ctrl.get("enabled") and ctrl.get("request_id"))
  except Exception:
    st["paused"] = bool(_sim_pause_event(t).is_set()) if is_sim_thread_running(t) else False
  cache[t] = (now, dict(st))
  get_sim_status._cache = cache
  return st


def _run_sim_bridge_loop(
  stop_event: threading.Event, model_id: str | None, risk_pct: float, tf: str | None = None,
) -> None:
  """BridgeEngine cycle on bridge_sim while EA feeds bars."""
  t = _tf(tf)
  bridge_dir = ensure_bridge_dir(bridge_dir_for(t, "sim"))
  cache_path = cache_path_for(t)
  mid = model_id or load_config(t).get("model_id")
  engine = BridgeEngine(model_id=mid, risk_pct=float(risk_pct), bridge_dir=bridge_dir, tf=t)
  try:
    if cache_path.exists():
      engine.ensure_history()
      print(
        f"[sim-bridge:{t}] canonical history bars={len(engine.load())} "
        f"fp={engine.conditions_fp}",
        flush=True,
      )
  except Exception as e:
    print(f"[sim-bridge:{t}] ensure_history failed: {e}", flush=True)
  last_bar_fp = None
  last_fill_fp = None
  while not stop_event.is_set():
    try:
      last_bar_fp, last_fill_fp = _cycle(engine, bridge_dir, last_bar_fp, last_fill_fp)
    except MemoryError as e:
      msg = f"sim_bridge MemoryError: {e}"
      print(f"[sim-bridge:{t}] {msg}", flush=True)
      try:
        from mt5_bridge.ea_simulator import write_sim_state
        write_sim_state({"error": msg, "status": "error"}, bridge_dir)
        write_status(
          bridge_dir,
          state="error",
          error=msg,
          **_engine_status_fields(engine),
        )
      except Exception:
        pass
      # Drop FeatureMatrix only — keep weekly strat cache (avoid mid-week remine drift)
      try:
        engine._fm = None
        engine._fm_key = None
      except Exception:
        pass
      time.sleep(1.0)
    except Exception as e:
      try:
        write_status(
          bridge_dir,
          state="error",
          error=f"sim_bridge: {e}",
          **_engine_status_fields(engine),
        )
      except Exception:
        pass
      print(f"[sim-bridge:{t}] cycle error: {e}", flush=True)
      time.sleep(0.2)
    # Tight poll so HistoryFeed delay_ms is not dominated by App lag
    time.sleep(0.03)


def start_sim_worker(
  *,
  date_from: str,
  date_to: str,
  delay_ms: int = 100,
  model_id: str | None = None,
  risk_pct: float = 1.0,
  tf: str | None = None,
  detached: bool = True,
) -> bool:
  """Start HISTORY_FEED control + bridge_sim decide loop.

  Default = detached OS process (GUI stays smooth, like Live service).
  """
  t = _tf(tf)
  with _sim_lock:
    if is_sim_running(t):
      return False
    from mt5_bridge.ea_simulator import SimConfig, run_history_feed_control, write_sim_state

    sim_dir = bridge_dir_for(t, "sim")
    mid = model_id or load_config(t).get("model_id")
    delay = max(1, int(delay_ms))

    if detached:
      report_dir = _report_dir(t)
      report_dir.mkdir(parents=True, exist_ok=True)
      cmd = [
        sys.executable,
        str(SIM_SERVICE_SCRIPT),
        "--tf", t,
        "--from", str(date_from),
        "--to", str(date_to),
        "--delay-ms", str(delay),
        "--risk-pct", str(float(risk_pct)),
        "--bridge-dir", str(sim_dir),
      ]
      if mid:
        cmd.extend(["--model-id", str(mid)])
      log_path = sim_service_log_path(t)
      logf = open(log_path, "a", encoding="utf-8")
      logf.write(f"\n--- start {_now_iso()} tf={t} ---\n")
      logf.flush()
      proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=logf,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
      )
      sim_pid_path(t).write_text(str(proc.pid), encoding="utf-8")
      write_sim_state({
        "status": "running",
        "runtime": "process",
        "service_pid": proc.pid,
        "model_id": mid,
        "date_from": date_from,
        "date_to": date_to,
        "delay_ms": delay,
        "error": None,
      }, sim_dir)
      return True

    # Fallback: in-process threads (dev only — blocks Streamlit when remine)
    stop_event = _sim_stop_event(t)
    pause_event = _sim_pause_event(t)
    stop_event.clear()
    pause_event.clear()
    cfg = SimConfig(
      date_from=date_from,
      date_to=date_to,
      delay_ms=delay,
      model_id=mid,
      risk_pct=float(risk_pct),
      bridge_dir=sim_dir,
    )

    def _run_control():
      try:
        run_history_feed_control(
          cfg,
          stop_event=stop_event,
          pause_event=pause_event,
        )
      except Exception as e:
        write_sim_state({"status": "error", "error": str(e)}, sim_dir)
      finally:
        stop_event.set()

    bridge_thread = threading.Thread(
      target=_run_sim_bridge_loop,
      args=(stop_event, mid, float(risk_pct), t),
      name=f"ea-history-bridge-{t.lower()}",
      daemon=True,
    )
    bridge_thread.start()
    _sim_bridge_threads[t] = bridge_thread
    ctrl_thread = threading.Thread(
      target=_run_control, name=f"ea-history-control-{t.lower()}", daemon=True,
    )
    ctrl_thread.start()
    _sim_threads[t] = ctrl_thread
    write_sim_state({"status": "running", "runtime": "thread", "model_id": mid}, sim_dir)
    return True


def pause_sim_worker(paused: bool = True, tf: str | None = None) -> None:
  """Pause/resume via sim_control.enabled (works for detached process)."""
  from mt5_bridge.ea_simulator import write_sim_state
  from mt5_bridge.protocol import read_sim_control, write_sim_control

  t = _tf(tf)
  sim_dir = bridge_dir_for(t, "sim")
  ctrl = read_sim_control(sim_dir) or {}
  if paused:
    write_sim_control(sim_dir, enabled=False)
    write_sim_state({"status": "paused"}, sim_dir)
    _sim_pause_event(t).set()
  else:
    write_sim_control(
      sim_dir,
      enabled=True,
      request_id=ctrl.get("request_id"),
      **{
        k: ctrl[k]
        for k in ("from", "to", "delay_ms")
        if ctrl.get(k) is not None
      },
    )
    write_sim_state({"status": "running"}, sim_dir)
    _sim_pause_event(t).clear()


def stop_sim_worker(tf: str | None = None) -> None:
  t = _tf(tf)
  stop_event = _sim_stop_event(t)
  stop_event.set()
  _sim_pause_event(t).clear()
  from mt5_bridge.ea_simulator import stop_history_feed_control, write_sim_state

  sim_dir = bridge_dir_for(t, "sim")
  try:
    stop_history_feed_control(sim_dir)
  except Exception:
    pass

  pid = _read_sim_pid(t)
  if _pid_alive(pid):
    try:
      os.kill(int(pid), signal.SIGTERM)
    except OSError:
      pass
    for _ in range(40):
      if not _pid_alive(pid):
        break
      time.sleep(0.1)
    if _pid_alive(pid):
      try:
        os.kill(int(pid), signal.SIGKILL)
      except OSError:
        pass
  _clear_sim_pid(t)

  for store in (_sim_threads, _sim_bridge_threads):
    th = store.get(t)
    if th and th.is_alive():
      th.join(timeout=5.0)
    store.pop(t, None)
  write_sim_state({"status": "stopped", "service_pid": None}, sim_dir)


def reset_sim_data(tf: str | None = None) -> dict:
  """Stop feed if running, then wipe bridge_sim artifacts for a clean rerun."""
  t = _tf(tf)
  if is_sim_running(t):
    stop_sim_worker(t)
  from mt5_bridge.ea_simulator import reset_sim_data as _reset

  return _reset(bridge_dir_for(t, "sim"))
