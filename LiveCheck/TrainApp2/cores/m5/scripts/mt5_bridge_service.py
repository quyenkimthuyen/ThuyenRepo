#!/usr/bin/env python3
"""
Poll mt5/bridge/bar.json from ForgeBridge EA, decide with Trade Model(s), write decisions.

Usage:
  python scripts/mt5_bridge_service.py
  python scripts/mt5_bridge_service.py --once
  python scripts/mt5_bridge_service.py --model-ids id1,id2 --risk-pct 1.0
"""
from __future__ import annotations

import argparse
import atexit
import os
import sys
import time
import traceback
from pathlib import Path

from app_paths import get_root
ROOT = get_root()
sys.path.insert(0, str(ROOT))

from mt5_bridge.comm_log import append_event
from mt5_bridge.history_sync import (
  MT5_CACHE_PATH,
  process_history_sync,
  start_history_sync,
)
from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT, start_live_monitor_server
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  DEFAULT_MAGIC,
  DEFAULT_MODEL_ID,
  ensure_bridge_dir,
  normalize_model_ids,
  write_status,
)


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

  ids = normalize_model_ids(
    getattr(args, "model_ids", None),
    fallback=args.model_id or DEFAULT_MODEL_ID,
  )
  pid = os.getpid()
  PID_PATH.write_text(str(pid), encoding="utf-8")
  save_config(
    enabled=True,
    mode="process",
    service_pid=pid,
    bridge_dir=str(args.bridge_dir),
    model_id=ids[0] if ids else args.model_id,
    model_ids=ids,
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


def main() -> int:
  from mt5_bridge.background import (
    _cycle,
    _engine_status_fields,
    build_engines,
    config_model_ids,
    load_config,
  )

  ap = argparse.ArgumentParser(description="MT5 bridge decision service")
  ap.add_argument("--bridge-dir", type=Path, default=BRIDGE_DIR)
  ap.add_argument("--model-id", default=DEFAULT_MODEL_ID)
  ap.add_argument(
    "--model-ids",
    default=None,
    help="Comma-separated trade model ids (multi-model Live)",
  )
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

  cli_ids = normalize_model_ids(
    [x.strip() for x in str(args.model_ids).split(",")] if args.model_ids else None,
    fallback=args.model_id,
  )
  engines = build_engines(
    cli_ids,
    risk_pct=float(args.risk_pct),
    bridge_dir=bridge_dir,
    base_magic=DEFAULT_MAGIC,
  )
  primary = next(iter(engines.values()), None)
  print(
    f"[bridge] dir={bridge_dir} models={list(engines.keys())} "
    f"risk={args.risk_pct} fp={primary.conditions_fp if primary else '-'}",
    flush=True,
  )
  start_history_sync(bridge_dir, force=args.seed)
  try:
    for eng in engines.values():
      eng.ensure_history()
    if primary:
      print(f"[bridge] history bars={len(primary.load())}", flush=True)
  except Exception as e:
    print(f"[bridge] waiting for MT5 history: {e}", flush=True)

  write_status(
    bridge_dir,
    state="running",
    model_ids=list(engines.keys()),
    error=None,
    **_engine_status_fields(primary),
  )
  last_fp: str | None = None
  last_fill_fp: str | None = None
  while True:
    try:
      history = process_history_sync(bridge_dir)
      if not MT5_CACHE_PATH.exists():
        write_status(
          bridge_dir,
          state="syncing_history",
          model_ids=list(engines.keys()),
          history=history,
          error=None,
          **_engine_status_fields(primary),
        )
        if args.once:
          return 0
        time.sleep(max(0.2, args.poll))
        continue
      if not args.once:
        runtime_cfg = load_config()
        desired_ids = config_model_ids(runtime_cfg) or list(engines.keys())
        desired_risk = float(runtime_cfg.get("risk_pct", args.risk_pct))
        args.poll = float(runtime_cfg.get("poll_sec", args.poll))
        cur_ids = list(engines.keys())
        risk_changed = any(
          abs(e.risk_pct - desired_risk) > 1e-9 for e in engines.values()
        )
        if cur_ids != desired_ids or risk_changed:
          engines = build_engines(
            desired_ids,
            risk_pct=desired_risk,
            bridge_dir=bridge_dir,
            base_magic=DEFAULT_MAGIC,
            existing_engines=engines,
          )
          primary = next(iter(engines.values()), None)
          for eng in engines.values():
            eng.ensure_history()
          last_fp = None
          append_event(
            "system", "engine_reload", bridge_dir=bridge_dir,
            summary=f"models={desired_ids} risk={desired_risk}",
          )
          write_status(
            bridge_dir,
            state="running",
            model_ids=list(engines.keys()),
            error=None,
            reason="config_reload",
            **_engine_status_fields(primary),
          )
        else:
          for eng in engines.values():
            if eng.refresh_model():
              last_fp = None
              append_event(
                "system", "engine_reload", bridge_dir=bridge_dir,
                summary=f"conditions_fp={eng.conditions_fp} model={eng.model_id}",
                payload=eng.describe_conditions(),
              )
      last_fp, last_fill_fp = _cycle(
        engines, bridge_dir, last_fp, last_fill_fp,
      )
      if not args.once:
        if not load_config().get("enabled", True):
          print("[bridge] enabled=false — exiting (loss guard or Stop)", flush=True)
          write_status(
            bridge_dir,
            state="stopped",
            model_id=primary.model_id if primary else None,
            model_ids=list(engines.keys()),
            error=None,
          )
          return 0
    except Exception as e:
      write_status(
        bridge_dir,
        state="error",
        model_id=primary.model_id if primary else None,
        model_ids=list(engines.keys()),
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
