"""Weekend / end-of-week pre-remine for the *next* broker ISO week.

Live normally remines on the first decision bar of an unseen week (often Monday
open). That overlaps the trading open and can LAG / leave gate FAIL until too
late. This module pre-mines the upcoming Monday week on Fri evening / Sat / Sun
while the market is quiet, freezes into ``*_live_weeks.json``, and leaves
Monday as a fast schedule hit (first-bar remine remains the fallback).

Disable: env ``LIVE_WEEKEND_PREREMINE=0``.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from live_config import RESULTS_DIR

STATE_PATH = RESULTS_DIR / "weekend_preremine.json"  # legacy aggregate (read-only merge)
# How often a book may retry a failed / incomplete pre-remine for the same week.
RETRY_SEC = float(os.environ.get("LIVE_WEEKEND_PREREMINE_RETRY_SEC") or 900)
# Friday local hour (inclusive) when end-of-week window opens.
FRI_START_HOUR = int(os.environ.get("LIVE_WEEKEND_PREREMINE_FRI_HOUR") or 18)


def _now_local() -> datetime:
  return datetime.now(timezone.utc).astimezone()


def _enabled() -> bool:
  env = str(os.environ.get("LIVE_WEEKEND_PREREMINE") or "").strip().lower()
  if env in ("0", "false", "no", "off"):
    return False
  if env in ("1", "true", "yes", "on"):
    return True
  return True


def _book_state_path(book: str) -> Path:
  return RESULTS_DIR / f"weekend_preremine_{book}.json"


def _read_json(path: Path) -> dict[str, Any]:
  if not path.exists():
    return {}
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
  except (OSError, json.JSONDecodeError):
    return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def _read_book_state(book: str) -> dict[str, Any]:
  """Per-book state (avoids 4 workers clobbering one shared JSON)."""
  row = _read_json(_book_state_path(book))
  if row:
    return row
  # Migrate once from legacy aggregate if present.
  legacy = (_read_json(STATE_PATH).get("books") or {}).get(book)
  return dict(legacy) if isinstance(legacy, dict) else {}


def _write_book_state(book: str, row: dict[str, Any]) -> None:
  _write_json(_book_state_path(book), row)


def load_all_preremine_state() -> dict[str, Any]:
  """Merged view for UI / debug (per-book files + legacy)."""
  books: dict[str, Any] = {}
  legacy = _read_json(STATE_PATH)
  for k, v in (legacy.get("books") or {}).items():
    if isinstance(v, dict):
      books[str(k)] = v
  for p in RESULTS_DIR.glob("weekend_preremine_*.json"):
    key = p.stem.replace("weekend_preremine_", "", 1)
    if not key or key.endswith(".json"):
      continue
    row = _read_json(p)
    if row:
      books[key] = row
  return {"books": books, "updated_at": _now_local().isoformat(timespec="seconds")}


def next_week_start(now: datetime | pd.Timestamp | None = None) -> pd.Timestamp:
  """Monday 00:00 of the *next* ISO week after ``now``'s week."""
  ts = pd.Timestamp(now or _now_local())
  if getattr(ts, "tzinfo", None) is not None:
    try:
      ts = ts.tz_convert(None)
    except Exception:
      ts = pd.Timestamp(ts.to_pydatetime().replace(tzinfo=None))
  this_mon = (ts - pd.Timedelta(days=int(ts.weekday()))).normalize()
  return this_mon + pd.Timedelta(days=7)


def in_weekend_preremine_window(now: datetime | pd.Timestamp | None = None) -> bool:
  """Fri from FRI_START_HOUR, all Saturday, all Sunday (local wall clock)."""
  ts = pd.Timestamp(now or _now_local())
  if getattr(ts, "tzinfo", None) is not None:
    try:
      ts = ts.tz_convert(None)
    except Exception:
      ts = pd.Timestamp(ts.to_pydatetime().replace(tzinfo=None))
  wd = int(ts.weekday())  # Mon=0 … Sun=6
  if wd >= 5:
    return True
  if wd == 4 and int(ts.hour) >= FRI_START_HOUR:
    return True
  return False


