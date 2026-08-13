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
from mt5_bridge.history_sync import MT5_CACHE_PATH, process_history_sync, start_history_sync
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  DEFAULT_MAGIC,
  DEFAULT_MODEL_ID,
  DEFAULT_SIM_MAGIC,
  MAX_BRIDGE_MODELS,
  atomic_write_json,
  bar_path,
  decision_path,
  ensure_bridge_dir,
  fill_path,
  magic_to_model_id,
  normalize_model_ids,
  read_json,
  read_models_roster,
  write_model_decision,
  write_models_roster,
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
_engines: dict[str, BridgeEngine] = {}


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _engine_status_fields(engine: BridgeEngine | None, **extra) -> dict:
  """Status fields shared with Health (same Trade Model conditions fingerprint).

  ``extra`` overrides engine defaults — callers must not also pass the same keys
  as explicit kwargs alongside ``**_engine_status_fields(...)``.
  """
  out: dict = {}
  if engine is not None:
    out = {
      "model_id": engine.model_id,
      "conditions_fp": engine.conditions_fp,
      "run_conditions": engine.describe_conditions(),
    }
  out.update(extra)
  return out


def config_model_ids(cfg: dict | None = None) -> list[str]:
  data = cfg or load_config()
  return normalize_model_ids(
    data.get("model_ids"),
    fallback=data.get("model_id") or DEFAULT_MODEL_ID,
  )


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


def sync_bridge_roster(
  *,
  bridge_dir: Path | None = None,
  model_ids: list[str] | None = None,
  risk_pct: float | None = None,
  base_magic: int | None = None,
  labels: dict[str, str] | None = None,
) -> dict:
  """Write models.json for EA; returns roster payload."""
  cfg = load_config()
  ids = normalize_model_ids(model_ids, fallback=None) or config_model_ids(cfg)
  risk = float(risk_pct if risk_pct is not None else cfg.get("risk_pct") or 1.0)
  from mt5_bridge.protocol import BRIDGE_SIM_DIR
  bdir = ensure_bridge_dir(bridge_dir or Path(cfg.get("bridge_dir") or BRIDGE_DIR))
  is_sim = Path(bdir).resolve() == BRIDGE_SIM_DIR.resolve()
  base = int(
    base_magic
    if base_magic is not None
    else (DEFAULT_SIM_MAGIC if is_sim else DEFAULT_MAGIC)
  )
  label_map = dict(labels or {})
  if not label_map:
    try:
      from gui.trade_model import format_model_label, list_trade_models
      by_id = {
        str(m.get("id") or ""): format_model_label(m)
        for m in list_trade_models()
        if m.get("id")
      }
      for mid in ids:
        if mid in by_id:
          label_map[mid] = by_id[mid]
    except Exception:
      pass
  return write_models_roster(
    ids, risk_pct=risk, bridge_dir=bdir, base_magic=base, labels=label_map,
  )


def build_engines(
  model_ids: list[str],
  *,
  risk_pct: float,
  bridge_dir: Path,
  base_magic: int,
  existing_engines: dict[str, BridgeEngine] | None = None,
) -> dict[str, BridgeEngine]:
  """Create/reuse BridgeEngine per model with stable magics from roster."""
  roster = write_models_roster(
    model_ids,
    risk_pct=float(risk_pct),
    bridge_dir=bridge_dir,
    base_magic=int(base_magic),
  )
  magic_by_id = {
    str(r["id"]): int(r["magic"])
    for r in (roster.get("models") or [])
    if isinstance(r, dict) and r.get("id") is not None
  }
  prev = existing_engines or {}
  out: dict[str, BridgeEngine] = {}
  for mid in normalize_model_ids(model_ids):
    magic = int(magic_by_id.get(mid, base_magic))
    old = prev.get(mid)
    if (
      old is not None
      and old.model_id == mid
      and abs(old.risk_pct - float(risk_pct)) < 1e-9
      and int(old.magic) == magic
    ):
      out[mid] = old
    else:
      eng = BridgeEngine(
        model_id=mid,
        risk_pct=float(risk_pct),
        magic=magic,
        bridge_dir=bridge_dir,
      )
      out[mid] = eng
  return out


