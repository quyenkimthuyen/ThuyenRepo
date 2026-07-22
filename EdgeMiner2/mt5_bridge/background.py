"""Background worker — MT5 bridge decision service (GUI-controllable).

Default Start = detached OS process (`scripts/mt5_bridge_service.py`) so it
survives Streamlit tab switches and page refresh. Thread mode is fallback only.
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

from mt5_bridge.comm_log import append_event
from mt5_bridge.engine import BridgeEngine
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  DEFAULT_MODEL_ID,
  atomic_write_json,
  bar_path,
  decision_path,
  ensure_bridge_dir,
  fill_path,
  read_json,
  write_status,
)
from mt5_bridge.trade_journal import process_fill
from run_backtest import REPORT_DIR

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPORT_DIR / "mt5_bridge_config.json"
PID_PATH = REPORT_DIR / "mt5_bridge_service.pid"
SERVICE_LOG = REPORT_DIR / "mt5_bridge_service.log"
SERVICE_SCRIPT = ROOT / "scripts" / "mt5_bridge_service.py"

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop = threading.Event()
_engine: BridgeEngine | None = None


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
  tmp.replace(path)


def load_config() -> dict:
  data = _read_json(CONFIG_PATH) or {}
  return {
    "enabled": bool(data.get("enabled", False)),
    "model_id": data.get("model_id") or DEFAULT_MODEL_ID,
    "risk_pct": float(data.get("risk_pct", 1.0)),
    "poll_sec": float(data.get("poll_sec", 2.0)),
    "bridge_dir": data.get("bridge_dir") or str(BRIDGE_DIR),
    "mode": data.get("mode") or "process",
    "service_pid": data.get("service_pid"),
    "last_run_at": data.get("last_run_at"),
    "last_error": data.get("last_error"),
    "last_action": data.get("last_action"),
    "last_bar": data.get("last_bar"),
  }


def save_config(**updates) -> dict:
  cfg = load_config()
  # Allow clearing nullable fields with None (e.g. service_pid)
  nullable = {"service_pid", "last_error", "last_action", "last_bar", "last_run_at"}
  for k, v in updates.items():
    if v is None and k not in nullable:
      continue
    cfg[k] = v
  _write_json(CONFIG_PATH, cfg)
  return cfg


def _pid_alive(pid: int | None) -> bool:
  if not pid:
    return False
  try:
    os.kill(int(pid), 0)
    return True
  except (OSError, TypeError, ValueError):
    return False


def _read_pid_file() -> int | None:
  if not PID_PATH.exists():
    return None
  try:
    return int(PID_PATH.read_text(encoding="utf-8").strip())
  except (OSError, ValueError):
    return None


def _clear_pid() -> None:
  save_config(service_pid=None)
  try:
    if PID_PATH.exists():
      PID_PATH.unlink()
  except OSError:
    pass


def is_process_running() -> bool:
  cfg = load_config()
  pid = cfg.get("service_pid") or _read_pid_file()
  if _pid_alive(pid):
    return True
  if cfg.get("service_pid") or PID_PATH.exists():
    _clear_pid()
  return False


def is_thread_running() -> bool:
  return _thread is not None and _thread.is_alive() and not _stop.is_set()


def is_running() -> bool:
  return is_process_running() or is_thread_running()


def get_status() -> dict:
  cfg = load_config()
  proc = is_process_running()
  thr = is_thread_running()
  pid = cfg.get("service_pid") or _read_pid_file()
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
    + str(fill.get("time") or "")
    + "|"
    + str(fill.get("event") or fill.get("detail") or "")
    + "|"
    + str(fill.get("ticket") or "")
  )


def _cycle(engine: BridgeEngine, bridge_dir: Path, last_bar_fp: str | None, last_fill_fp: str | None):
  fill = read_json(fill_path(bridge_dir))
  fp_fill = _fill_fp(fill if isinstance(fill, dict) else None)
  if fp_fill and fp_fill != last_fill_fp and isinstance(fill, dict):
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
    last_fill_fp = fp_fill
    save_config(last_run_at=_now_iso())

  bar = read_json(bar_path(bridge_dir))
  if not isinstance(bar, dict):
    write_status(bridge_dir, state="waiting_bar", model_id=engine.model_id, error=None)
    return last_bar_fp, last_fill_fp

  fp = _bar_fp(bar)
  if not fp:
    write_status(bridge_dir, state="bad_bar", model_id=engine.model_id, error="bar missing time")
    return last_bar_fp, last_fill_fp

  if fp == last_bar_fp:
    write_status(
      bridge_dir,
      state="idle",
      model_id=engine.model_id,
      last_bar=fp,
      last_action=(engine._last_decision or {}).get("action"),
      error=None,
    )
    return last_bar_fp, last_fill_fp

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
    model_id=engine.model_id,
    last_bar=fp,
    last_action=decision.get("action"),
    reason=decision.get("reason"),
    week_start=decision.get("week_start"),
    strategy_name=decision.get("strategy_name"),
    error=None,
  )
  save_config(
    last_run_at=_now_iso(),
    last_action=decision.get("action"),
    last_bar=fp,
    last_error=None,
  )
  return fp, last_fill_fp


def _worker():
  global _engine
  cfg = load_config()
  bridge_dir = ensure_bridge_dir(Path(cfg["bridge_dir"]))
  append_event("system", "service_start", bridge_dir=bridge_dir, summary="bridge thread started")
  try:
    _engine = BridgeEngine(model_id=cfg["model_id"], risk_pct=cfg["risk_pct"])
    _engine.seed_from_dukascopy()
    write_status(bridge_dir, state="running", model_id=_engine.model_id, error=None, runtime="thread")
  except Exception as e:
    save_config(last_error=str(e), enabled=False)
    append_event(
      "system", "error", bridge_dir=bridge_dir, summary=str(e),
      payload={"tb": traceback.format_exc()[-1500:]},
    )
    write_status(bridge_dir, state="error", model_id=cfg["model_id"], error=str(e))
    return

  last_bar_fp = None
  last_fill_fp = None
  while not _stop.is_set():
    cfg = load_config()
    if not cfg.get("enabled"):
      break
    poll = max(0.3, float(cfg.get("poll_sec") or 2.0))
    try:
      if _engine and (
        _engine.model_id != cfg["model_id"]
        or abs(_engine.risk_pct - float(cfg["risk_pct"])) > 1e-9
      ):
        _engine = BridgeEngine(model_id=cfg["model_id"], risk_pct=float(cfg["risk_pct"]))
        _engine.seed_from_dukascopy()
        append_event(
          "system", "engine_reload", bridge_dir=bridge_dir,
          summary=f"model={cfg['model_id']} risk={cfg['risk_pct']}",
        )
      last_bar_fp, last_fill_fp = _cycle(_engine, bridge_dir, last_bar_fp, last_fill_fp)
    except Exception as e:
      save_config(last_error=str(e), last_run_at=_now_iso())
      append_event(
        "system", "error", bridge_dir=bridge_dir,
        summary=str(e), payload={"tb": traceback.format_exc()[-1500:]},
      )
      write_status(bridge_dir, state="error", model_id=cfg["model_id"], error=str(e))
    _stop.wait(poll)

  append_event("system", "service_stop", bridge_dir=bridge_dir, summary="bridge thread stopped")
  write_status(bridge_dir, state="stopped", model_id=cfg.get("model_id"), error=None)


def start_thread_worker() -> bool:
  global _thread
  with _lock:
    if is_process_running() or is_thread_running():
      return True
    save_config(enabled=True, mode="thread")
    _stop.clear()
    _thread = threading.Thread(target=_worker, name="mt5-bridge", daemon=True)
    _thread.start()
    return True


def start_process_worker() -> bool:
  """Detached CLI process — survives GUI tab switch / page refresh."""
  with _lock:
    if is_process_running():
      save_config(enabled=True, mode="process")
      return True
    _stop.set()
    cfg = load_config()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
      sys.executable,
      str(SERVICE_SCRIPT),
      "--model-id", str(cfg.get("model_id") or DEFAULT_MODEL_ID),
      "--risk-pct", str(cfg.get("risk_pct") or 1.0),
      "--poll", str(cfg.get("poll_sec") or 2.0),
      "--bridge-dir", str(cfg.get("bridge_dir") or BRIDGE_DIR),
    ]
    logf = open(SERVICE_LOG, "a", encoding="utf-8")
    logf.write(f"\n--- start {_now_iso()} ---\n")
    logf.flush()
    proc = subprocess.Popen(
      cmd,
      cwd=str(ROOT),
      stdout=logf,
      stderr=subprocess.STDOUT,
      start_new_session=True,
      close_fds=True,
    )
    PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    save_config(enabled=True, mode="process", service_pid=proc.pid, last_error=None)
    append_event(
      "system", "service_start",
      summary=f"detached process pid={proc.pid}",
      payload={"pid": proc.pid},
    )
    write_status(
      Path(cfg.get("bridge_dir") or BRIDGE_DIR),
      state="running",
      model_id=cfg.get("model_id"),
      runtime="process",
      pid=proc.pid,
      error=None,
    )
    return True


def start_worker(*, detached: bool = True) -> bool:
  """Default: detached process (safe across Streamlit refresh)."""
  if detached:
    return start_process_worker()
  return start_thread_worker()


def stop_worker() -> None:
  with _lock:
    save_config(enabled=False)
    _stop.set()
    pid = load_config().get("service_pid") or _read_pid_file()
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
      append_event("system", "service_stop", summary=f"killed process pid={pid}")
    _clear_pid()
    write_status(BRIDGE_DIR, state="stopped", error=None)


def ensure_worker_running() -> None:
  """On each GUI load — restart detached process if enabled but dead."""
  cfg = load_config()
  if not cfg.get("enabled"):
    return
  if is_running():
    return
  if (cfg.get("mode") or "process") == "thread":
    start_thread_worker()
  else:
    start_process_worker()


def process_once_now() -> dict | None:
  cfg = load_config()
  bridge_dir = ensure_bridge_dir(Path(cfg["bridge_dir"]))
  engine = BridgeEngine(model_id=cfg["model_id"], risk_pct=float(cfg["risk_pct"]))
  engine.seed_from_dukascopy()
  _cycle(engine, bridge_dir, None, None)
  return engine._last_decision
