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
from debug_log import (  # noqa: E402
  check_pending_signal_timeouts,
  install_comm_log_mirror,
  log_ea_sync_if_changed,
  log_event,
  prune_old_logs,
)
from shared.constants import (  # noqa: E402
  LIVE_BRIDGE_PORT,
  LIVE_MAGIC_BASE,
  LIVE_SIM_MAGIC_BASE,
  LIVE_SIM_PORT,
)


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
    # Do not overwrite global union model_ids — each book worker has its own set.
    # Keep last_error clear; leave model_ids to bridge_control.start_bridge.
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
  ap.add_argument("--poll", type=float, default=0.5)
  ap.add_argument("--monitor-port", type=int, default=None)
  ap.add_argument("--once", action="store_true")
  ap.add_argument("--seed", action="store_true")
  ap.add_argument(
    "--sim",
    action="store_true",
    help="Sim/replay mode: sim magics, skip EA history wait, treat bridge as sim",
  )
  args = ap.parse_args()
  if args.monitor_port is None:
    args.monitor_port = LIVE_SIM_PORT if args.sim else LIVE_BRIDGE_PORT

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  mat = materialize_enabled()
  groups = mat.get("groups") or []
  match = [
    g for g in groups
    if str(g.get("symbol")) == str(args.symbol)
    and str(g.get("timeframe")) == str(args.timeframe)
  ]
  if not match and groups:
    print(
      f"[live-bridge] WARN no group for CLI {args.symbol}/{args.timeframe}; "
      f"available={[ (g['symbol'], g['timeframe']) for g in groups ]}",
      flush=True,
    )
  book_ids = list(match[0]["model_ids"]) if match else list(mat.get("model_ids") or [])

  desk = bootstrap_host(args.symbol, args.timeframe, force=True)
  print(
    f"[live-bridge] host={desk.name} symbol={args.symbol} tf={args.timeframe} "
    f"sim={bool(args.sim)}",
    flush=True,
  )

  prune_old_logs()
  log_event(
    "worker_start",
    summary=f"start {args.symbol} {args.timeframe} sim={bool(args.sim)}",
    payload={
      "model_ids": book_ids,
      "risk_pct": args.risk_pct,
      "poll": args.poll,
      "sim": bool(args.sim),
      "once": bool(args.once),
    },
    symbol=args.symbol,
    timeframe=args.timeframe,
    bridge_dir=args.bridge_dir,
    source="worker",
  )

  from mt5_bridge.background import (  # noqa: WPS433
    _cycle,
    _engine_status_fields,
    build_engines,
    load_config,
  )
  from mt5_bridge.comm_log import append_event
  from mt5_bridge.history_sync import (
    MT5_CACHE_PATH,
    process_history_sync,
    start_history_sync,
  )
  from mt5_bridge.live_monitor_server import start_live_monitor_server
  import mt5_bridge.protocol as protocol  # noqa: WPS433
  from mt5_bridge.protocol import (  # noqa: WPS433
    ensure_bridge_dir,
    normalize_model_ids,
    write_status,
  )
  # After desk modules imported — mirror + re-bind stale append_event refs
  install_comm_log_mirror(symbol=args.symbol, timeframe=args.timeframe)
  import mt5_bridge.background as background  # noqa: WPS433

  book_key = f"{str(args.symbol).lower()}_{str(args.timeframe).lower()}"
  # Each book worker must NOT share mt5_bridge_config.json — 4 processes
  # racing atomic .tmp replace causes PermissionError and kills the worker.
  worker_cfg = RESULTS_DIR / f"mt5_bridge_worker_{book_key}.json"
  worker_pid = RESULTS_DIR / f"mt5_bridge_worker_{book_key}.pid"
  background.CONFIG_PATH = worker_cfg
  background.PID_PATH = worker_pid
  protocol.CONFIG_PATH = worker_cfg

  if args.sim:
    # Isolate sim worker state from live Start/Stop config.
    background.CONFIG_PATH = RESULTS_DIR / f"mt5_bridge_sim_{book_key}.json"
    background.PID_PATH = RESULTS_DIR / f"mt5_bridge_sim_{book_key}.pid"
    background.SERVICE_LOG = RESULTS_DIR / "mt5_bridge_sim_service.log"
    protocol.CONFIG_PATH = background.CONFIG_PATH

  cli_ids = normalize_model_ids(
    [x.strip() for x in str(args.model_ids).split(",")] if args.model_ids else None,
    fallback=args.model_id or (book_ids[0] if book_ids else ""),
  )
  if not cli_ids:
    cli_ids = list(book_ids)
  if not cli_ids:
    print("[live-bridge] no models", flush=True)
    return 2
  # Pin this worker to its book models forever — global mt5_bridge_config.json
  # holds the UNION of all books and must never replace engines here.
  pinned_ids = list(cli_ids)

  if not args.once:
    _register(args, cli_ids)

  bridge_dir = ensure_bridge_dir(args.bridge_dir)
  if args.sim:
    # Make background._cycle treat this dir as sim (skip live-only guards).
    protocol.BRIDGE_SIM_DIR = bridge_dir

  monitor_server = None
  if not args.once:
    try:
      monitor_server = start_live_monitor_server(bridge_dir, args.monitor_port)
      atexit.register(monitor_server.shutdown)
      print(f"[live-bridge] monitor=http://127.0.0.1:{args.monitor_port}", flush=True)
    except OSError as e:
      print(f"[live-bridge] monitor unavailable: {e}", flush=True)

  magic_base = int(LIVE_SIM_MAGIC_BASE if args.sim else LIVE_MAGIC_BASE)
  engines = build_engines(
    cli_ids,
    risk_pct=float(args.risk_pct),
    bridge_dir=bridge_dir,
    base_magic=magic_base,
  )
  primary = next(iter(engines.values()), None)
  print(
    f"[live-bridge] dir={bridge_dir} models={list(engines.keys())} "
    f"risk={args.risk_pct} magic_base={magic_base} "
    f"fp={primary.conditions_fp if primary else '-'}",
    flush=True,
  )
  if not args.sim:
    start_history_sync(bridge_dir, force=args.seed)
  elif not MT5_CACHE_PATH.exists():
    print(
      f"[live-bridge] sim mode needs cache at {MT5_CACHE_PATH} "
      f"(run live/scripts/seed_mt5_cache.py)",
      flush=True,
    )
  try:
    for eng in engines.values():
      eng.ensure_history()
    if primary:
      print(f"[live-bridge] history bars={len(primary.load())}", flush=True)
  except Exception as e:
    print(f"[live-bridge] waiting for history: {e}", flush=True)

  write_status(
    bridge_dir,
    state="running",
    model_ids=list(engines.keys()),
    error=None,
    **_engine_status_fields(primary),
  )
  if not args.sim:
    try:
      from position_sync import reconcile_bridge_positions
      rec = reconcile_bridge_positions(bridge_dir, reason="worker_start_reconcile")
      if rec.get("closed"):
        print(f"[live-bridge] startup reconcile closed={rec.get('closed')}", flush=True)
    except Exception as sync_exc:
      print(f"[live-bridge] startup position_sync skip: {sync_exc}", flush=True)
  last_fp: str | None = None
  last_fill_fp: str | None = None
  last_hist_force_at = 0.0

  while True:
    try:
      if (not args.sim) and is_kill_switch_armed():
        write_status(bridge_dir, state="halted", halt_source="kill_switch", error="kill_switch")
        print("[live-bridge] kill-switch armed — exiting", flush=True)
        return 0

      if not args.sim:
        history = process_history_sync(bridge_dir)
      else:
        history = {"ok": True, "source": "sim_cache"}
      if not MT5_CACHE_PATH.exists():
        # Empty EA export (done + 0 bars) used to stick as "completed" forever.
        hist_state = str((history or {}).get("state") or "").lower()
        stored = int((history or {}).get("stored_bars") or (history or {}).get("received_bars") or 0)
        avail = int((history or {}).get("available_bars") or 0)
        now = time.time()
        if (
          hist_state in ("completed", "error")
          and stored <= 0
          and avail <= 0
          and (now - last_hist_force_at) >= 30.0
        ):
          print(
            f"[live-bridge] history {hist_state} with 0 bars — force re-sync",
            flush=True,
          )
          history = start_history_sync(bridge_dir, force=True)
          last_hist_force_at = now
        write_status(
          bridge_dir,
          state="syncing_history",
          model_ids=list(engines.keys()),
          history=history,
          error=(history or {}).get("error"),
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
        # Never adopt global config.model_ids (all books). Stay on pinned book set.
        desired_ids = list(pinned_ids)
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
            base_magic=magic_base,
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

      if not args.sim:
        try:
          from position_sync import reconcile_bridge_positions
          reconcile_bridge_positions(bridge_dir)
        except Exception as sync_exc:
          print(f"[live-bridge] position_sync skip: {sync_exc}", flush=True)

      if not args.sim:
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
      if not args.sim:
        try:
          log_ea_sync_if_changed(
            bridge_dir, symbol=args.symbol, timeframe=args.timeframe,
          )
          check_pending_signal_timeouts(older_than_sec=120.0)
        except Exception as dbg_exc:
          print(f"[live-bridge] debug_log skip: {dbg_exc}", flush=True)
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
      try:
        log_event(
          "worker_error",
          summary=err.splitlines()[-1] if err else "error",
          payload={"traceback": err[-4000:]},
          level="error",
          symbol=args.symbol,
          timeframe=args.timeframe,
          bridge_dir=bridge_dir,
          source="worker",
        )
      except Exception:
        pass
      write_status(bridge_dir, state="error", error=err[-500:])
      if args.once:
        return 1
    time.sleep(max(0.2, args.poll))


if __name__ == "__main__":
  raise SystemExit(main())
