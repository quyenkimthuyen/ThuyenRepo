#!/usr/bin/env python3
"""Persistent Paper Monitor service; recompute on new H1 bar/config changes."""
from __future__ import annotations

import atexit
import os
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from mt5_bridge.history_sync import load_mt5_cache
from mt5_bridge.models import get_model_run_params, load_active_model_id, resolve_model
from paper_live_monitor_server import start_paper_live_monitor_server
from paper_service import PID_PATH, load_config, save_config
from paper_background import run_cycle_now

_stop = False


def _request_stop(*_args) -> None:
  global _stop
  _stop = True


def _bar_fingerprint() -> str | None:
  frame = load_mt5_cache()
  if frame is None or frame.empty:
    return None
  return f"{len(frame)}|{frame.index[-1]}|{float(frame.iloc[-1]['Close']):.5f}"


def _runtime_config() -> dict:
  cfg = load_config()
  model_id = load_active_model_id()
  model = resolve_model(model_id)
  params = get_model_run_params(model, model_id)
  desired = {
    "model_id": model_id,
    "use_learning": bool(params.get("use_learning", True)),
    "kb_profile": params.get("kb_profile") or "default",
    "kb_snapshot": params.get("kb_snapshot"),
    "spread_pips": float(params.get("spread_pips", 1.0)),
    "slippage_pips": float(params.get("slippage_pips", 0.3)),
  }
  if any(cfg.get(key) != value for key, value in desired.items()):
    cfg = save_config(**desired, last_model_reload_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
  return cfg


def _settings_fingerprint(cfg: dict) -> tuple:
  return (
    cfg.get("model_id"),
    float(cfg.get("risk_pct", 1.0)),
    bool(cfg.get("use_learning")),
    cfg.get("kb_profile"),
    cfg.get("kb_snapshot"),
    float(cfg.get("spread_pips", 1.0)),
    float(cfg.get("slippage_pips", 0.3)),
  )


def main() -> int:
  global _stop
  pid = os.getpid()
  PID_PATH.write_text(str(pid), encoding="utf-8")
  save_config(enabled=True, service_pid=pid, last_error=None)

  def cleanup() -> None:
    cfg = load_config()
    if int(cfg.get("service_pid") or 0) == pid:
      save_config(service_pid=None)
    try:
      if PID_PATH.exists() and PID_PATH.read_text(encoding="utf-8").strip() == str(pid):
        PID_PATH.unlink()
    except OSError:
      pass

  atexit.register(cleanup)
  signal.signal(signal.SIGINT, _request_stop)
  if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, _request_stop)

  try:
    chart_server = start_paper_live_monitor_server()
    atexit.register(chart_server.shutdown)
    print("paper chart=http://127.0.0.1:8866", flush=True)
  except OSError as exc:
    print(f"paper chart unavailable: {exc}", flush=True)

  last_bar = None
  last_settings = None
  while not _stop:
    cfg = _runtime_config()
    if not cfg.get("enabled"):
      break
    poll = max(0.5, float(cfg.get("poll_sec", 2.0)))
    try:
      bar_fp = _bar_fingerprint()
      settings_fp = _settings_fingerprint(cfg)
      state_exists = (ROOT / "results" / "paper_monitor_state.json").exists()
      if bar_fp and (bar_fp != last_bar or settings_fp != last_settings or not state_exists):
        state = run_cycle_now(cfg)
        last_bar = bar_fp
        last_settings = settings_fp
        save_config(
          last_bar=state.get("last_bar"),
          last_run_at=state.get("updated_at"),
          last_error=None,
        )
        print(
          f"paper bar={state.get('last_bar')} model={cfg.get('model_id')} "
          f"trades={state.get('week_trades_taken')}",
          flush=True,
        )
    except Exception as exc:
      save_config(last_error=str(exc))
      print(f"paper ERROR: {exc}", flush=True)
    end = time.monotonic() + poll
    while not _stop and time.monotonic() < end:
      time.sleep(min(0.2, end - time.monotonic()))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())

