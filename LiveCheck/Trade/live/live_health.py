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
from remine_gate import gate_enabled
from runtime_host import normalize_symbol, normalize_timeframe

# EA process liveness = connection.json write age (OnTimer/OnTick), not broker tick clock.
# Heartbeat rewrite is ~2s; allow slack for disk/UI lag.
EA_WARN_SEC = 45.0
EA_STALE_SEC = 90.0
# Broker last-tick age (tick_time_msc). Stale ticks while EA file is fresh = market quiet.
TICK_WARN_SEC = 45.0
TICK_STALE_SEC = 90.0
# Worker status.json should refresh every poll cycle while running
WORKER_WARN_SEC = 90.0
WORKER_STALE_SEC = 180.0
# After EA publishes a new closed bar, App should answer within this window
DECISION_LAG_SEC = 25.0
DECISION_TIMEOUT_SEC = 45.0
HISTORY_STUCK_SEC = 300.0
# Local wall clock: Fri from this hour, Sat, Sun → expect no FX ticks.
MARKET_QUIET_FRI_HOUR = 18

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


def live_quote(conn: dict[str, Any] | None, bar: dict[str, Any] | None) -> dict[str, Any]:
  """Live bid/ask/spread from EA connection.json (tick) with bar.json fallback."""
  conn = conn if isinstance(conn, dict) else {}
  bar = bar if isinstance(bar, dict) else {}
  nested = conn.get("bar") if isinstance(conn.get("bar"), dict) else {}
  bid = conn.get("bid")
  ask = conn.get("ask")
  pts = conn.get("spread_points")
  if pts is None:
    pts = bar.get("spread_points")
  if pts is None:
    pts = nested.get("spread_points")
  digits = bar.get("digits")
  if digits is None:
    digits = conn.get("digits") or nested.get("digits")
  point = bar.get("point")
  if point is None:
    point = conn.get("point") or nested.get("point")
  try:
    if pts is None and bid is not None and ask is not None and point not in (None, "", 0, 0.0):
      pts = int(round((float(ask) - float(bid)) / float(point)))
  except (TypeError, ValueError):
    pass
  try:
    pts_n = int(pts) if pts is not None else None
  except (TypeError, ValueError):
    pts_n = None
  pips = None
  try:
    if digits is not None:
      d = int(digits)
    elif point not in (None, ""):
      d = 5 if float(point) <= 0.0001 else (3 if float(point) <= 0.01 else 2)
    else:
      d = 5
    pip_div = 10 if d in (3, 5) else 1
    if pts_n is not None:
      pips = pts_n / float(pip_div)
  except (TypeError, ValueError, ZeroDivisionError):
    pips = None
  if pips is not None:
    text = f"{pips:.1f}p".replace(".0p", "p")
  elif pts_n is not None:
    text = f"{pts_n}pts"
  else:
    text = "—"
  return {
    "bid": bid,
    "ask": ask,
    "spread_points": pts_n,
    "spread_pips": pips,
    "spread_text": text,
  }


def _in_market_quiet_window(now: datetime | None = None) -> bool:
  """Fri ≥ MARKET_QUIET_FRI_HOUR, all Saturday, all Sunday (local)."""
  ts = now or datetime.now().astimezone()
  if ts.tzinfo is None:
    ts = ts.replace(tzinfo=timezone.utc).astimezone()
  wd = int(ts.weekday())  # Mon=0 … Sun=6
  if wd >= 5:
    return True
  if wd == 4 and int(ts.hour) >= MARKET_QUIET_FRI_HOUR:
    return True
  return False