def load_config() -> dict:
  data = _read_json(CONFIG_PATH) or {}
  bridge_dir = data.get("bridge_dir") or str(BRIDGE_DIR)
  # Config may come from the old Linux/Docker deployment. On native Windows
  # that path is invalid and causes a failed service restart on every rerun.
  if os.name == "nt" and str(bridge_dir).startswith("/"):
    bridge_dir = str(BRIDGE_DIR)
  model_id = data.get("model_id") or DEFAULT_MODEL_ID
  model_ids = normalize_model_ids(data.get("model_ids"), fallback=model_id)
  primary = model_ids[0] if model_ids else model_id
  return {
    "enabled": bool(data.get("enabled", False)),
    "model_id": primary,
    "model_ids": model_ids,
    "risk_pct": float(data.get("risk_pct", 1.0)),
    "poll_sec": float(data.get("poll_sec", 2.0)),
    "bridge_dir": bridge_dir,
    "mode": data.get("mode") or "process",
    "service_pid": data.get("service_pid"),
    "last_run_at": data.get("last_run_at"),
    "last_error": data.get("last_error"),
    "last_action": data.get("last_action"),
    "last_bar": data.get("last_bar"),
    # Opt-in consecutive-loss circuit breaker (Live). Numeric defaults are
    # overwritten in the GUI from int(model Max DD)+1 when a Trade Model is set.
    "loss_guard_enabled": bool(data.get("loss_guard_enabled", True)),
    "loss_guard_max_day": int(
      data["loss_guard_max_day"] if "loss_guard_max_day" in data else 3
    ),
    "loss_guard_max_week": int(
      data["loss_guard_max_week"] if "loss_guard_max_week" in data else 3
    ),
    "loss_guard_max_day_dd_r": float(data.get("loss_guard_max_day_dd_r") or 0),
    "loss_guard_max_week_dd_r": float(data.get("loss_guard_max_week_dd_r") or 0),
    "loss_guard_max_day_loss_r": float(data.get("loss_guard_max_day_loss_r") or 0),
    "loss_guard_max_week_loss_r": float(data.get("loss_guard_max_week_loss_r") or 0),
    "loss_guard_tripped": bool(data.get("loss_guard_tripped", False)),
    "loss_guard_tripped_at": data.get("loss_guard_tripped_at"),
    "loss_guard_tripped_reason": data.get("loss_guard_tripped_reason"),
  }


def save_config(**updates) -> dict:
  cfg = load_config()
  # Allow clearing nullable fields with None (e.g. service_pid)
  nullable = {
    "service_pid", "last_error", "last_action", "last_bar", "last_run_at",
    "loss_guard_tripped_at", "loss_guard_tripped_reason",
  }
  for k, v in updates.items():
    if v is None and k not in nullable:
      continue
    cfg[k] = v
  if "model_ids" in updates or "model_id" in updates:
    ids = normalize_model_ids(
      cfg.get("model_ids"),
      fallback=cfg.get("model_id") or DEFAULT_MODEL_ID,
    )
    cfg["model_ids"] = ids
    if ids:
      cfg["model_id"] = ids[0]
  _write_json(CONFIG_PATH, cfg)
  return cfg


def check_and_apply_loss_guard(
  *,
  bridge_dir: Path | None = None,
  bar: dict | None = None,
  model_id: str | None = None,
  model_ids: list[str] | None = None,
  cfg: dict | None = None,
) -> dict | None:
  """If consecutive-loss limits hit → FLAT + disable service. Returns trip or None."""
  from mt5_bridge.loss_guard import apply_loss_guard_halt, evaluate_loss_guard

  runtime = cfg or load_config()
  trip = evaluate_loss_guard(runtime, bridge_dir=bridge_dir)
  if not trip:
    return None
  ids = normalize_model_ids(model_ids, fallback=None) or config_model_ids(runtime)
  apply_loss_guard_halt(
    trip,
    bridge_dir=bridge_dir,
    bar=bar,
    model_id=model_id or (ids[0] if ids else runtime.get("model_id")),
    model_ids=ids,
  )
  _stop.set()
  return trip


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


