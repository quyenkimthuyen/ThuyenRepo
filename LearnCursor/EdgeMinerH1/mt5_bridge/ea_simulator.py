"""App-side control for ForgeBridge HISTORY_FEED mode.

EA (MT5) reads sim_control.json, CopyRates historical bars, writes bar/fill
into mt5/bridge_sim/. App only writes from/to/delay and polls EA status —
it does NOT fake bar.json / fill.json.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from mt5_bridge.protocol import (
  BRIDGE_SIM_DIR,
  atomic_write_json,
  ensure_bridge_dir,
  read_sim_control,
  write_sim_control,
)
from mt5_bridge.trade_journal import clear_trades
from run_backtest import REPORT_DIR

ROOT = Path(__file__).resolve().parents[1]
SIM_STATE_PATH = REPORT_DIR / "mt5_bridge_sim_state.json"

ProgressCb = Callable[[dict[str, Any]], None]


@dataclass
class SimConfig:
  date_from: str
  date_to: str
  delay_ms: int = 100
  model_id: str | None = None
  risk_pct: float = 1.0
  bridge_dir: Path = field(default_factory=lambda: BRIDGE_SIM_DIR)
  clear_journal: bool = True
  request_id: str | None = None


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _canonical_sim_bridge_dir(raw: Any = None) -> Path:
  """Always use H1 bridge_sim_h1 — ignore stale bridge_sim paths from older deploys."""
  try:
    if raw:
      p = Path(str(raw))
      if p.resolve() == BRIDGE_SIM_DIR.resolve():
        return BRIDGE_SIM_DIR
  except Exception:
    pass
  return BRIDGE_SIM_DIR


def write_sim_state(update: dict[str, Any]) -> dict:
  REPORT_DIR.mkdir(parents=True, exist_ok=True)
  cur: dict[str, Any] = {}
  if SIM_STATE_PATH.exists():
    try:
      cur = json.loads(SIM_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
      cur = {}
  cur.update(update)
  cur["bridge_dir"] = str(_canonical_sim_bridge_dir(cur.get("bridge_dir")))
  cur["updated_at"] = _now()
  atomic_write_json(SIM_STATE_PATH, cur)
  return cur


def load_sim_state() -> dict[str, Any]:
  if not SIM_STATE_PATH.exists():
    return {"status": "idle", "bridge_dir": str(BRIDGE_SIM_DIR)}
  try:
    cur = json.loads(SIM_STATE_PATH.read_text(encoding="utf-8"))
  except Exception:
    return {"status": "idle", "bridge_dir": str(BRIDGE_SIM_DIR)}
  want = str(BRIDGE_SIM_DIR)
  if str(cur.get("bridge_dir") or "") != want:
    cur["bridge_dir"] = want
    try:
      atomic_write_json(SIM_STATE_PATH, cur)
    except Exception:
      pass
  return cur


def _norm_date(s: str) -> str:
  """EA accepts YYYY.MM.DD or ISO; store dotted for MT5 StringToTime."""
  t = str(s or "").strip().replace("-", ".")[:10]
  return t


def start_history_feed_control(cfg: SimConfig) -> dict[str, Any]:
  """Enable EA HISTORY_FEED via sim_control.json (control only)."""
  bridge_dir = ensure_bridge_dir(Path(cfg.bridge_dir))
  request_id = cfg.request_id or uuid.uuid4().hex[:12]
  delay = max(1, int(cfg.delay_ms))
  if cfg.clear_journal:
    clear_trades(bridge_dir)

  write_sim_control(
    bridge_dir,
    merge=False,
    enabled=True,
    **{
      "from": _norm_date(cfg.date_from),
      "to": _norm_date(cfg.date_to),
      "delay_ms": delay,
      "request_id": request_id,
      "ea_status": "idle",
      "bars_done": 0,
      "bars_total": 0,
      "last_bar": "",
      "error": "",
      "model_id": cfg.model_id,
    },
  )

  return write_sim_state({
    "status": "running",
    "source": "ea_history_feed",
    "date_from": cfg.date_from,
    "date_to": cfg.date_to,
    "delay_ms": delay,
    "request_id": request_id,
    "bridge_dir": str(bridge_dir),
    "model_id": cfg.model_id,
    "bars_done": 0,
    "bars_total": 0,
    "progress": 0.0,
    "last_bar": None,
    "n_fills": 0,
    "error": None,
    "ea_status": "idle",
  })


def stop_history_feed_control(bridge_dir: Path | None = None) -> dict[str, Any]:
  bridge_dir = ensure_bridge_dir(bridge_dir or BRIDGE_SIM_DIR)
  write_sim_control(bridge_dir, enabled=False)
  return write_sim_state({"status": "stopped", "ea_status": "idle"})


def reset_sim_data(bridge_dir: Path | None = None) -> dict[str, Any]:
  """Wipe bridge_sim run artifacts so the next History Feed starts clean."""
  from mt5_bridge.comm_log import clear_log

  bridge_dir = ensure_bridge_dir(bridge_dir or BRIDGE_SIM_DIR)
  clear_trades(bridge_dir)
  clear_log(bridge_dir)

  # Ephemeral protocol files from the previous run
  for name in (
    "bar.json",
    "bars.json",
    "connection.json",
    "decision.json",
    "fill.json",
    "ea_fills.jsonl",
    "fills.jsonl",
    "status.json",
    "command.json",
    "command_ack.json",
    "history_request.json",
    "history_chunk.json",
    "history_ack.json",
    "history_status.json",
  ):
    path = bridge_dir / name
    if path.exists():
      try:
        path.unlink()
      except OSError:
        pass

  write_sim_control(
    bridge_dir,
    merge=False,
    enabled=False,
    **{
      "from": "",
      "to": "",
      "delay_ms": 100,
      "request_id": "",
      "ea_status": "idle",
      "bars_done": 0,
      "bars_total": 0,
      "last_bar": "",
      "error": "",
    },
  )
  if SIM_STATE_PATH.exists():
    try:
      SIM_STATE_PATH.unlink()
    except OSError:
      pass
  return write_sim_state({
    "status": "idle",
    "source": "ea_history_feed",
    "ea_status": "idle",
    "bars_done": 0,
    "bars_total": 0,
    "progress": 0.0,
    "last_bar": None,
    "n_fills": 0,
    "error": None,
    "enabled": False,
    "bridge_dir": str(bridge_dir),
  })


def sync_state_from_ea(
  bridge_dir: Path | None = None,
  *,
  persist: bool = True,
) -> dict[str, Any]:
  """Mirror EA fields from sim_control.json into app sim_state.

  persist=False: return merged status without writing disk (UI polls — avoids
  Streamlit file-watcher full reruns that remount the chart iframe).
  """
  bridge_dir = bridge_dir or BRIDGE_SIM_DIR
  prev = load_sim_state()
  ctrl = read_sim_control(bridge_dir)
  # EA rewrites sim_control every bar — transient empty/partial JSON must NOT
  # demote a running feed to "stopped" (that kills the App sim service mid-run).
  if not ctrl:
    kept = str(prev.get("status") or "running")
    if kept not in ("running", "paused", "completed", "error"):
      kept = "running"
    payload = {
      **prev,
      "status": kept,
      "error": prev.get("error"),
      "updated_at": _now(),
      "read_glitch": True,
    }
    if not persist:
      return payload
    return write_sim_state({k: v for k, v in payload.items() if k != "read_glitch"})

  ea_status = str(ctrl.get("ea_status") or "idle")
  bars_done = int(ctrl.get("bars_done") or 0)
  bars_total = int(ctrl.get("bars_total") or 0)
  progress = (bars_done / bars_total) if bars_total > 0 else 0.0
  enabled = bool(ctrl.get("enabled"))
  error = ctrl.get("error") or None
  if not error:
    error = None

  in_progress = bars_total > 0 and 0 < bars_done < bars_total
  if ea_status == "completed":
    status = "completed"
  elif ea_status == "error":
    status = "error"
    if not error:
      error = "EA reported error status"
  elif enabled or ea_status == "running":
    status = "running"
  elif prev.get("status") == "paused" or ea_status == "paused":
    status = "paused"
  elif in_progress and prev.get("status") == "running":
    # enabled briefly false / idle flicker while EA still mid-range
    status = "running"
  elif prev.get("status") in ("running", "paused") and not enabled:
    status = "stopped"
  else:
    status = str(prev.get("status") or "idle")

  trades_path = ensure_bridge_dir(bridge_dir) / "trades.json"
  n_fills = 0
  if trades_path.exists():
    try:
      data = json.loads(trades_path.read_text(encoding="utf-8"))
      trades = data.get("trades") if isinstance(data, dict) else data
      n_fills = len(trades or [])
    except Exception:
      n_fills = int(prev.get("n_fills") or 0)

  payload = {
    "status": status,
    "ea_status": ea_status,
    "bars_done": bars_done,
    "bars_total": bars_total,
    "progress": progress,
    "last_bar": ctrl.get("last_bar") or prev.get("last_bar"),
    "error": error,
    "n_fills": n_fills,
    "enabled": enabled,
    "request_id": ctrl.get("request_id") or prev.get("request_id"),
    "date_from": ctrl.get("from") or prev.get("date_from"),
    "date_to": ctrl.get("to") or prev.get("date_to"),
    "delay_ms": ctrl.get("delay_ms") or prev.get("delay_ms"),
    "bridge_dir": str(bridge_dir),
    "source": "ea_history_feed",
    "model_id": prev.get("model_id"),
    "updated_at": _now(),
  }
  if not persist:
    return {**prev, **payload}
  return write_sim_state(payload)


def run_history_feed_control(
  cfg: SimConfig,
  *,
  stop_event: threading.Event | None = None,
  pause_event: threading.Event | None = None,
  on_progress: ProgressCb | None = None,
  poll_sec: float = 0.5,
) -> dict[str, Any]:
  """Write control, poll EA until completed/stopped/error."""
  st0 = start_history_feed_control(cfg)
  bridge_dir = Path(cfg.bridge_dir)
  request_id = st0.get("request_id")
  last_persist_bars = -1
  last_persist_t = 0.0
  stop_hits = 0
  last_bars_done = -1

  while True:
    if stop_event is not None and stop_event.is_set():
      stop_history_feed_control(bridge_dir)
      st = sync_state_from_ea(bridge_dir, persist=True)
      st["stop_reason"] = "stop_event"
      return st

    if pause_event is not None and pause_event.is_set():
      write_sim_control(bridge_dir, enabled=False)
      write_sim_state({"status": "paused"})
      while pause_event.is_set():
        if stop_event is not None and stop_event.is_set():
          stop_history_feed_control(bridge_dir)
          return sync_state_from_ea(bridge_dir, persist=True)
        time.sleep(0.25)
      write_sim_control(
        bridge_dir,
        enabled=True,
        request_id=request_id,
        **{
          "from": _norm_date(cfg.date_from),
          "to": _norm_date(cfg.date_to),
          "delay_ms": max(1, int(cfg.delay_ms)),
        },
      )
      write_sim_state({"status": "running"})

    # Throttle disk writes — frequent writes remount Streamlit iframes
    now = time.time()
    st = sync_state_from_ea(bridge_dir, persist=False)
    bars_done = int(st.get("bars_done") or 0)
    if bars_done > last_bars_done:
      last_bars_done = bars_done
      stop_hits = 0
    should_persist = (
      st.get("status") in ("completed", "error", "stopped")
      or (bars_done != last_persist_bars and (now - last_persist_t) >= 2.0)
      or (now - last_persist_t) >= 5.0
    )
    if should_persist:
      st = sync_state_from_ea(bridge_dir, persist=True)
      last_persist_bars = bars_done
      last_persist_t = now
    if on_progress:
      on_progress(st)

    status = st.get("status")
    if status in ("completed", "error"):
      print(
        f"[sim-control] exit status={status} bars={bars_done}/"
        f"{st.get('bars_total')} ea={st.get('ea_status')} err={st.get('error')}",
        flush=True,
      )
      return st
    if status == "stopped":
      stop_hits += 1
      # Require sustained stop (avoid JSON race on sim_control mid-write)
      if stop_hits >= 6:
        print(
          f"[sim-control] exit status=stopped after {stop_hits} polls "
          f"enabled={st.get('enabled')} ea={st.get('ea_status')} "
          f"bars={bars_done}/{st.get('bars_total')} last={st.get('last_bar')}",
          flush=True,
        )
        st["stop_reason"] = "ea_disabled_or_idle"
        return st
    else:
      stop_hits = 0
    time.sleep(max(0.2, float(poll_sec)))


# Back-compat alias used by older CLI / background imports
def run_simulation(*args, **kwargs):
  return run_history_feed_control(*args, **kwargs)