def weekend_preremine_target(now: datetime | pd.Timestamp | None = None) -> pd.Timestamp | None:
  """Next-week Monday if we are in the pre-remine window, else None."""
  if not _enabled():
    return None
  if not in_weekend_preremine_window(now):
    return None
  return next_week_start(now)


def _book_key(symbol: str, timeframe: str) -> str:
  return f"{str(symbol).lower()}_{str(timeframe).lower()}"


def _model_done(book_state: dict[str, Any], *, model_id: str, week: str) -> bool:
  models = book_state.get("models") or {}
  m = models.get(str(model_id)) or {}
  return str(m.get("week_start") or "") == week and bool(m.get("ok"))


def _mark_model(
  book_state: dict[str, Any],
  *,
  model_id: str,
  week: str,
  ok: bool,
  source: str,
  error: str | None = None,
  gate: dict[str, Any] | None = None,
) -> None:
  models = book_state.setdefault("models", {})
  entry: dict[str, Any] = {
    "week_start": week,
    "ok": bool(ok),
    "source": source,
    "error": error,
    "updated_at": _now_local().isoformat(timespec="seconds"),
  }
  if isinstance(gate, dict) and gate:
    metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}
    baseline = gate.get("baseline") if isinstance(gate.get("baseline"), dict) else {}
    reasons = gate.get("reasons") if isinstance(gate.get("reasons"), list) else []
    if gate.get("skipped"):
      entry["gate"] = "OFF"
    elif "ok" in gate:
      entry["gate"] = "PASS" if gate.get("ok") else "FAIL"
    if metrics:
      entry["n_trades"] = metrics.get("n_trades")
      entry["profit_factor"] = metrics.get("profit_factor")
      entry["total_r"] = metrics.get("total_r")
      entry["win_rate"] = metrics.get("win_rate")
    if baseline.get("profit_factor") is not None:
      entry["baseline_pf"] = baseline.get("profit_factor")
    if reasons:
      entry["gate_reasons"] = [str(x) for x in reasons][:6]
      if not error:
        entry["error"] = "; ".join(str(x) for x in reasons)[:240]
  models[str(model_id)] = entry
  book_state["week_start"] = week
  book_state["updated_at"] = _now_local().isoformat(timespec="seconds")