def _cycle(
  engines: dict[str, BridgeEngine] | BridgeEngine,
  bridge_dir: Path,
  last_bar_fp: str | None,
  last_fill_fp: str | None,
):
  from mt5_bridge.protocol import BRIDGE_SIM_DIR

  if isinstance(engines, BridgeEngine):
    eng_map: dict[str, BridgeEngine] = {engines.model_id: engines}
  else:
    eng_map = dict(engines or {})
  primary = next(iter(eng_map.values()), None)
  primary_id = primary.model_id if primary else None
  is_sim = Path(bridge_dir).resolve() == BRIDGE_SIM_DIR.resolve()
  roster = read_models_roster(bridge_dir)
  seen_fills: set[str] = set()
  if isinstance(last_fill_fp, str) and last_fill_fp.startswith("["):
    try:
      seen_fills = set(json.loads(last_fill_fp))
    except Exception:
      seen_fills = {last_fill_fp} if last_fill_fp else set()
  elif last_fill_fp:
    seen_fills = {last_fill_fp}

  def _resolve_engine_for_fill(fill: dict) -> BridgeEngine | None:
    mid = str(fill.get("model_id") or "") or None
    if mid and mid in eng_map:
      return eng_map[mid]
    mag = fill.get("magic")
    mapped = magic_to_model_id(roster, mag)
    if mapped and mapped in eng_map:
      return eng_map[mapped]
    if mag is not None:
      try:
        m = int(mag)
      except (TypeError, ValueError):
        m = None
      if m is not None:
        for eng in eng_map.values():
          if int(eng.magic) == m:
            return eng
    return primary

  def _ingest_fill(fill: dict) -> None:
    nonlocal seen_fills
    fp_fill = _fill_fp(fill)
    if not fp_fill or fp_fill in seen_fills:
      return
    eng = _resolve_engine_for_fill(fill)
    if not is_sim:
      append_event(
        "ea_to_app",
        "fill_received",
        bridge_dir=bridge_dir,
        payload=fill,
        summary=(
          f"fill {fill.get('event') or fill.get('action')} ok={fill.get('ok')} "
          f"sid={fill.get('signal_id')} model={fill.get('model_id') or (eng.model_id if eng else '')} "
          f"detail={fill.get('detail')}"
        ),
      )
    last_decision = eng._last_decision if eng else None
    process_fill(
      fill,
      bridge_dir=bridge_dir,
      decision=last_decision if isinstance(last_decision, dict) else None,
      model_id=(eng.model_id if eng else None) or fill.get("model_id"),
    )
    seen_fills.add(fp_fill)
    if not is_sim:
      save_config(last_run_at=_now_iso())

  # HistoryFeed: atomic drain so EA appends during read are not truncated away
  from mt5_bridge.trade_journal import drain_ea_fills_queue

  for payload in drain_ea_fills_queue(bridge_dir):
    _ingest_fill(payload)

  fill = read_json(fill_path(bridge_dir))
  if isinstance(fill, dict):
    _ingest_fill(fill)

  last_fill_fp = json.dumps(sorted(seen_fills)[-80:], ensure_ascii=False)

  bar = read_json(bar_path(bridge_dir))
  if not is_sim:
    trip = check_and_apply_loss_guard(
      bridge_dir=bridge_dir,
      bar=bar if isinstance(bar, dict) else None,
      model_id=primary_id,
      model_ids=list(eng_map.keys()),
    )
    if trip:
      return last_bar_fp, last_fill_fp

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

  runtime = load_config() if not is_sim else {}
  halt = (
    (not is_sim)
    and (runtime.get("loss_guard_tripped") or not runtime.get("enabled", True))
  )
  per_model: dict[str, dict] = {}
  last_decision: dict | None = None
  for mid, eng in eng_map.items():
    if halt:
      from mt5_bridge.loss_guard import build_flat_halt_decision
      decision = build_flat_halt_decision(
        bar,
        reason=runtime.get("loss_guard_tripped_reason") or "Loss guard / service disabled",
        model_id=mid,
      )
      decision["magic"] = eng.magic
      decision["risk_pct"] = eng.risk_pct
    else:
      decision = eng.decide_for_bar(bar)
    write_model_decision(
      decision,
      bridge_dir=bridge_dir,
      mirror_primary=True,
      primary_model_id=primary_id,
    )
    last_decision = decision
    per_model[mid] = {
      "action": decision.get("action"),
      "reason": decision.get("reason"),
      "signal_id": decision.get("signal_id"),
      "magic": decision.get("magic"),
      "strategy_name": decision.get("strategy_name"),
      "conditions_fp": decision.get("conditions_fp") or eng.conditions_fp,
    }
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
          "model_id": mid,
          "magic": decision.get("magic"),
        },
        summary=(
          f"decision {mid} {decision.get('action')} bar={decision.get('bar_time')} "
          f"reason={decision.get('reason')}"
        ),
      )

  write_status(
    bridge_dir,
    state="decided",
    last_bar=fp,
    last_action=(last_decision or {}).get("action"),
    reason=(last_decision or {}).get("reason"),
    week_start=(last_decision or {}).get("week_start"),
    strategy_name=(last_decision or {}).get("strategy_name"),
    model_ids=list(eng_map.keys()),
    per_model=per_model,
    error=None,
    **_engine_status_fields(primary),
  )
  if not is_sim:
    save_config(
      last_run_at=_now_iso(),
      last_action=(last_decision or {}).get("action"),
      last_bar=fp,
      last_error=None,
    )
  return fp, last_fill_fp



