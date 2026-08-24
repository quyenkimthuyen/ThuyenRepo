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
  BRIDGE_DIR,
  BRIDGE_SIM_DIR,
  atomic_write_json,
  ensure_bridge_dir,
  read_sim_control,
  write_sim_control,
)
from mt5_bridge.trade_journal import clear_trades
from run_backtest import REPORT_DIR

from app_paths import get_root
ROOT = get_root()
SIM_STATE_PATH = REPORT_DIR / "mt5_bridge_sim_state.json"
# Fail fast if Sim EA never acks (no bars / still idle) after Start.
EA_ACK_TIMEOUT_SEC = 25.0

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


def write_sim_state(update: dict[str, Any]) -> dict:
  REPORT_DIR.mkdir(parents=True, exist_ok=True)
  cur: dict[str, Any] = {}
  if SIM_STATE_PATH.exists():
    try:
      cur = json.loads(SIM_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
      cur = {}
  cur.update(update)
  cur["updated_at"] = _now()
  atomic_write_json(SIM_STATE_PATH, cur)
  return cur


def load_sim_state() -> dict[str, Any]:
  if not SIM_STATE_PATH.exists():
    return {"status": "idle"}
  try:
    return json.loads(SIM_STATE_PATH.read_text(encoding="utf-8"))
  except Exception:
    return {"status": "idle"}


def _norm_date(s: str) -> str:
  """EA accepts YYYY.MM.DD or ISO; store dotted for MT5 StringToTime."""
  t = str(s or "").strip().replace("-", ".")[:10]
  return t


def start_history_feed_control(cfg: SimConfig) -> dict[str, Any]:
  """Enable EA HISTORY_FEED via sim_control.json (control only)."""
  bridge_dir = ensure_bridge_dir(Path(cfg.bridge_dir))
  request_id = cfg.request_id or uuid.uuid4().hex[:12]
  delay = max(1, int(cfg.delay_ms))

  # Snapshot previous run before wiping journal for a new feed.
  try:
    from mt5_bridge.sim_history import archive_sim_run, new_sim_run_id
    archive_sim_run(bridge_dir=bridge_dir, status="stopped")
    run_id = new_sim_run_id()
  except Exception:
    run_id = uuid.uuid4().hex[:12]

  if cfg.clear_journal:
    clear_trades(bridge_dir)
    # Sticky fill.json from a Stop mid-trade must not re-open a ghost position
    # on the next Start (engine would HOLD forever on position_open).
    for name in ("fill.json", "ea_fills.jsonl", "fills.jsonl"):
      path = bridge_dir / name
      if path.exists():
        try:
          path.unlink()
        except OSError:
          pass

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
    "run_id": run_id,
    "archived": False,
    "ghosts_reconciled": False,
    "ghosts_closed": 0,
    "started_at": _now(),
    "finished_at": None,
    "bridge_dir": str(bridge_dir),
    "model_id": cfg.model_id,
    "bars_done": 0,
    "bars_total": 0,
    "progress": 0.0,
    "last_bar": None,
    "n_fills": 0,
    "error": None,
    "ea_status": "idle",
    "enabled": True,
  })


def stop_history_feed_control(bridge_dir: Path | None = None) -> dict[str, Any]:
  bridge_dir = ensure_bridge_dir(bridge_dir or BRIDGE_SIM_DIR)
  # Clear EA status so UI cannot stay stuck "running" after Stop with EA offline.
  write_sim_control(
    bridge_dir,
    enabled=False,
    ea_status="idle",
    error="",
  )
  st = write_sim_state({
    "status": "stopped",
    "ea_status": "idle",
    "enabled": False,
    "finished_at": _now(),
  })
  try:
    from mt5_bridge.sim_history import archive_sim_run
    archive_sim_run(bridge_dir=bridge_dir, state=st, status="stopped")
  except Exception:
    pass
  return st


