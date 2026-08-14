"""Live pipeline health — per book / per model freshness & stuck signals."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from books import bridge_dir, bridge_subdir, group_models_by_book
from bridge_control import load_workers, status as bridge_status
from chart_validate import read_chart_identity
from live_config import RESULTS_DIR
from package_store import load_roster
from runtime_host import normalize_symbol, normalize_timeframe

# Heartbeat is ~2s; allow slack for disk/UI lag
EA_WARN_SEC = 45.0
EA_STALE_SEC = 90.0
# Worker status.json should refresh every poll cycle while running
WORKER_WARN_SEC = 90.0
WORKER_STALE_SEC = 180.0
# After EA publishes a new closed bar, App should answer within this window
DECISION_LAG_SEC = 25.0
DECISION_TIMEOUT_SEC = 45.0
HISTORY_STUCK_SEC = 300.0

TF_SECONDS = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600}


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _fmt_sync_summary(raw: str) -> str:
  """Normalize EA ANSI mojibake for UI (Vietnamese was written as FILE_ANSI)."""
  s = str(raw or "").strip()
  if not s:
    return s
  # Common corruption of "App chậm / worker tắt?" (and ASCII "?" replacements)
  low = s.lower()
  if ("app ch" in low or "app slow" in low) and "worker" in low:
    if "TIMEOUT" in s.upper():
      head = s.split("|", 1)[0].strip()
      return f"{head} | App slow / worker down?"
    return "App slow / worker down?"
  return s


def _tf_bar_seconds(tf: str) -> float:
  return float(TF_SECONDS.get(str(tf).upper(), 300))


def _parse_ts(raw: Any) -> datetime | None:
  if not raw:
    return None
  if isinstance(raw, datetime):
    return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
  s = str(raw).strip()
  if not s:
    return None
  try:
    if s.endswith("Z"):
      s = s[:-1] + "+00:00"
    # EA TimeToString often "YYYY.MM.DD HH:MM"
    if "." in s[:10] and s[4] == ".":
      s = s.replace(".", "-", 2)
    return datetime.fromisoformat(s)
  except ValueError:
    return None


def _age_seconds(ts: datetime | None) -> float | None:
  if ts is None:
    return None
  now = datetime.now(timezone.utc)
  if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc)
  return max(0.0, (now - ts.astimezone(timezone.utc)).total_seconds())


def _file_age_seconds(path: Path) -> float | None:
  try:
    if not path.exists():
      return None
    return max(0.0, time.time() - path.stat().st_mtime)
  except OSError:
    return None


def _fmt_age(sec: float | None) -> str:
  if sec is None:
    return "—"
  if sec < 5:
    return "now"
  if sec < 60:
    return f"{int(sec)}s"
  if sec < 3600:
    return f"{int(sec // 60)}m"
  return f"{int(sec // 3600)}h"


def _norm_bar_key(raw: Any) -> str | None:
  ts = _parse_ts(raw)
  if ts is None:
    s = str(raw or "").strip()
    return s or None
  if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc)
  local = ts.astimezone()
  return local.strftime("%Y-%m-%d %H:%M")


def _severity_rank(level: str) -> int:
  return {"ok": 0, "warn": 1, "danger": 2, "muted": -1}.get(level, 0)


def _worst(*levels: str) -> str:
  best = "ok"
  for lv in levels:
    if _severity_rank(lv) > _severity_rank(best):
      best = lv
  return best


def _load_decisions_by_model(bdir: Path) -> dict[str, dict]:
  out: dict[str, dict] = {}
  primary = _read(bdir / "decision.json")
  if isinstance(primary, dict):
    mid = str(primary.get("model_id") or "")
    if mid:
      out[mid] = {**primary, "_file": "decision.json"}
  dec_dir = bdir / "decisions"
  if dec_dir.is_dir():
    for p in sorted(dec_dir.glob("*.json")):
      data = _read(p)
      if not isinstance(data, dict):
        continue
      mid = str(data.get("model_id") or p.stem)
      out[mid] = {**data, "_file": p.name, "_path": str(p)}
  return out


def _worker_for_book(
  workers: list[dict],
  symbol: str,
  timeframe: str,
) -> dict | None:
  sym = normalize_symbol(symbol)
  tf = normalize_timeframe(timeframe)
  for w in workers:
    if normalize_symbol(w.get("symbol")) == sym and normalize_timeframe(w.get("timeframe")) == tf:
      return w
  return None


def build_live_health(*, sim: bool = False) -> dict[str, Any]:
  """Snapshot pipeline health for enabled roster books/models."""
  roster = load_roster()
  enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
  groups = group_models_by_book(enabled)
  bstat = bridge_status()
  workers = list(bstat.get("workers") or load_workers().get("workers") or [])
  bridge_running = bool(bstat.get("running")) if not sim else False

  books_out: list[dict[str, Any]] = []
  alerts: list[dict[str, Any]] = []
  overall = "muted" if not enabled else ("ok" if (bridge_running or sim) else "muted")

  for (sym, tf), rows in groups.items():
    sym_n = normalize_symbol(sym)
    tf_n = normalize_timeframe(tf)
    bdir = bridge_dir(sym_n, tf_n, sim=bool(sim))
    sub = bridge_subdir(sym_n, tf_n, sim=bool(sim))
    worker = _worker_for_book(workers, sym_n, tf_n)
    worker_alive = bool(worker and worker.get("alive"))
    status = _read(bdir / "status.json") or {}
    conn = _read(bdir / "connection.json") or {}
    bar = _read(bdir / "bar.json") or {}
    hist = _read(bdir / "history_status.json") or {}
    ea_sync = _read(bdir / "ea_sync.json") or {}
    chart = read_chart_identity(bdir)

    conn_path = bdir / "connection.json"
    bar_path = bdir / "bar.json"
    status_path = bdir / "status.json"

    # Prefer EA tick clock, then file mtime
    ea_age = None
    if isinstance(conn, dict) and conn.get("tick_time_msc"):
      try:
        ea_age = max(0.0, time.time() - (float(conn["tick_time_msc"]) / 1000.0))
      except (TypeError, ValueError):
        ea_age = None
    if ea_age is None:
      ea_age = _file_age_seconds(conn_path)
    if ea_age is None:
      ea_age = _file_age_seconds(bar_path)

    bar_time_raw = bar.get("time") or bar.get("bar_time") or (conn.get("bar") or {}).get("time")
    bar_key = _norm_bar_key(bar_time_raw)
    bar_file_age = _file_age_seconds(bar_path)
    status_age = _age_seconds(_parse_ts(status.get("updated_at"))) or _file_age_seconds(status_path)

    book_flags: list[str] = []
    book_level = "ok"
    sync_summary = ""
    sync_bar = None
    sync_age = None
    pending_ea_timeout = False
    history_empty = False

    if sim:
      book_level = "ok"
      ea_state = "replay"
    elif not bridge_running:
      book_level = "muted"
      ea_state = "idle"
      book_flags.append("IDLE")
    else:
      if not worker_alive:
        book_level = _worst(book_level, "danger")
        book_flags.append("WORKER_DOWN")
        alerts.append({
          "level": "danger",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": "WORKER_DOWN",
          "message": f"{sym_n} {tf_n}: worker không chạy",
        })
      elif status_age is not None and status_age > WORKER_STALE_SEC:
        book_level = _worst(book_level, "danger")
        book_flags.append("WORKER_STALE")
        alerts.append({
          "level": "danger",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": "WORKER_STALE",
          "message": f"{sym_n} {tf_n}: status.json { _fmt_age(status_age) } — worker có thể kẹt",
        })
      elif status_age is not None and status_age > WORKER_WARN_SEC:
        book_level = _worst(book_level, "warn")
        book_flags.append("WORKER_SLOW")

      st = str(status.get("state") or "").lower()
      if st in ("error", "halted"):
        book_level = _worst(book_level, "danger")
        book_flags.append(st.upper())
        alerts.append({
          "level": "danger",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": st.upper(),
          "message": f"{sym_n} {tf_n}: state={st} · {status.get('error') or status.get('reason') or '—'}",
        })

      if ea_age is None or not (chart.get("symbol") or conn or bar):
        book_level = _worst(book_level, "danger")
        book_flags.append("EA_OFFLINE")
        alerts.append({
          "level": "danger",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": "EA_OFFLINE",
          "message": f"{sym_n} {tf_n}: không thấy EA heartbeat ({sub})",
        })
        ea_state = "offline"
      elif ea_age > EA_STALE_SEC:
        book_level = _worst(book_level, "danger")
        book_flags.append("EA_STALE")
        ea_state = "stale"
        alerts.append({
          "level": "danger",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": "EA_STALE",
          "message": f"{sym_n} {tf_n}: EA heartbeat {_fmt_age(ea_age)} — có thể kẹt/chart tắt",
        })
      elif ea_age > EA_WARN_SEC:
        book_level = _worst(book_level, "warn")
        book_flags.append("EA_SLOW")
        ea_state = "slow"
      else:
        ea_state = "online"
        if conn.get("connected") is False:
          book_level = _worst(book_level, "warn")
          book_flags.append("TERMINAL_DISC")

      hist_state = str(hist.get("state") or "").lower()
      hist_age = _age_seconds(_parse_ts(hist.get("updated_at")))
      hist_bars = int(hist.get("stored_bars") or hist.get("received_bars") or 0)
      cache_path = RESULTS_DIR / "data" / f"mt5_{sym_n.lower()}_{tf_n.lower()}.parquet"
      history_empty = (
        worker_alive
        and (
          st == "syncing_history"
          or (not cache_path.exists())
          or (hist_state in ("completed", "error") and hist_bars <= 0 and not cache_path.exists())
        )
      )
      if history_empty:
        book_level = _worst(book_level, "danger")
        book_flags.append("HISTORY_EMPTY")
        alerts.append({
          "level": "danger",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": "HISTORY_EMPTY",
          "message": (
            f"{sym_n} {tf_n}: chưa có MT5 history cache "
            f"(state={st or hist_state or '—'}; EA export 0 bar?)"
          ),
        })
      elif hist_state in ("requesting", "waiting") and hist_age is not None and hist_age > HISTORY_STUCK_SEC:
        book_level = _worst(book_level, "warn")
        book_flags.append("HISTORY_STUCK")
        alerts.append({
          "level": "warn",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": "HISTORY_STUCK",
          "message": f"{sym_n} {tf_n}: history sync {hist_state} {_fmt_age(hist_age)}",
        })

      # EA ea_sync.json — last closed-bar handshake written by ForgeBridgeLive
      sync_age = _age_seconds(_parse_ts(ea_sync.get("updated_at"))) or _file_age_seconds(bdir / "ea_sync.json")
      sync_summary = _fmt_sync_summary(str(ea_sync.get("summary") or ""))
      sync_bar = _norm_bar_key(ea_sync.get("bar_time"))
      pending_ea_timeout = False
      if isinstance(ea_sync, dict) and ea_sync:
        # Sticky TIMEOUT from a past remine/boot must not stay danger forever.
        sync_fresh = sync_age is not None and sync_age < max(120.0, _tf_bar_seconds(tf_n) * 2)
        # HISTORY_EMPTY is the root cause — don't also scream TIMEOUT.
        if "TIMEOUT" in sync_summary.upper() and sync_fresh and not history_empty:
          pending_ea_timeout = True
        if sync_bar and bar_key and sync_bar != bar_key and (bar_file_age or 0) > DECISION_LAG_SEC:
          book_level = _worst(book_level, "warn")
          book_flags.append("EA_SYNC_LAG")
      else:
        sync_summary = ""
        sync_bar = None
        sync_age = None

    decisions = _load_decisions_by_model(bdir)
    models_out: list[dict[str, Any]] = []
    for row in rows:
      mid = str(row.get("model_id") or "")
      label = row.get("label") or mid
      dec = decisions.get(mid) or {}
      # fallback: single-model primary file without model_id
      if not dec and len(rows) == 1 and decisions:
        dec = next(iter(decisions.values()))

      dec_bar = _norm_bar_key(dec.get("bar_time") or dec.get("time"))
      dec_age = _age_seconds(_parse_ts(dec.get("updated_at")))
      if dec_age is None and dec.get("_path"):
        dec_age = _file_age_seconds(Path(dec["_path"]))
      action = str(dec.get("action") or "—").upper()
      matched = bool(bar_key and dec_bar and bar_key == dec_bar)
      # Also accept when decision has no bar_time but was updated after bar file
      flags: list[str] = []
      level = "ok"

      if sim:
        level = "ok"
      elif not bridge_running:
        level = "muted"
      elif not dec:
        if worker_alive and bar_key and (bar_file_age is not None and bar_file_age > DECISION_TIMEOUT_SEC):
          level = "danger"
          flags.append("NO_DECISION")
          alerts.append({
            "level": "danger",
            "scope": "model",
            "symbol": sym_n,
            "timeframe": tf_n,
            "model_id": mid,
            "code": "NO_DECISION",
            "message": f"{label}: không có decision sau bar {bar_key}",
          })
        elif worker_alive:
          level = "warn"
          flags.append("WAITING")
        else:
          level = "muted"
          flags.append("NO_DECISION")
      elif bar_key and dec_bar and not matched:
        lag_ref = bar_file_age
        if lag_ref is not None and lag_ref > DECISION_TIMEOUT_SEC and worker_alive:
          level = "danger"
          flags.append("TIMEOUT")
          alerts.append({
            "level": "danger",
            "scope": "model",
            "symbol": sym_n,
            "timeframe": tf_n,
            "model_id": mid,
            "code": "TIMEOUT",
            "message": (
              f"{label}: decision kẹt bar {dec_bar} · EA bar {bar_key} "
              f"(+{_fmt_age(lag_ref)})"
            ),
          })
        elif lag_ref is not None and lag_ref > DECISION_LAG_SEC and worker_alive:
          level = "warn"
          flags.append("LAG")
          alerts.append({
            "level": "warn",
            "scope": "model",
            "symbol": sym_n,
            "timeframe": tf_n,
            "model_id": mid,
            "code": "LAG",
            "message": f"{label}: đang chậm vs bar {bar_key} (decision {dec_bar})",
          })
        else:
          flags.append("CATCHING_UP")
      elif dec.get("halt"):
        level = "warn"
        flags.append("HALT")

      reason = str(dec.get("reason") or dec.get("halt_source") or "")[:80]
      models_out.append({
        "model_id": mid,
        "label": label,
        "magic": row.get("magic"),
        "action": action,
        "reason": reason,
        "bar_time": dec_bar or dec.get("bar_time"),
        "decision_age_sec": dec_age,
        "decision_age": _fmt_age(dec_age),
        "matched_bar": matched,
        "flags": flags,
        "level": level,
        "ok": level == "ok",
      })
      book_level = _worst(book_level, level)

    if pending_ea_timeout:
      # Decisions may arrive after EA's wait budget — if all models match sync/current bar,
      # treat as healthy (sticky ea_sync TIMEOUT must not keep alarming).
      caught = False
      match_bar = sync_bar or bar_key
      if match_bar and rows:
        caught = all(
          _norm_bar_key(
            (decisions.get(str(r.get("model_id") or "")) or {}).get("bar_time")
            or (decisions.get(str(r.get("model_id") or "")) or {}).get("time")
          )
          == match_bar
          for r in rows
        )
      if caught:
        sync_summary = "SYNC OK | late catch-up"
        # Drop TIMEOUT from book flags — pipeline is caught up.
      else:
        # Soften: worker alive + decisions arriving (any model matched) → warn, not danger.
        any_matched = any(
          _norm_bar_key(
            (decisions.get(str(r.get("model_id") or "")) or {}).get("bar_time")
            or (decisions.get(str(r.get("model_id") or "")) or {}).get("time")
          )
          == match_bar
          for r in rows
        ) if match_bar and rows else False
        if worker_alive and any_matched:
          book_level = _worst(book_level, "warn")
          book_flags.append("EA_SYNC_LATE")
          alerts.append({
            "level": "warn",
            "scope": "book",
            "symbol": sym_n,
            "timeframe": tf_n,
            "code": "EA_SYNC_LATE",
            "message": f"{sym_n} {tf_n}: EA sync late — {sync_summary}",
          })
        else:
          book_level = _worst(book_level, "danger")
          book_flags.append("EA_SYNC_TIMEOUT")
          alerts.append({
            "level": "danger",
            "scope": "book",
            "symbol": sym_n,
            "timeframe": tf_n,
            "code": "EA_SYNC_TIMEOUT",
            "message": f"{sym_n} {tf_n}: EA sync {sync_summary}",
          })

    book_row = {
      "symbol": sym_n,
      "timeframe": tf_n,
      "bridge_subdir": sub,
      "bridge_dir": str(bdir),
      "worker_alive": worker_alive,
      "worker_pid": (worker or {}).get("pid"),
      "status_state": status.get("state") or ("—" if not status else "unknown"),
      "status_error": status.get("error") or status.get("reason"),
      "status_age_sec": status_age,
      "status_age": _fmt_age(status_age),
      "ea_state": ea_state if not sim else "replay",
      "ea_age_sec": ea_age,
      "ea_age": _fmt_age(ea_age),
      "bar_time": bar_key or bar_time_raw,
      "bar_age_sec": bar_file_age,
      "bar_age": _fmt_age(bar_file_age),
      "history_state": hist.get("state"),
      "ea_sync_summary": sync_summary or None,
      "ea_sync_bar": sync_bar,
      "ea_sync_age": _fmt_age(sync_age),
      "flags": book_flags,
      "level": book_level,
      "models": models_out,
      "n_models": len(models_out),
    }
    books_out.append(book_row)
    overall = _worst(overall, book_level)

  n_warn = sum(1 for a in alerts if a.get("level") == "warn")
  n_danger = sum(1 for a in alerts if a.get("level") == "danger")
  summary = "OK"
  if not enabled:
    summary = "NO MODELS"
  elif sim:
    summary = "REPLAY"
  elif not bridge_running:
    summary = "IDLE"
  elif n_danger:
    summary = f"{n_danger} ISSUE{'S' if n_danger != 1 else ''}"
  elif n_warn:
    summary = f"{n_warn} WARN"
  else:
    summary = "HEALTHY"

  return {
    "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "sim": bool(sim),
    "bridge_running": bridge_running,
    "overall": overall,
    "summary": summary,
    "n_books": len(books_out),
    "n_alerts": len(alerts),
    "n_warn": n_warn,
    "n_danger": n_danger,
    "alerts": alerts[:20],
    "books": books_out,
  }