def _worker():
  global _engine, _engines
  cfg = load_config()
  bridge_dir = ensure_bridge_dir(Path(cfg["bridge_dir"]))
  append_event("system", "service_start", bridge_dir=bridge_dir, summary="bridge thread started")
  start_history_sync(bridge_dir)
  try:
    ids = config_model_ids(cfg)
    _engines = build_engines(
      ids,
      risk_pct=float(cfg["risk_pct"]),
      bridge_dir=BRIDGE_DIR,
      base_magic=DEFAULT_MAGIC,
    )
    _engine = next(iter(_engines.values()), None)
    if MT5_CACHE_PATH.exists() and _engine:
      for eng in _engines.values():
        eng.ensure_history()
    write_status(
      bridge_dir,
      state="running",
      error=None,
      runtime="thread",
      model_ids=list(_engines.keys()),
      **_engine_status_fields(_engine),
    )
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
      process_history_sync(bridge_dir)
      if not MT5_CACHE_PATH.exists():
        _stop.wait(poll)
        continue
      desired_ids = config_model_ids(cfg)
      desired_risk = float(cfg["risk_pct"])
      cur_ids = list(_engines.keys())
      risk_changed = any(
        abs(e.risk_pct - desired_risk) > 1e-9 for e in _engines.values()
      )
      if cur_ids != desired_ids or risk_changed:
        _engines = build_engines(
          desired_ids,
          risk_pct=desired_risk,
          bridge_dir=BRIDGE_DIR,
          base_magic=DEFAULT_MAGIC,
          existing_engines=_engines,
        )
        _engine = next(iter(_engines.values()), None)
        for eng in _engines.values():
          eng.ensure_history()
        append_event(
          "system", "engine_reload", bridge_dir=bridge_dir,
          summary=f"models={desired_ids} risk={desired_risk}",
        )
      else:
        for eng in _engines.values():
          if eng.refresh_model():
            append_event(
              "system", "engine_reload", bridge_dir=bridge_dir,
              summary=f"conditions_fp={eng.conditions_fp} model={eng.model_id}",
              payload=eng.describe_conditions(),
            )
      last_bar_fp, last_fill_fp = _cycle(_engines, bridge_dir, last_bar_fp, last_fill_fp)
      if _stop.is_set() or not load_config().get("enabled"):
        break
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
    try:
      from mt5_bridge.trade_journal import clear_sticky_fill_files
      clear_sticky_fill_files(BRIDGE_DIR)
    except Exception:
      pass
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
    try:
      from mt5_bridge.trade_journal import clear_sticky_fill_files
      clear_sticky_fill_files(BRIDGE_DIR)
    except Exception:
      pass
    _stop.set()
    cfg = load_config()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
      sys.executable,
      str(SERVICE_SCRIPT),
      "--risk-pct", str(cfg.get("risk_pct") or 1.0),
      "--poll", str(cfg.get("poll_sec") or 2.0),
      "--bridge-dir", str(cfg.get("bridge_dir") or BRIDGE_DIR),
    ]
    ids = config_model_ids(cfg)
    if ids:
      cmd.extend(["--model-ids", ",".join(ids)])
      cmd.extend(["--model-id", ids[0]])
    else:
      cmd.extend(["--model-id", str(cfg.get("model_id") or DEFAULT_MODEL_ID)])
    sync_bridge_roster(
      bridge_dir=Path(cfg.get("bridge_dir") or BRIDGE_DIR),
      model_ids=ids,
      risk_pct=float(cfg.get("risk_pct") or 1.0),
      base_magic=DEFAULT_MAGIC,
    )
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
  ids = config_model_ids(cfg)
  engines = build_engines(
    ids,
    risk_pct=float(cfg["risk_pct"]),
    bridge_dir=bridge_dir,
    base_magic=DEFAULT_MAGIC,
  )
  process_history_sync(bridge_dir)
  for eng in engines.values():
    eng.ensure_history()
  _cycle(engines, bridge_dir, None, None)
  primary = next(iter(engines.values()), None)
  return primary._last_decision if primary else None


