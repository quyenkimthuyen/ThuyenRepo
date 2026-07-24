#!/usr/bin/env python3
"""
Poll mt5/bridge/bar.json from ForgeBridge EA, decide with Best 3m, write decision.json.

Usage:
  python scripts/mt5_bridge_service.py
  python scripts/mt5_bridge_service.py --once
"""
from __future__ import annotations

import argparse
import atexit
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mt5_bridge.comm_log import append_event
from mt5_bridge.engine import BridgeEngine
from mt5_bridge.history_sync import (
  MT5_CACHE_PATH,
  process_history_sync,
  start_history_sync,
)
from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT, start_live_monitor_server
from mt5_bridge.models import load_active_model_id
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  DEFAULT_MAGIC,
  DEFAULT_MODEL_ID,
  DEFAULT_TIMEFRAME,
  INSTANCE_ID,
  atomic_write_json,
  bar_path,
  decision_path,
  ensure_bridge_dir,
  fill_path,
  read_json,
  write_status,
)
from mt5_bridge.trade_journal import process_fill


def _register_service_process(args) -> None:
  """Persist PID/config and provide output handles for pythonw on Windows."""
  from mt5_bridge.background import PID_PATH, SERVICE_LOG, load_config, save_config

  if sys.stdout is None or sys.stderr is None:
    SERVICE_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = open(SERVICE_LOG, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
      sys.stdout = log
    if sys.stderr is None:
      sys.stderr = log

  active_model_id = load_active_model_id()
  if active_model_id:
    args.model_id = active_model_id
  pid = os.getpid()
  PID_PATH.write_text(str(pid), encoding="utf-8")
  save_config(
    enabled=True,
    mode="process",
    service_pid=pid,
    bridge_dir=str(args.bridge_dir),
    model_id=args.model_id,
    risk_pct=args.risk_pct,
    poll_sec=args.poll,
    last_error=None,
  )

  def _cleanup() -> None:
    try:
      cfg = load_config()
      if int(cfg.get("service_pid") or 0) == pid:
        save_config(service_pid=None)
      if PID_PATH.exists() and PID_PATH.read_text(encoding="utf-8").strip() == str(pid):
        PID_PATH.unlink()
    except Exception:
      pass

  atexit.register(_cleanup)



def _bar_fingerprint(bar: dict | None) -> str | None:
  if not isinstance(bar, dict):
    return None
  return str(
    bar.get("time")
    or bar.get("bar_time")
    or bar.get("time_msc")
    or ""
  )


def _identity_matches(payload: dict | None) -> bool:
  return bool(
    isinstance(payload, dict)
    and payload.get("period") == DEFAULT_TIMEFRAME
    and payload.get("instance_id") == INSTANCE_ID
    and int(payload.get("magic") or 0) == DEFAULT_MAGIC
  )


def process_once(engine: BridgeEngine, bridge_dir: Path, *, last_fp: str | None, last_fill_fp: str | None = None):
  fill = read_json(fill_path(bridge_dir))
  if isinstance(fill, dict):
    if not _identity_matches(fill):
      write_status(
        bridge_dir, state="identity_error", model_id=engine.model_id,
        error=f"Rejected fill from {fill.get('instance_id')}/{fill.get('period')}/{fill.get('magic')}",
      )
      fill = None
  if isinstance(fill, dict):
    ffp = str(fill.get("signal_id") or "") + "|" + str(fill.get("time") or "") + "|" + str(fill.get("event") or fill.get("detail") or "")
    if ffp and ffp != last_fill_fp:
      append_event(
        "ea_to_app", "fill_received", bridge_dir=bridge_dir, payload=fill,
        summary=f"fill {fill.get('event') or fill.get('action')} ok={fill.get('ok')} sid={fill.get('signal_id')}",
      )
      process_fill(
        fill,
        bridge_dir=bridge_dir,
        decision=engine._last_decision if isinstance(engine._last_decision, dict) else None,
        model_id=engine.model_id,
      )
      last_fill_fp = ffp

  path = bar_path(bridge_dir)
  bar = read_json(path)
  if not isinstance(bar, dict):
    write_status(
      bridge_dir,
      state="waiting_bar",
      model_id=engine.model_id,
      error=None,
      last_bar=None,
    )
    return last_fp, last_fill_fp
  if not _identity_matches(bar):
    write_status(
      bridge_dir, state="identity_error", model_id=engine.model_id,
      error=f"Rejected bar from {bar.get('instance_id')}/{bar.get('period')}/{bar.get('magic')}",
    )
    return last_fp, last_fill_fp

  fp = _bar_fingerprint(bar)
  if not fp:
    write_status(bridge_dir, state="bad_bar", model_id=engine.model_id, error="bar missing time")
    return last_fp, last_fill_fp

  if fp == last_fp:
    write_status(
      bridge_dir,
      state="idle",
      model_id=engine.model_id,
      last_bar=fp,
      last_action=(engine._last_decision or {}).get("action"),
      week_start=(engine._last_decision or {}).get("week_start"),
      error=None,
    )
    return last_fp, last_fill_fp

  append_event(
    "ea_to_app", "bar_received", bridge_dir=bridge_dir,
    payload={"symbol": bar.get("symbol"), "time": bar.get("time") or bar.get("bar_time"), "close": bar.get("close")},
    summary=f"bar {bar.get('symbol')} {bar.get('time') or bar.get('bar_time')} c={bar.get('close')}",
  )
  decision = engine.decide_for_bar(bar)
  atomic_write_json(decision_path(bridge_dir), decision)
  append_event(
    "app_to_ea", "decision_sent", bridge_dir=bridge_dir,
    payload={
      "action": decision.get("action"), "bar_time": decision.get("bar_time"),
      "reason": decision.get("reason"), "signal_id": decision.get("signal_id"),
    },
    summary=f"decision {decision.get('action')} bar={decision.get('bar_time')} reason={decision.get('reason')}",
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
  try:
    from mt5_bridge.background import save_config
    save_config(
      last_run_at=decision.get("updated_at"),
      last_action=decision.get("action"),
      last_bar=fp,
      last_error=None,
    )
  except Exception:
    pass
  print(
    f"[bridge] bar={decision.get('bar_time')} action={decision.get('action')} "
    f"reason={decision.get('reason')} strat={decision.get('strategy_name')}",
    flush=True,
  )
  return fp, last_fill_fp


def main() -> int:
  ap = argparse.ArgumentParser(description="MT5 bridge decision service")
  ap.add_argument("--bridge-dir", type=Path, default=BRIDGE_DIR)
  ap.add_argument("--model-id", default=DEFAULT_MODEL_ID)
  ap.add_argument("--risk-pct", type=float, default=1.0)
  ap.add_argument("--poll", type=float, default=2.0, help="seconds between polls")
  ap.add_argument("--monitor-port", type=int, default=DEFAULT_MONITOR_PORT)
  ap.add_argument("--once", action="store_true", help="process one bar then exit")
  ap.add_argument("--seed", action="store_true", help="force a full MT5 EA history sync")
  args = ap.parse_args()
  if not args.once:
    _register_service_process(args)

  bridge_dir = ensure_bridge_dir(args.bridge_dir)
  monitor_server = None
  if not args.once:
    try:
      monitor_server = start_live_monitor_server(bridge_dir, args.monitor_port)
      atexit.register(monitor_server.shutdown)
      print(f"[bridge] live monitor=http://127.0.0.1:{args.monitor_port}", flush=True)
    except OSError as e:
      print(f"[bridge] live monitor unavailable: {e}", flush=True)
  engine = BridgeEngine(model_id=args.model_id, risk_pct=args.risk_pct)
  print(f"[bridge] dir={bridge_dir} model={engine.model_id}", flush=True)
  start_history_sync(bridge_dir, force=args.seed)
  try:
    engine.ensure_history()
    print(f"[bridge] history bars={len(engine.load())}", flush=True)
  except Exception as e:
    print(f"[bridge] waiting for MT5 history: {e}", flush=True)

  write_status(bridge_dir, state="running", model_id=engine.model_id, error=None)
  last_fp: str | None = None
  last_fill_fp: str | None = None
  while True:
    try:
      history = process_history_sync(bridge_dir)
      if not MT5_CACHE_PATH.exists():
        write_status(
          bridge_dir, state="syncing_history", model_id=engine.model_id,
          history=history, error=None,
        )
        if args.once:
          return 0
        time.sleep(max(0.2, args.poll))
        continue
      if not args.once:
        from mt5_bridge.background import load_config
        runtime_cfg = load_config()
        desired_model = load_active_model_id() or runtime_cfg.get("model_id") or engine.model_id
        desired_risk = float(runtime_cfg.get("risk_pct", engine.risk_pct))
        args.poll = float(runtime_cfg.get("poll_sec", args.poll))
        if desired_model != engine.model_id or abs(desired_risk - engine.risk_pct) > 1e-9:
          engine = BridgeEngine(model_id=desired_model, risk_pct=desired_risk)
          engine.ensure_history()
          last_fp = None
          append_event(
            "system", "engine_reload", bridge_dir=bridge_dir,
            summary=f"model={desired_model} risk={desired_risk}",
          )
          write_status(
            bridge_dir, state="running", model_id=desired_model,
            error=None, reason="config_reload",
          )
      last_fp, last_fill_fp = process_once(
        engine, bridge_dir, last_fp=last_fp, last_fill_fp=last_fill_fp,
      )
    except Exception as e:
      write_status(
        bridge_dir,
        state="error",
        model_id=engine.model_id,
        error=str(e),
        traceback=traceback.format_exc()[-2000:],
      )
      append_event("system", "error", bridge_dir=bridge_dir, summary=str(e))
      print(f"[bridge] ERROR: {e}", flush=True)
      if args.once:
        return 1
    if args.once:
      return 0
    time.sleep(max(0.2, args.poll))


if __name__ == "__main__":
  raise SystemExit(main())