def reset_sim_data(bridge_dir: Path | None = None) -> dict[str, Any]:
  """Reset history-test control files without wiping Live heartbeat or trade journal."""
  from mt5_bridge.comm_log import clear_log

  bridge_dir = ensure_bridge_dir(bridge_dir or BRIDGE_DIR)
  try:
    from mt5_bridge.sim_history import archive_sim_run
    archive_sim_run(bridge_dir=bridge_dir, status="stopped")
  except Exception:
    pass
  clear_log(bridge_dir)

  # Ephemeral protocol files from the previous history test (keep Live heartbeat)
  for name in (
    "bar.json",
    "bars.json",
    "decision.json",
    "fill.json",
    "ea_fills.jsonl",
    "fills.jsonl",
    "status.json",
    "command.json",
    "command_ack.json",
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
  elif enabled:
    # App still wants feed on — do not use stale ea_status=running alone
    # (that left status="running" after Stop when EA had not rewritten control yet).
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
    "run_id": prev.get("run_id"),
    "archived": prev.get("archived"),
    "started_at": prev.get("started_at"),
    "updated_at": _now(),
  }
  if status == "completed" and not prev.get("finished_at"):
    payload["finished_at"] = _now()
  if not persist:
    return {**prev, **payload}
  out = write_sim_state(payload)
  if status in ("completed", "stopped", "error") and not prev.get("ghosts_reconciled"):
    try:
      from mt5_bridge.trade_journal import close_ghost_journal_opens, count_open_trades
      # Final drain then close any journal OPEN left after paper/EA went flat.
      from mt5_bridge.trade_journal import drain_ea_fills_queue, process_fill
      for fill_payload in drain_ea_fills_queue(bridge_dir):
        process_fill(
          fill_payload,
          bridge_dir=bridge_dir,
          model_id=fill_payload.get("model_id"),
        )
      n_ghost = close_ghost_journal_opens(bridge_dir, reason="sim_end_reconcile")
      if n_ghost:
        print(f"[sim] reconciled {n_ghost} ghost OPEN after {status}", flush=True)
        # refresh fill count for archive
        try:
          data = json.loads(trades_path.read_text(encoding="utf-8"))
          trades = data.get("trades") if isinstance(data, dict) else data
          out = write_sim_state({
            "n_fills": len(trades or []),
            "ghosts_reconciled": True,
            "ghosts_closed": n_ghost,
          })
        except Exception:
          out = write_sim_state({"ghosts_reconciled": True, "ghosts_closed": n_ghost})
      elif count_open_trades(bridge_dir) == 0:
        out = write_sim_state({"ghosts_reconciled": True, "ghosts_closed": 0})
    except Exception as e:
      print(f"[sim] ghost reconcile skipped: {e}", flush=True)
  if status == "completed" and not out.get("archived") and not prev.get("archived"):
    try:
      from mt5_bridge.sim_history import archive_sim_run
      archive_sim_run(bridge_dir=bridge_dir, state=out, status="completed")
    except Exception:
      pass
  return out


def run_history_feed_control(
  cfg: SimConfig,
  *,
  stop_event: threading.Event | None = None,
  pause_event: threading.Event | None = None,
  on_progress: ProgressCb | None = None,
  poll_sec: float = 0.5,
  ea_ack_timeout_sec: float = EA_ACK_TIMEOUT_SEC,
) -> dict[str, Any]:
  """Write control, poll EA until completed/stopped/error.

  If the Sim EA never acknowledges within ``ea_ack_timeout_sec`` (still idle,
  zero bars), stop the feed and return ``status=error`` so the UI is not left
  hung forever when the EA is not deployed.
  """
  st0 = start_history_feed_control(cfg)
  bridge_dir = Path(cfg.bridge_dir)
  request_id = st0.get("request_id")
  last_persist_bars = -1
  last_persist_t = 0.0
  stop_hits = 0
  last_bars_done = -1
  t0 = time.time()
  ea_acked = False
  timeout_sec = max(5.0, float(ea_ack_timeout_sec))

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
      # Don't count pause time against EA ack timeout
      t0 = time.time()

    # Throttle disk writes — frequent writes remount Streamlit iframes
    now = time.time()
    st = sync_state_from_ea(bridge_dir, persist=False)
    bars_done = int(st.get("bars_done") or 0)
    bars_total = int(st.get("bars_total") or 0)
    ea_status = str(st.get("ea_status") or "idle")
    if (
      not ea_acked
      and (
        ea_status in ("running", "completed", "error")
        or bars_done > 0
        or bars_total > 0
      )
    ):
      ea_acked = True

    if not ea_acked and (now - t0) >= timeout_sec:
      msg = (
        f"EA Simulate không phản hồi trong {timeout_sec:.0f}s — "
        "gắn ForgeBridge*Sim lên chart (InpMode=History Feed), "
        "đúng folder bridge_sim, rồi Deploy lại nếu cần."
      )
      print(f"[sim-control] EA ack timeout: {msg}", flush=True)
      write_sim_control(
        bridge_dir,
        enabled=False,
        ea_status="error",
        error=msg,
      )
      out = write_sim_state({
        "status": "error",
        "ea_status": "error",
        "error": msg,
        "enabled": False,
        "finished_at": _now(),
        "stop_reason": "ea_ack_timeout",
      })
      try:
        from mt5_bridge.sim_history import archive_sim_run
        archive_sim_run(bridge_dir=bridge_dir, state=out, status="error")
      except Exception:
        pass
      return out

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