def _tick_age_seconds(conn: dict[str, Any]) -> float | None:
  raw = conn.get("tick_time_msc") if isinstance(conn, dict) else None
  if raw is None:
    return None
  try:
    return max(0.0, time.time() - (float(raw) / 1000.0))
  except (TypeError, ValueError):
    return None


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
  try:
    bstat = bridge_status(sim=sim)
  except TypeError:
    bstat = bridge_status()
  try:
    extra_workers = load_workers(sim=sim)
  except TypeError:
    extra_workers = load_workers()
  workers = list(bstat.get("workers") or extra_workers.get("workers") or [])
  bridge_running = bool(bstat.get("running"))
  remine_gate_on = bool(gate_enabled())

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

    # Split clocks: EA process write vs broker last tick (weekend quiet ≠ EA dead).
    tick_age = _tick_age_seconds(conn if isinstance(conn, dict) else {})
    conn_age = _file_age_seconds(conn_path)
    if conn_age is None:
      conn_age = _age_seconds(_parse_ts((conn or {}).get("updated_at") if isinstance(conn, dict) else None))
    # Primary "EA age" for UI = connection write freshness (process alive).
    ea_age = conn_age if conn_age is not None else _file_age_seconds(bar_path)

    bar_time_raw = bar.get("time") or bar.get("bar_time") or (conn.get("bar") or {}).get("time")
    bar_key = _norm_bar_key(bar_time_raw)
    bar_file_age = _file_age_seconds(bar_path)
    status_age = _age_seconds(_parse_ts(status.get("updated_at"))) or _file_age_seconds(status_path)
    market_quiet = _in_market_quiet_window()

    book_flags: list[str] = []
    book_level = "ok"
    sync_summary = ""
    sync_bar = None
    sync_age = None
    pending_ea_timeout = False
    history_empty = False
    book_halted = False

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
        book_halted = True
      else:
        book_halted = False

      has_ea_signal = bool(chart.get("symbol") or conn or bar)
      if ea_age is None or not has_ea_signal:
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
        # connection.json not rewritten → EA/chart truly stuck or removed
        book_level = _worst(book_level, "danger")
        book_flags.append("EA_STALE")
        ea_state = "stale"
        alerts.append({
          "level": "danger",
          "scope": "book",
          "symbol": sym_n,
          "timeframe": tf_n,
          "code": "EA_STALE",
          "message": (
            f"{sym_n} {tf_n}: EA connection {_fmt_age(ea_age)} — "
            "chart/EA có thể tắt (không ghi connection.json)"
          ),
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
        # EA alive but broker tick clock frozen (weekend / holiday / feed pause)
        if tick_age is not None and tick_age > TICK_STALE_SEC:
          book_flags.append("TICK_STALE")
          if market_quiet:
            book_flags.append("MARKET_QUIET")
            ea_state = "quiet"
            # Expected weekend — warn only, do not raise overall to danger
            book_level = _worst(book_level, "warn")
            alerts.append({
              "level": "warn",
              "scope": "book",
              "symbol": sym_n,
              "timeframe": tf_n,
              "code": "MARKET_QUIET",
              "message": (
                f"{sym_n} {tf_n}: market quiet · last tick {_fmt_age(tick_age)} "
                "(cuối tuần/không có tick — EA vẫn online)"
              ),
            })
          else:
            ea_state = "tick_stale"
            book_level = _worst(book_level, "warn")
            alerts.append({
              "level": "warn",
              "scope": "book",
              "symbol": sym_n,
              "timeframe": tf_n,
              "code": "TICK_STALE",
              "message": (
                f"{sym_n} {tf_n}: last tick {_fmt_age(tick_age)} — "
                "EA online nhưng feed/tick đứng"
              ),
            })
        elif tick_age is not None and tick_age > TICK_WARN_SEC:
          book_flags.append("TICK_SLOW")
          book_level = _worst(book_level, "warn")

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
        # HISTORY_EMPTY / HALTED are the root cause — don't also scream TIMEOUT.
        if "TIMEOUT" in sync_summary.upper() and sync_fresh and not history_empty and not book_halted:
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
    n_models = max(1, len(rows))
    # Shared FM + parallel decide: warm bars usually <25s. Keep modest headroom
    # for cold remine / first bar after Start (not a substitute for speed fixes).
    lag_lim = max(DECISION_LAG_SEC, min(45.0, 8.0 * n_models))
    timeout_lim = max(DECISION_TIMEOUT_SEC, min(90.0, 15.0 * n_models))
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
      elif book_halted:
        level = "warn"
        flags.append("HALT")
      elif not dec:
        if worker_alive and bar_key and (bar_file_age is not None and bar_file_age > timeout_lim):
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
        if lag_ref is not None and lag_ref > timeout_lim and worker_alive:
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
        elif lag_ref is not None and lag_ref > lag_lim and worker_alive:
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
      strat_src = str(dec.get("strategy_source") or "").strip().lower() or None
      # Gate OFF → do not surface remine/schedule_fallback noise (sticky decision
      # tags from an earlier gate-on remine stay in decision.json until next bar).
      if remine_gate_on and (strat_src == "remine_gate_fail" or reason == "remine_gate_fail"):
        flags.append("GATE_FAIL")
        level = _worst(level, "danger")
        alerts.append({
          "level": "danger",
          "scope": "model",
          "symbol": sym_n,
          "timeframe": tf_n,
          "model_id": mid,
          "code": "REMINE_GATE_FAIL",
          "message": (
            f"{label}: remine gate FAIL — "
            + "; ".join(str(x) for x in (dec.get("remine_gate_reasons") or ["blocked"]))
          )[:160],
        })
      elif remine_gate_on and strat_src == "schedule_fallback":
        flags.append("SCHEDULE_FALLBACK")
        level = _worst(level, "warn")
        alerts.append({
          "level": "warn",
          "scope": "model",
          "symbol": sym_n,
          "timeframe": tf_n,
          "model_id": mid,
          "code": "SCHEDULE_FALLBACK",
          "message": (
            f"{label}: remine gate fail -> using prior schedule week"
          )[:160],
        })
      elif reason in ("risk_cap", "risk_cap_error"):
        flags.append("RISK_CAP")
        level = _worst(level, "warn")
        alerts.append({
          "level": "warn",
          "scope": "model",
          "symbol": sym_n,
          "timeframe": tf_n,
          "model_id": mid,
          "code": "RISK_CAP",
          "message": (
            f"{label}: risk cap block — "
            + "; ".join(str(x) for x in (dec.get("risk_cap_reasons") or [reason]))
          )[:160],
        })
      elif strat_src == "remine":
        # Remine past schedule is normal on Live. Only surface as WARN when the
        # quality gate is ON (and passed). Gate OFF → keep src=remine in meta,
        # do not paint orange HEALTHY/OK.
        if remine_gate_on:
          flags.append("REMINE")
          level = _worst(level, "warn")
          alerts.append({
            "level": "warn",
            "scope": "model",
            "symbol": sym_n,
            "timeframe": tf_n,
            "model_id": mid,
            "code": "REMINE_OK",
            "message": f"{label}: using remined week (gate pass)",
          })
      models_out.append({
        "model_id": mid,
        "label": label,
        "magic": row.get("magic"),
        "action": action,
        "reason": reason,
        "strategy_source": strat_src,
        "remine_gate_ok": dec.get("remine_gate_ok"),
        "remine_gate_reasons": dec.get("remine_gate_reasons"),
        "risk_cap_ok": dec.get("risk_cap_ok"),
        "risk_cap_reasons": dec.get("risk_cap_reasons"),
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
      "tick_age_sec": tick_age if not sim else None,
      "tick_age": _fmt_age(tick_age) if not sim else "—",
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
    quote = live_quote(conn if isinstance(conn, dict) else {}, bar if isinstance(bar, dict) else {})
    book_row.update(quote)
    books_out.append(book_row)
    overall = _worst(overall, book_level)

  n_warn = sum(1 for a in alerts if a.get("level") == "warn")
  n_danger = sum(1 for a in alerts if a.get("level") == "danger")
  # Summary must follow `overall` (book/model level), not alerts alone —
  # soft warns (EA_SLOW, REMINE, …) can raise overall without an alert row,
  # which previously showed HEALTHY/OK text on an orange pill.
  summary = "OK"
  if not enabled:
    summary = "NO MODELS"
  elif sim:
    summary = "REPLAY"
  elif not bridge_running or overall == "muted":
    summary = "IDLE"
  elif overall == "danger" or n_danger:
    n = n_danger or sum(1 for b in books_out if b.get("level") == "danger") or 1
    summary = f"{n} ISSUE{'S' if n != 1 else ''}"
  elif overall == "warn" or n_warn:
    n = n_warn or sum(1 for b in books_out if b.get("level") == "warn") or 1
    summary = f"{n} WARN"
  elif overall == "ok":
    summary = "HEALTHY"

  remine_last = {}
  risk_cap_last = {}
  try:
    from remine_gate import load_last_alert
    remine_last = load_last_alert() or {}
  except Exception:
    remine_last = {}
  try:
    from risk_cap import load_last_alert as load_risk_cap_last
    risk_cap_last = load_risk_cap_last() or {}
  except Exception:
    risk_cap_last = {}

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
    "remine_gate_last": remine_last,
    "risk_cap_last": risk_cap_last,
  }