def maybe_preremine_engines(
  engines: dict[str, Any],
  *,
  symbol: str,
  timeframe: str,
  bridge_dir: Path | str | None = None,
  force: bool = False,
) -> dict[str, Any]:
  """Pre-remine next week for each engine when in weekend window.

  Safe to call often: skips when outside window, already frozen, or recently tried.
  Uses ``BridgeEngine.prewarm_week`` (same path as Live + remine gate wrap).
  """
  target = weekend_preremine_target()
  out: dict[str, Any] = {
    "ok": True,
    "skipped": True,
    "reason": "outside_window",
    "week_start": None,
    "models": [],
  }
  if target is None and not force:
    return out
  if target is None:
    target = next_week_start()

  week_s = str(target.date())
  book = _book_key(symbol, timeframe)
  book_state = _read_book_state(book)

  mids = [str(m) for m in (engines or {}).keys()]
  if not mids:
    out.update(skipped=True, reason="no_engines", week_start=week_s)
    return out

  all_done = all(
    _model_done(book_state, model_id=mid, week=week_s) for mid in mids
  )
  if all_done and not force:
    out.update(skipped=True, reason="already_done", week_start=week_s)
    return out

  last_attempt = book_state.get("last_attempt_at")
  if not force and last_attempt:
    try:
      age = (_now_local() - datetime.fromisoformat(str(last_attempt))).total_seconds()
      if age < RETRY_SEC:
        out.update(
          skipped=True,
          reason="retry_throttle",
          week_start=week_s,
          age_sec=round(age, 1),
        )
        return out
    except Exception:
      pass

  try:
    from trade_model_schedule import lookup_week_strategy
  except Exception:
    lookup_week_strategy = None  # type: ignore

  out["skipped"] = False
  out["reason"] = "run"
  out["week_start"] = week_s
  results: list[dict[str, Any]] = []
  any_work = False

  for mid, eng in (engines or {}).items():
    mid_s = str(mid)
    row: dict[str, Any] = {"model_id": mid_s, "week_start": week_s}
    try:
      if lookup_week_strategy is not None:
        hit = lookup_week_strategy(eng.model_id, target)
        if hit and isinstance(hit.get("strategy"), dict):
          # Ensure in-memory cache is warm for Monday
          eng.prewarm_week(target)
          src = "schedule_hit"
          row.update(ok=True, source=src, action="cache_warm")
          _mark_model(book_state, model_id=mid_s, week=week_s, ok=True, source=src)
          results.append(row)
          continue
      if _model_done(book_state, model_id=mid_s, week=week_s) and not force:
        row.update(ok=True, source="state_done", action="skip")
        results.append(row)
        continue

      any_work = True
      print(
        f"[weekend_preremine] {symbol} {timeframe} model={mid_s} week={week_s} …",
        flush=True,
      )
      t0 = time.time()
      eng.prewarm_week(target)
      dt = round(time.time() - t0, 2)
      src = str(getattr(eng, "_last_strategy_source", None) or "remine")
      gate = getattr(eng, "_last_remine_gate", None)
      ok = src not in ("remine_gate_fail", "none")
      row.update(
        ok=ok,
        source=src,
        action="prewarm",
        duration_sec=dt,
        gate_ok=(gate or {}).get("ok") if isinstance(gate, dict) else None,
        gate_reasons=(gate or {}).get("reasons") if isinstance(gate, dict) else None,
        metrics=(gate or {}).get("metrics") if isinstance(gate, dict) else None,
      )
      _mark_model(
        book_state,
        model_id=mid_s,
        week=week_s,
        ok=ok,
        source=src,
        error=None if ok else ",".join(str(x) for x in ((gate or {}).get("reasons") or [])),
        gate=gate if isinstance(gate, dict) else None,
      )
      print(
        f"[weekend_preremine] {symbol} {timeframe} model={mid_s} "
        f"week={week_s} src={src} ok={ok} {dt}s",
        flush=True,
      )
    except Exception as exc:
      any_work = True
      row.update(ok=False, source="error", error=str(exc)[:240])
      _mark_model(
        book_state, model_id=mid_s, week=week_s, ok=False, source="error", error=str(exc)[:240],
      )
      print(
        f"[weekend_preremine] {symbol} {timeframe} model={mid_s} FAIL: {exc}",
        flush=True,
      )
    results.append(row)

  book_state["last_attempt_at"] = _now_local().isoformat(timespec="seconds")
  book_state["week_start"] = week_s
  _write_book_state(book, book_state)

  out["models"] = results
  out["ok"] = all(bool(r.get("ok")) for r in results) if results else True
  out["any_work"] = any_work

  if any_work or results:
    try:
      from debug_log import log_event
      log_event(
        "weekend_preremine",
        summary=(
          f"{symbol} {timeframe} week={week_s} "
          f"ok={out['ok']} n={len(results)} work={any_work}"
        ),
        payload={
          "week_start": week_s,
          "symbol": symbol,
          "timeframe": timeframe,
          "models": results,
          "ok": out["ok"],
        },
        symbol=symbol,
        timeframe=timeframe,
        bridge_dir=bridge_dir,
        level="info" if out["ok"] else "warn",
        source="weekend_preremine",
      )
    except Exception:
      pass

  return out
