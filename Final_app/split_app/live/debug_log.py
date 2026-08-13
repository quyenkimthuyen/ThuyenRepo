"""Durable debug logging for Live — support/AI diagnosis, not trader UI.

Writes append-only JSONL under ``results/debug_logs/YYYY-MM-DD/``.
Also mirrors ``mt5_bridge.comm_log.append_event`` so every bridge event is kept
beyond the short per-bridge ``comm_log.jsonl``.

Retention: prune day folders older than ``RETENTION_DAYS``.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from live_config import RESULTS_DIR

DEBUG_ROOT = RESULTS_DIR / "debug_logs"
RETENTION_DAYS = int(os.environ.get("LIVE_DEBUG_RETENTION_DAYS") or 14)
MAX_FILE_BYTES = int(os.environ.get("LIVE_DEBUG_MAX_FILE_MB") or 32) * 1024 * 1024
_LOCK = threading.Lock()
_INSTALLED = False
_LAST_EA_SYNC: dict[str, str] = {}
_PENDING_SIGNALS: dict[str, dict[str, Any]] = {}


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _day_dir(ts: datetime | None = None) -> Path:
  d = (ts or datetime.now().astimezone()).strftime("%Y-%m-%d")
  return DEBUG_ROOT / d


def book_key(symbol: str | None = None, timeframe: str | None = None, bridge_dir: Path | str | None = None) -> str:
  if symbol and timeframe:
    return f"{str(symbol).lower()}_{str(timeframe).lower()}"
  if bridge_dir:
    name = Path(bridge_dir).name.lower()
    for prefix in ("bridge_live_", "bridge_sim_live_", "bridge_"):
      if name.startswith(prefix):
        return name[len(prefix):] or name
    return name or "unknown"
  return "app"


def debug_log_paths(*, limit_days: int = 3) -> list[Path]:
  if not DEBUG_ROOT.is_dir():
    return []
  days = sorted([p for p in DEBUG_ROOT.iterdir() if p.is_dir()], reverse=True)
  out: list[Path] = []
  for day in days[: max(1, limit_days)]:
    out.extend(sorted(day.glob("*.jsonl")))
  return out


def prune_old_logs(*, retention_days: int | None = None) -> list[str]:
  keep = int(retention_days if retention_days is not None else RETENTION_DAYS)
  if keep < 1 or not DEBUG_ROOT.is_dir():
    return []
  cutoff = datetime.now().astimezone().date() - timedelta(days=keep)
  removed: list[str] = []
  for p in list(DEBUG_ROOT.iterdir()):
    if not p.is_dir():
      continue
    try:
      day = datetime.strptime(p.name, "%Y-%m-%d").date()
    except ValueError:
      continue
    if day < cutoff:
      import shutil
      shutil.rmtree(p, ignore_errors=True)
      removed.append(str(p))
  return removed


def _rotate_if_huge(path: Path) -> None:
  try:
    if path.exists() and path.stat().st_size >= MAX_FILE_BYTES:
      rotated = path.with_suffix(path.suffix + ".1")
      if rotated.exists():
        rotated.unlink()
      path.replace(rotated)
  except OSError:
    pass


def log_event(
  event: str,
  *,
  summary: str = "",
  payload: dict | None = None,
  level: str = "info",
  symbol: str | None = None,
  timeframe: str | None = None,
  bridge_dir: Path | str | None = None,
  model_id: str | None = None,
  source: str = "app",
) -> Path:
  """Append one debug row. Returns the jsonl path written."""
  key = book_key(symbol, timeframe, bridge_dir)
  day = _day_dir()
  day.mkdir(parents=True, exist_ok=True)
  # One-time README for humans / support
  readme = DEBUG_ROOT / "README.txt"
  if not readme.exists():
    readme.write_text(
      "EdgeMiner Live debug logs (for support / AI diagnosis).\n"
      "Traders normally ignore this folder.\n"
      f"Retention: {RETENTION_DAYS} days. Env LIVE_DEBUG_RETENTION_DAYS to change.\n"
      "Each line = JSON event (decision, fill, ea_sync, error, start/stop…).\n",
      encoding="utf-8",
    )
  path = day / f"{key}.jsonl"
  row = {
    "ts": _now(),
    "level": level,
    "event": event,
    "source": source,
    "book": key,
    "symbol": symbol,
    "timeframe": timeframe,
    "model_id": model_id,
    "bridge_dir": str(bridge_dir) if bridge_dir else None,
    "summary": summary or "",
    "payload": payload or {},
  }
  line = json.dumps(row, ensure_ascii=False, default=str) + "\n"
  with _LOCK:
    _rotate_if_huge(path)
    with open(path, "a", encoding="utf-8") as f:
      f.write(line)
  return path


def install_comm_log_mirror(
  *,
  symbol: str | None = None,
  timeframe: str | None = None,
) -> bool:
  """Wrap mt5_bridge.comm_log.append_event → also write durable debug_logs."""
  global _INSTALLED
  try:
    import mt5_bridge.comm_log as comm_log
  except Exception:
    return False

  # Preserve true original across re-installs (import order / worker reloads)
  original = getattr(comm_log, "_debug_log_original_append", None)
  if original is None:
    original = comm_log.append_event
    comm_log._debug_log_original_append = original  # type: ignore[attr-defined]

  def _wrapped(
    direction: str,
    event: str,
    *,
    bridge_dir=None,
    payload=None,
    summary=None,
  ):
    original(direction, event, bridge_dir=bridge_dir, payload=payload, summary=summary)
    try:
      pl = dict(payload or {})
      mid = pl.get("model_id")
      log_event(
        f"comm.{event}",
        summary=summary or f"{direction}:{event}",
        payload={"direction": direction, **pl},
        level="error" if event in ("error", "loss_guard_halt") else "info",
        symbol=symbol or pl.get("symbol"),
        timeframe=timeframe or pl.get("timeframe") or pl.get("period"),
        bridge_dir=bridge_dir,
        model_id=str(mid) if mid else None,
        source="comm_log",
      )
      action = str(pl.get("action") or "").upper()
      if event == "decision_sent" and action in ("BUY", "SELL"):
        sid = str(pl.get("signal_id") or "")
        if sid:
          _PENDING_SIGNALS[sid] = {
            "ts": _now(),
            "model_id": mid,
            "action": action,
            "bar_time": pl.get("bar_time"),
            "bridge_dir": str(bridge_dir) if bridge_dir else None,
            "symbol": symbol,
            "timeframe": timeframe,
            "reason": pl.get("reason"),
            "strategy_name": pl.get("strategy_name"),
            "entry": pl.get("entry"),
            "sl": pl.get("sl"),
            "tp": pl.get("tp"),
          }
      if event in ("fill_received", "trade_opened", "trade_closed", "fill"):
        sid = str(pl.get("signal_id") or "")
        if sid and sid in _PENDING_SIGNALS:
          pending = _PENDING_SIGNALS.pop(sid)
          log_event(
            "signal_filled",
            summary=f"fill matched {sid}",
            payload={"pending": pending, "fill": pl},
            symbol=symbol,
            timeframe=timeframe,
            bridge_dir=bridge_dir,
            model_id=str(mid or pending.get("model_id") or "") or None,
            source="debug",
          )
    except Exception:
      pass

  comm_log.append_event = _wrapped  # type: ignore[assignment]
  # Re-bind modules that imported append_event by name (stale closure otherwise)
  import sys
  for mod_name in (
    "mt5_bridge.background",
    "mt5_bridge.trade_journal",
    "mt5_bridge.loss_guard",
  ):
    mod = sys.modules.get(mod_name)
    if mod is not None and hasattr(mod, "append_event"):
      setattr(mod, "append_event", _wrapped)
  _INSTALLED = True
  return True


def log_ea_sync_if_changed(
  bridge_dir: Path | str,
  *,
  symbol: str | None = None,
  timeframe: str | None = None,
) -> dict[str, Any] | None:
  """Read ea_sync.json; log when summary/bar changes (TIMEOUT especially)."""
  bdir = Path(bridge_dir)
  path = bdir / "ea_sync.json"
  if not path.exists():
    return None
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None
  if not isinstance(data, dict):
    return None
  key = str(bdir)
  fingerprint = f"{data.get('bar_time')}|{data.get('summary')}|{data.get('model_n')}"
  if _LAST_EA_SYNC.get(key) == fingerprint:
    return data
  _LAST_EA_SYNC[key] = fingerprint
  summary = str(data.get("summary") or "")
  level = "error" if "TIMEOUT" in summary.upper() else "info"
  log_event(
    "ea_sync",
    summary=summary or "ea_sync",
    payload=data,
    level=level,
    symbol=symbol or data.get("symbol"),
    timeframe=timeframe or data.get("period"),
    bridge_dir=bdir,
    source="ea",
  )
  return data


def check_pending_signal_timeouts(*, older_than_sec: float = 120.0) -> int:
  """Log signals that never got a fill — classic 'no hit' debug trail."""
  now = datetime.now(timezone.utc)
  n = 0
  expired: list[str] = []
  for sid, pending in list(_PENDING_SIGNALS.items()):
    try:
      ts = datetime.fromisoformat(str(pending.get("ts")).replace("Z", "+00:00"))
      if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
      age = (now - ts.astimezone(timezone.utc)).total_seconds()
    except Exception:
      age = older_than_sec + 1
    if age < older_than_sec:
      continue
    expired.append(sid)
    log_event(
      "signal_no_fill",
      summary=f"NO FILL after {int(age)}s · {pending.get('action')} {sid}",
      payload=pending,
      level="warn",
      symbol=pending.get("symbol"),
      timeframe=pending.get("timeframe"),
      bridge_dir=pending.get("bridge_dir"),
      model_id=str(pending.get("model_id") or "") or None,
      source="debug",
    )
    n += 1
  for sid in expired:
    _PENDING_SIGNALS.pop(sid, None)
  return n


def support_bundle_hint() -> str:
  """Short path hint for Setup / when user asks for help."""
  prune_old_logs()
  latest = debug_log_paths(limit_days=1)
  if not latest:
    return str(DEBUG_ROOT)
  return str(DEBUG_ROOT) + f" · today {len(latest)} file(s)"
