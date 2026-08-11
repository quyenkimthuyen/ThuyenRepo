#!/usr/bin/env python3
"""Live bridge decision service — remine from installed packages via lab host desk.

Usage:
  python scripts/mt5_bridge_service_live.py --symbol EURUSD --timeframe M5 --model-ids id1
  python scripts/mt5_bridge_service_live.py --once ...
"""
from __future__ import annotations

import argparse
import atexit
import os
import sys
import time
import traceback
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from live_config import BRIDGE_DIR, RESULTS_DIR  # noqa: E402
from materialize_models import materialize_enabled  # noqa: E402
from runtime_bootstrap import bootstrap_host  # noqa: E402
from safety import is_kill_switch_armed  # noqa: E402
from shared.constants import LIVE_BRIDGE_PORT, LIVE_MAGIC_BASE  # noqa: E402


def _register(args, model_ids: list[str]) -> None:
  from mt5_bridge.background import PID_PATH, SERVICE_LOG, save_config

  if sys.stdout is None or sys.stderr is None:
    SERVICE_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = open(SERVICE_LOG, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
      sys.stdout = log
    if sys.stderr is None:
      sys.stderr = log

  pid = os.getpid()
  PID_PATH.parent.mkdir(parents=True, exist_ok=True)
  PID_PATH.write_text(str(pid), encoding="utf-8")
  save_config(
    enabled=True,
    mode="process",
    service_pid=pid,
    bridge_dir=str(args.bridge_dir),
    model_id=model_ids[0] if model_ids else args.model_id,
    model_ids=model_ids,
    risk_pct=args.risk_pct,
    poll_sec=args.poll,
    symbol=args.symbol,
    timeframe=args.timeframe,
    last_error=None,
  )

  def _cleanup() -> None:
    try:
      from mt5_bridge.background import load_config, save_config as sc
      cfg = load_config()
      if int(cfg.get("service_pid") or 0) == pid:
        sc(service_pid=None)
      if PID_PATH.exists() and PID_PATH.read_text(encoding="utf-8").strip() == str(pid):
        PID_PATH.unlink()
    except Exception:
      pass

  atexit.register(_cleanup)


def main() -> int:
  ap = argparse.ArgumentParser(description="Live MT5 bridge remine service")
  ap.add_argument("--bridge-dir", type=Path, default=BRIDGE_DIR)
  ap.add_argument("--symbol", required=True)
  ap.add_argument("--timeframe", required=True)
  ap.add_argument("--model-id", default="")
  ap.add_argument("--model-ids", default=None)
  ap.add_argument("--risk-pct", type=float, default=1.0)
  ap.add_argument("--poll", type=float, default=2.0)
  ap.add_argument("--monitor-port", type=int, default=LIVE_BRIDGE_PORT)
  ap.add_argument("--once", action="store_true")
  ap.add_argument("--seed", action="store_true")
  args = ap.parse_args()

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  mat = materialize_enabled()
  if args.symbol != mat["symbol"] or args.timeframe != mat["timeframe"]:
    print(
      f"[live-bridge] WARN CLI {args.symbol}/{args.timeframe} vs roster "
      f"{mat['symbol']}/{mat['timeframe']} — using roster",
      flush=True,
    )
    args.symbol, args.timeframe = mat["symbol"], mat["timeframe"]

  desk = bootstrap_host(args.symbol, args.timeframe, force=True)
  print(f"[live-bridge] host={desk.name} symbol={args.symbol} tf={args.timeframe}", flush=True)

  from mt5_bridge.background import (  # noqa: WPS433
    _cycle,
    _engine_status_fields,
    build_engines,
    config_model_ids,
    load_config,
  )
  from mt5_bridge.comm_log import append_event
  from mt5_bridge.history_sync import (
    MT5_CACHE_PATH,
    process_history_sync,
    start_history_sync,
  )
  from mt5_bridge.live_monitor_server import start_live_monitor_server
  from mt5_bridge.protocol import (
    ensure_bridge_dir,
    normalize_model_ids,
    write_status,
  )

  cli_ids = normalize_model_ids(
    [x.strip() for x in str(args.model_ids).split(",")] if args.model_ids else None,
    fallback=args.model_id or (mat["model_ids"][0] if mat["model_ids"] else ""),
  )
  if not cli_ids:
    cli_ids = list(mat["model_ids"])
  if not cli_ids:
    print("[live-bridge] no models", flush=True)
    return 2

  if not args.once:
    _register(args, cli_ids)

  bridge_dir = ensure_bridge_dir(args.bridge_dir)
  monitor_server = None
  if not args.once:
    try:
      monitor_server = start_live_monitor_server(bridge_dir, args.monitor_port)
      atexit.register(monitor_server.shutdown)
      print(f"[live-bridge] monitor=http://127.0.0.1:{args.monitor_port}", flush=True)
    except OSError as e:
      print(f"[live-bridge] monitor unavailable: {e}", flush=True)

  engines = build_engines(
    cli_ids,
    risk_pct=float(args.risk_pct),
    bridge_dir=bridge_dir,
    base_magic=int(LIVE_MAGIC_BASE),
  )
  primary = next(iter(engines.values()), None)
  print(
    f"[live-bridge] dir={bridge_dir} models={list(engines.keys())} "
    f"risk={args.risk_pct} fp={primary.conditions_fp if primary else '-'}",
    flush=True,
  )
  start_history_sync(bridge_dir, force=args.seed)
  try:
    for eng in engines.values():
      eng.ensure_history()
    if primary:
      print(f"[live-bridge] history bars={len(primary.load())}", flush=True)
  except Exception as e:
    print(f"[live-bridge] waiting for MT5 history: {e}", flush=True)

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
      if is_kill_switch_armed():
        write_status(bridge_dir, state="halted", halt_source="kill_switch", error="kill_switch")
        print("[live-bridge] kill-switch armed — exiting", flush=True)
        return 0

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
          print("[live-bridge] --once but no MT5 cache yet", flush=True)
          return 0
        time.sleep(max(0.2, args.poll))
        continue

      if not args.once:
        runtime_cfg = load_config()
        if runtime_cfg.get("kill_switch") or not runtime_cfg.get("enabled", True):
          if not runtime_cfg.get("enabled", True) and not runtime_cfg.get("kill_switch"):
            write_status(bridge_dir, state="stopped", error=None)
            return 0
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
            base_magic=int(LIVE_MAGIC_BASE),
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

      # Loss guard (desk implementation)
      try:
        from mt5_bridge.background import check_and_apply_loss_guard
        check_and_apply_loss_guard(
          bridge_dir=bridge_dir,
          model_id=(primary.model_id if primary else None),
        )
        cfg_now = load_config()
        if cfg_now.get("loss_guard_tripped"):
          write_status(
            bridge_dir,
            state="halted",
            halt_source="loss_guard",
            error=cfg_now.get("loss_guard_tripped_reason"),
          )
          if args.once:
            return 0
          time.sleep(max(0.5, args.poll))
          continue
      except Exception as lg_exc:
        print(f"[live-bridge] loss_guard skip: {lg_exc}", flush=True)

      last_fp, last_fill_fp = _cycle(engines, bridge_dir, last_fp, last_fill_fp)
      write_status(
        bridge_dir,
        state="running",
        model_ids=list(engines.keys()),
        error=None,
        **_engine_status_fields(primary),
      )
      if args.once:
        return 0
    except Exception:
      err = traceback.format_exc()
      print(err, flush=True)
      write_status(bridge_dir, state="error", error=err[-500:])
      if args.once:
        return 1
    time.sleep(max(0.2, args.poll))


if __name__ == "__main__":
  raise SystemExit(main())