# --- Simulate EA worker: detached process (like Live) so Streamlit stays smooth ---

_sim_thread: threading.Thread | None = None
_sim_bridge_thread: threading.Thread | None = None
_sim_stop = threading.Event()
_sim_pause = threading.Event()
_sim_lock = threading.Lock()

SIM_PID_PATH = REPORT_DIR / "mt5_bridge_sim_service.pid"
SIM_SERVICE_LOG = REPORT_DIR / "mt5_bridge_sim_service.log"
SIM_SERVICE_SCRIPT = ROOT / "scripts" / "mt5_bridge_sim_service.py"


def _read_sim_pid() -> int | None:
  if not SIM_PID_PATH.exists():
    return None
  try:
    return int(SIM_PID_PATH.read_text(encoding="utf-8").strip())
  except Exception:
    return None


def _clear_sim_pid() -> None:
  try:
    if SIM_PID_PATH.exists():
      SIM_PID_PATH.unlink()
  except Exception:
    pass


def is_sim_process_running() -> bool:
  return _pid_alive(_read_sim_pid())


def is_sim_thread_running() -> bool:
  return _sim_thread is not None and _sim_thread.is_alive()


def is_sim_running() -> bool:
  return is_sim_process_running() or is_sim_thread_running()


def get_sim_status() -> dict:
  from mt5_bridge.ea_simulator import load_sim_state, sync_state_from_ea
  from mt5_bridge.protocol import BRIDGE_SIM_DIR

  # Short TTL cache — Streamlit fragments must not hammer disk every redraw
  now = time.time()
  cached = getattr(get_sim_status, "_cache", None)
  if isinstance(cached, tuple) and (now - cached[0]) < 0.4:
    return dict(cached[1])

  # Always mirror sim_control.json (EA updates bars_done/last_bar even if PID
  # detection briefly lags after Start — otherwise UI looks frozen until Refresh).
  try:
    st = sync_state_from_ea(BRIDGE_SIM_DIR, persist=False)
  except Exception:
    st = load_sim_state()
  st["running"] = is_sim_running()
  ea_st = str(st.get("ea_status") or "")
  bars_done = int(st.get("bars_done") or 0)
  bars_total = int(st.get("bars_total") or 0)
  enabled = bool(st.get("enabled"))
  # Brief PID lag after Start only — do NOT treat enabled=True alone as running
  # (that left the UI stuck “running” after a dead process / failed deploy).
  # Also require enabled so Stop (enabled=False) cannot leave a ghost running flag
  # when EA never rewrote ea_status=idle.
  if not st["running"] and enabled:
    if ea_st == "running" and (bars_done > 0 or bars_total > 0):
      st["running"] = True
    else:
      started = str(st.get("started_at") or "")
      try:
        from datetime import datetime
        ts = datetime.fromisoformat(started)
        age = abs(now - ts.timestamp())
        if age <= 8.0 and str(st.get("status") or "") == "running":
          st["running"] = True
      except Exception:
        pass
  st["runtime"] = "process" if is_sim_process_running() else (
    "thread" if is_sim_thread_running() else st.get("runtime")
  )
  st["service_pid"] = _read_sim_pid() if is_sim_process_running() else st.get("service_pid")
  # Pause = sim_control.enabled false while process still alive
  try:
    from mt5_bridge.protocol import read_sim_control
    ctrl = read_sim_control(BRIDGE_SIM_DIR) or {}
    st["paused"] = bool(st["running"] and not ctrl.get("enabled") and ctrl.get("request_id"))
  except Exception:
    st["paused"] = bool(_sim_pause.is_set()) if is_sim_thread_running() else False
  get_sim_status._cache = (now, dict(st))
  return st


