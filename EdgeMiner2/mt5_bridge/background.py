"""Background worker — MT5 bridge decision service (GUI-controllable)."""
from __future__ import annotations

import json
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

CONFIG_PATH = REPORT_DIR / "mt5_bridge_config.json"

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
    "last_run_at": data.get("last_run_at"),
    "last_error": data.get("last_error"),
    "last_action": data.get("last_action"),
    "last_bar": data.get("last_bar"),
  }


def save_config(**updates) -> dict:
  cfg = load_config()
  cfg.update({k: v for k, v in updates.items() if v is not None})
  _write_json(CONFIG_PATH, cfg)
  return cfg


def is_running() -> bool:
  return _thread is not None and _thread.is_alive() and not _stop.is_set()


def get_status() -> dict:
  cfg = load_config()
  return {
    **cfg,
    "running": is_running(),
    "thread_alive": _thread is not None and _thread.is_alive(),
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
  # Fills from EA → trade journal (open/close + R)
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
  append_event("system", "service_start", bridge_dir=bridge_dir, summary="bridge worker started")
  try:
    _engine = BridgeEngine(model_id=cfg["model_id"], risk_pct=cfg["risk_pct"])
    _engine.seed_from_dukascopy()
    write_status(bridge_dir, state="running", model_id=_engine.model_id, error=None)
  except Exception as e:
    save_config(last_error=str(e), enabled=False)
    append_event("system", "error", bridge_dir=bridge_dir, summary=str(e), payload={"tb": traceback.format_exc()[-1500:]})
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
      # Hot-reload model/risk if changed
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

  append_event("system", "service_stop", bridge_dir=bridge_dir, summary="bridge worker stopped")
  write_status(bridge_dir, state="stopped", model_id=cfg.get("model_id"), error=None)


def start_worker() -> bool:
  global _thread
  with _lock:
    if is_running():
      return True
    save_config(enabled=True)
    _stop.clear()
    _thread = threading.Thread(target=_worker, name="mt5-bridge", daemon=True)
    _thread.start()
    return True


def stop_worker() -> None:
  with _lock:
    save_config(enabled=False)
    _stop.set()


def ensure_worker_running() -> None:
  cfg = load_config()
  if cfg.get("enabled") and not is_running():
    start_worker()


def process_once_now() -> dict | None:
  """Manual single cycle (GUI button)."""
  cfg = load_config()
  bridge_dir = ensure_bridge_dir(Path(cfg["bridge_dir"]))
  engine = BridgeEngine(model_id=cfg["model_id"], risk_pct=float(cfg["risk_pct"]))
  engine.seed_from_dukascopy()
  last_bar, last_fill = _cycle(engine, bridge_dir, None, None)
  return engine._last_decision