def _run_sim_bridge_loop(
  stop_event: threading.Event,
  model_id: str | None,
  risk_pct: float,
  model_ids: list[str] | None = None,
) -> None:
  """BridgeEngine cycle on bridge_sim while EA feeds bars."""
  from mt5_bridge.protocol import BRIDGE_SIM_DIR, ensure_bridge_dir

  bridge_dir = ensure_bridge_dir(BRIDGE_SIM_DIR)
  ids = normalize_model_ids(model_ids, fallback=model_id or load_config().get("model_id"))
  engines = build_engines(
    ids,
    risk_pct=float(risk_pct),
    bridge_dir=bridge_dir,
    base_magic=DEFAULT_SIM_MAGIC,
  )
  primary = next(iter(engines.values()), None)
  try:
    if MT5_CACHE_PATH.exists():
      for eng in engines.values():
        eng.ensure_history()
      print(
        f"[sim-bridge] canonical history models={list(engines.keys())} "
        f"fp={primary.conditions_fp if primary else '-'}",
        flush=True,
      )
      # Pre-warm first feed week so EA is not stalled waiting on remine
      # during the first WaitDecisionForBar (felt like “treo lệnh đầu”).
      try:
        from mt5_bridge.ea_simulator import load_sim_state
        import pandas as pd
        st0 = load_sim_state()
        raw = str(st0.get("date_from") or "").replace(".", "-")[:10]
        if raw:
          ts0 = pd.Timestamp(raw)
          if ts0.tzinfo is None:
            # Match bridge bar timezone handling loosely
            pass
          for eng in engines.values():
            try:
              eng.prewarm_week(ts0)
            except Exception as e:
              print(f"[sim-bridge] prewarm {eng.model_id}: {e}", flush=True)
          print(f"[sim-bridge] prewarm done for week of {raw}", flush=True)
      except Exception as e:
        print(f"[sim-bridge] prewarm skipped: {e}", flush=True)
  except Exception as e:
    print(f"[sim-bridge] ensure_history failed: {e}", flush=True)
  last_bar_fp = None
  last_fill_fp = None
  while not stop_event.is_set():
    try:
      last_bar_fp, last_fill_fp = _cycle(engines, bridge_dir, last_bar_fp, last_fill_fp)
    except MemoryError as e:
      msg = f"sim_bridge MemoryError: {e}"
      print(f"[sim-bridge] {msg}", flush=True)
      try:
        from mt5_bridge.ea_simulator import write_sim_state
        write_sim_state({"error": msg, "status": "error"})
        write_status(
          bridge_dir,
          state="error",
          error=msg,
          model_ids=list(engines.keys()),
          **_engine_status_fields(primary),
        )
      except Exception:
        pass
      # Drop FeatureMatrix only — keep weekly strat cache (avoid mid-week remine drift)
      try:
        for eng in engines.values():
          eng._fm = None
          eng._fm_key = None
      except Exception:
        pass
      time.sleep(1.0)
    except Exception as e:
      try:
        write_status(
          bridge_dir,
          state="error",
          error=f"sim_bridge: {e}",
          model_ids=list(engines.keys()),
          **_engine_status_fields(primary),
        )
      except Exception:
        pass
      print(f"[sim-bridge] cycle error: {e}", flush=True)
      time.sleep(0.2)
    # Tight poll so HistoryFeed delay_ms is not dominated by App lag
    time.sleep(0.03)


def start_sim_worker(
  *,
  date_from: str,
  date_to: str,
  delay_ms: int = 100,
  model_id: str | None = None,
  model_ids: list[str] | None = None,
  risk_pct: float = 1.0,
  detached: bool = True,
) -> bool:
  """Start HISTORY_FEED control + bridge_sim decide loop.

  Default = detached OS process (GUI stays smooth, like Live service).
  """
  global _sim_thread, _sim_bridge_thread
  with _sim_lock:
    if is_sim_running():
      return False
    from mt5_bridge.ea_simulator import SimConfig, run_history_feed_control, write_sim_state
    from mt5_bridge.protocol import BRIDGE_SIM_DIR

    ids = normalize_model_ids(model_ids, fallback=model_id or load_config().get("model_id"))
    mid = ids[0] if ids else (model_id or load_config().get("model_id"))
    delay = max(1, int(delay_ms))
    sync_bridge_roster(
      bridge_dir=BRIDGE_SIM_DIR,
      model_ids=ids,
      risk_pct=float(risk_pct),
      base_magic=DEFAULT_SIM_MAGIC,
    )

    if detached:
      REPORT_DIR.mkdir(parents=True, exist_ok=True)
      cmd = [
        sys.executable,
        str(SIM_SERVICE_SCRIPT),
        "--from", str(date_from),
        "--to", str(date_to),
        "--delay-ms", str(delay),
        "--risk-pct", str(float(risk_pct)),
        "--bridge-dir", str(BRIDGE_SIM_DIR),
      ]
      if ids:
        cmd.extend(["--model-ids", ",".join(ids)])
      if mid:
        cmd.extend(["--model-id", str(mid)])
      logf = open(SIM_SERVICE_LOG, "a", encoding="utf-8")
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
      SIM_PID_PATH.write_text(str(proc.pid), encoding="utf-8")
      write_sim_state({
        "status": "running",
        "runtime": "process",
        "service_pid": proc.pid,
        "model_id": mid,
        "model_ids": ids,
        "date_from": date_from,
        "date_to": date_to,
        "delay_ms": delay,
        "error": None,
      })
      return True

    # Fallback: in-process threads (dev only — blocks Streamlit when remine)
    _sim_stop.clear()
    _sim_pause.clear()
    cfg = SimConfig(
      date_from=date_from,
      date_to=date_to,
      delay_ms=delay,
      model_id=mid,
      risk_pct=float(risk_pct),
      bridge_dir=BRIDGE_SIM_DIR,
    )

    def _run_control():
      try:
        run_history_feed_control(
          cfg,
          stop_event=_sim_stop,
          pause_event=_sim_pause,
        )
      except Exception as e:
        write_sim_state({"status": "error", "error": str(e)})
      finally:
        _sim_stop.set()

    _sim_bridge_thread = threading.Thread(
      target=_run_sim_bridge_loop,
      args=(_sim_stop, mid, float(risk_pct), ids),
      name="ea-history-bridge",
      daemon=True,
    )
    _sim_bridge_thread.start()
    _sim_thread = threading.Thread(target=_run_control, name="ea-history-control", daemon=True)
    _sim_thread.start()
    write_sim_state({
      "status": "running", "runtime": "thread", "model_id": mid, "model_ids": ids,
    })
    return True


def pause_sim_worker(paused: bool = True) -> None:
  """Pause/resume via sim_control.enabled (works for detached process)."""
  from mt5_bridge.ea_simulator import write_sim_state
  from mt5_bridge.protocol import BRIDGE_SIM_DIR, read_sim_control, write_sim_control

  ctrl = read_sim_control(BRIDGE_SIM_DIR) or {}
  if paused:
    write_sim_control(BRIDGE_SIM_DIR, enabled=False)
    write_sim_state({"status": "paused"})
    _sim_pause.set()
  else:
    write_sim_control(
      BRIDGE_SIM_DIR,
      enabled=True,
      request_id=ctrl.get("request_id"),
      **{
        k: ctrl[k]
        for k in ("from", "to", "delay_ms")
        if ctrl.get(k) is not None
      },
    )
    write_sim_state({"status": "running"})
    _sim_pause.clear()


def stop_sim_worker() -> None:
  global _sim_thread, _sim_bridge_thread
  _sim_stop.set()
  _sim_pause.clear()
  from mt5_bridge.ea_simulator import stop_history_feed_control, write_sim_state
  from mt5_bridge.protocol import BRIDGE_SIM_DIR
  try:
    stop_history_feed_control(BRIDGE_SIM_DIR)
  except Exception:
    pass

  pid = _read_sim_pid()
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
  _clear_sim_pid()

  for t in (_sim_thread, _sim_bridge_thread):
    if t and t.is_alive():
      t.join(timeout=5.0)
  _sim_thread = None
  _sim_bridge_thread = None
  write_sim_state({"status": "stopped", "service_pid": None})


def reset_sim_data() -> dict:
  """Stop feed if running, then wipe bridge_sim artifacts for a clean rerun."""
  if is_sim_running():
    stop_sim_worker()
  from mt5_bridge.ea_simulator import reset_sim_data as _reset
  from mt5_bridge.protocol import BRIDGE_SIM_DIR
  return _reset(BRIDGE_SIM_DIR)
