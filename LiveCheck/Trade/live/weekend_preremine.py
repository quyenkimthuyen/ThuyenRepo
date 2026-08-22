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


def _legacy_state_path() -> Path:
  return RESULTS_DIR / "weekend_preremine.json"


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
  legacy = (_read_json(_legacy_state_path()).get("books") or {}).get(book)
  return dict(legacy) if isinstance(legacy, dict) else {}


def _write_book_state(book: str, row: dict[str, Any]) -> None:
  _write_json(_book_state_path(book), row)


def load_all_preremine_state() -> dict[str, Any]:
  """Merged view for UI / debug (per-book files + legacy)."""
  books: dict[str, Any] = {}
  legacy = _read_json(_legacy_state_path())
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


def _book_key(symbol: str, timeframe: str) -> str:
  return f"{str(symbol).lower()}_{str(timeframe).lower()}"


def _live_model_index(live_models: list[dict[str, Any]] | None) -> dict[str, dict[str, dict[str, Any]]]:
  """book -> model_id -> row (symbol/timeframe/model_id/installed_at)."""
  index: dict[str, dict[str, dict[str, Any]]] = {}
  for m in live_models or []:
    if not isinstance(m, dict):
      continue
    sym = str(m.get("symbol") or "").strip().lower()
    tf = str(m.get("timeframe") or "").strip().lower()
    mid = str(m.get("model_id") or m.get("id") or "").strip()
    if not (sym and tf and mid):
      continue
    book = _book_key(sym, tf)
    prev = (index.get(book) or {}).get(mid) or {}
    merged = dict(prev)
    merged.update({k: v for k, v in m.items() if v not in (None, "")})
    index.setdefault(book, {})[mid] = merged
  return index


def _resolve_live_models(live_models: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
  if live_models is not None:
    return list(live_models)
  rows: list[dict[str, Any]] = []
  try:
    from package_store import list_installed, load_roster
    rows.extend(list_installed())
    for m in (load_roster().get("models") or []):
      if isinstance(m, dict):
        rows.append(m)
  except Exception:
    pass
  return rows


def _is_reimported(entry: dict[str, Any], live_row: dict[str, Any]) -> bool:
  """True when the package on disk is newer than this pre-remine freeze."""
  inst = str(live_row.get("installed_at") or "").strip()
  upd = str(entry.get("updated_at") or "").strip()
  if not inst or not upd:
    return False
  return inst > upd


def drop_preremine_model(symbol: str, timeframe: str, model_id: str) -> bool:
  """Remove one model from per-book + legacy pre-remine state (fresh import)."""
  book = _book_key(symbol, timeframe)
  mid = str(model_id or "").strip()
  if not mid:
    return False
  dropped = False
  row = _read_book_state(book)
  models = dict(row.get("models") or {})
  if mid in models:
    models.pop(mid, None)
    dropped = True
    if models:
      row["models"] = models
      row["updated_at"] = _now_local().isoformat(timespec="seconds")
      _write_book_state(book, row)
    else:
      path = _book_state_path(book)
      if path.exists():
        path.unlink()
  legacy = _read_json(_legacy_state_path())
  books = dict(legacy.get("books") or {})
  brow = books.get(book)
  if isinstance(brow, dict):
    lmodels = dict(brow.get("models") or {})
    if mid in lmodels:
      lmodels.pop(mid, None)
      dropped = True
      if lmodels:
        brow = dict(brow)
        brow["models"] = lmodels
        books[book] = brow
      else:
        books.pop(book, None)
      legacy["books"] = books
      legacy["updated_at"] = _now_local().isoformat(timespec="seconds")
      _write_json(_legacy_state_path(), legacy)
  return dropped


def prune_preremine_to_live_models(
  live_models: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
  """Drop pre-remine rows for removed packages (and re-imported same ids).

  Re-import: ``installed_at`` newer than the freeze ``updated_at`` → PENDING
  until the weekend worker runs again.
  """
  index = _live_model_index(_resolve_live_models(live_models))
  dropped: list[dict[str, str]] = []

  def _filter_models(book: str, models: dict[str, Any]) -> dict[str, Any]:
    keep: dict[str, Any] = {}
    for mid, info in (models or {}).items():
      mid_s = str(mid)
      live_row = (index.get(book) or {}).get(mid_s)
      if not live_row:
        dropped.append({"book": book, "model_id": mid_s, "reason": "removed"})
        continue
      if isinstance(info, dict) and _is_reimported(info, live_row):
        dropped.append({"book": book, "model_id": mid_s, "reason": "reimport"})
        continue
      keep[mid_s] = info
    return keep

  for p in list(RESULTS_DIR.glob("weekend_preremine_*.json")):
    book = p.stem.replace("weekend_preremine_", "", 1)
    if not book:
      continue
    row = _read_json(p)
    keep = _filter_models(book, dict(row.get("models") or {}))
    if not keep:
      p.unlink(missing_ok=True)
      continue
    if keep != (row.get("models") or {}):
      row["models"] = keep
      row["updated_at"] = _now_local().isoformat(timespec="seconds")
      _write_json(p, row)

  legacy = _read_json(_legacy_state_path())
  if legacy:
    books = dict(legacy.get("books") or {})
    new_books: dict[str, Any] = {}
    for book, brow in books.items():
      if not isinstance(brow, dict):
        continue
      keep = _filter_models(str(book), dict(brow.get("models") or {}))
      if not keep:
        continue
      nb = dict(brow)
      nb["models"] = keep
      new_books[str(book)] = nb
    if new_books != books:
      legacy["books"] = new_books
      legacy["updated_at"] = _now_local().isoformat(timespec="seconds")
      _write_json(_legacy_state_path(), legacy)

  return {"dropped": dropped, "kept_books": sorted(index.keys())}


def this_week_start(now: datetime | pd.Timestamp | None = None) -> pd.Timestamp:
  """Monday 00:00 of the ISO week containing ``now`` (local)."""
  ts = pd.Timestamp(now or _now_local())
  if getattr(ts, "tzinfo", None) is not None:
    try:
      ts = ts.tz_convert(None)
    except Exception:
      ts = pd.Timestamp(ts.to_pydatetime().replace(tzinfo=None))
  return (ts - pd.Timedelta(days=int(ts.weekday()))).normalize()


def next_week_start(now: datetime | pd.Timestamp | None = None) -> pd.Timestamp:
  """Monday 00:00 of the *next* ISO week after ``now``'s week."""
  return this_week_start(now) + pd.Timedelta(days=7)


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


def quality_status_week(
  now: datetime | pd.Timestamp | None = None,
) -> tuple[str, str]:
  """Week the Quality table should show: trading week, or next week when pre-remining.

  Returns ``(week_start_iso, mode)`` with mode ``trading`` or ``preremine``.
  """
  tgt = weekend_preremine_target(now)
  if tgt is not None:
    return str(tgt.date()), "preremine"
  return str(this_week_start(now).date()), "trading"


def freeze_info_for_week(model_id: str, week: str) -> dict[str, Any]:
  """Live freeze / package schedule row for one ISO week (Quality table)."""
  mid = str(model_id or "").strip()
  week_s = str(week or "")[:10]
  if not mid or not week_s:
    return {}
  live = _read_json(RESULTS_DIR / "trade_models" / f"{mid}_live_weeks.json")
  meta = live.get("meta") if isinstance(live.get("meta"), dict) else {}
  for row in live.get("weekly") or []:
    if not (isinstance(row, dict) and str(row.get("week_start") or "")[:10] == week_s):
      continue
    if not isinstance(row.get("strategy"), dict):
      continue
    raw_src = str(meta.get("source") or row.get("source") or "live_remine")
    if raw_src in ("live_remine", "remine", "weekend_preremine"):
      source = "remine"
    elif "schedule" in raw_src:
      source = "schedule_hit"
    else:
      source = raw_src
    return {
      "week_start": week_s,
      "ok": True,
      "source": source,
      "updated_at": live.get("updated_at") or meta.get("updated_at"),
    }
  sched = _read_json(RESULTS_DIR / "trade_models" / f"{mid}_schedule.json")
  for row in sched.get("weekly") or []:
    if isinstance(row, dict) and str(row.get("week_start") or "")[:10] == week_s:
      if isinstance(row.get("strategy"), dict):
        return {"week_start": week_s, "ok": True, "source": "schedule_hit"}
  return {}


def _fmt_quality_num(v: Any, digits: int = 2) -> str:
  if v is None or v == "":
    return "—"
  try:
    x = float(v)
    if x != x:
      return "—"
    if abs(x - round(x)) < 1e-9:
      return str(int(round(x)))
    return f"{x:.{digits}f}"
  except (TypeError, ValueError):
    return str(v)


def build_quality_status_table() -> dict[str, Any]:
  """Rows for Setup Quality / Live remine status (current trading week, or next when pre-remining)."""
  week, mode = quality_status_week()
  books = (load_all_preremine_state().get("books") or {})
  gate_by_model: dict[str, dict] = {}
  try:
    from remine_gate import load_gate_by_model_week
    gate_by_model = load_gate_by_model_week(week)
  except Exception:
    gate_by_model = {}

  roster_rows: list[dict[str, Any]] = []
  try:
    from package_store import load_roster
    for m in (load_roster().get("models") or []):
      if not m.get("enabled", True):
        continue
      sym = str(m.get("symbol") or "").upper()
      tf = str(m.get("timeframe") or "").upper()
      mid = str(m.get("model_id") or m.get("id") or "")
      if not (sym and tf and mid):
        continue
      roster_rows.append({
        "book": f"{sym.lower()}_{tf.lower()}",
        "model_id": mid,
        "label": str(m.get("label") or mid),
      })
  except Exception:
    roster_rows = []

  by_book_model: dict[tuple[str, str], dict] = {}
  for bk, row in books.items():
    for mid, info in (row.get("models") or {}).items():
      by_book_model[(str(bk), str(mid))] = dict(info or {})

  def _row(book: str, label: str, mid: str, info: dict, pr_status: str) -> dict[str, Any]:
    src = str(info.get("source") or "—")
    gate_row = gate_by_model.get(mid) or {}
    metrics: dict[str, Any] = {}
    if info.get("n_trades") is not None or info.get("profit_factor") is not None:
      metrics = {
        "n_trades": info.get("n_trades"),
        "profit_factor": info.get("profit_factor"),
        "total_r": info.get("total_r"),
      }
    elif isinstance(gate_row.get("metrics"), dict) and str(gate_row.get("week_start") or "") == week:
      metrics = gate_row.get("metrics") or {}
    baseline_pf = info.get("baseline_pf")
    if baseline_pf is None and isinstance(gate_row.get("baseline"), dict):
      if str(gate_row.get("week_start") or "") == week:
        baseline_pf = (gate_row.get("baseline") or {}).get("profit_factor")
    gate_label = info.get("gate")
    if not gate_label:
      if src in ("schedule_hit", "state_done"):
        gate_label = "—"
      elif isinstance(gate_row, dict) and str(gate_row.get("week_start") or "") == week and "ok" in gate_row:
        gate_label = "PASS" if gate_row.get("ok") else "FAIL"
      elif src == "remine":
        gate_label = "PASS"
      elif src == "schedule_fallback":
        gate_label = "FAIL"
      else:
        gate_label = "—"
    reasons = info.get("gate_reasons") or info.get("error")
    if (not reasons or reasons == "—") and gate_row.get("reasons") and str(gate_row.get("week_start") or "") == week:
      reasons = "; ".join(str(x) for x in (gate_row.get("reasons") or []))
    if isinstance(reasons, list):
      reasons = "; ".join(str(x) for x in reasons)
    return {
      "book": book,
      "model": label,
      "week": str(info.get("week_start") or "—") if info else "—",
      "status": pr_status,
      "source": src,
      "gate": gate_label,
      "n": _fmt_quality_num(metrics.get("n_trades"), 0),
      "PF": _fmt_quality_num(metrics.get("profit_factor"), 2),
      "R": _fmt_quality_num(metrics.get("total_r"), 1),
      "base_PF": _fmt_quality_num(baseline_pf, 2),
      "reason": (str(reasons or "").strip() or "—")[:100],
      "updated": str(info.get("updated_at") or "—")[:19] if info else "—",
    }

  status_rows: list[dict[str, Any]] = []
  for rr in roster_rows:
    key = (rr["book"], rr["model_id"])
    info = by_book_model.get(key) or {}
    w = str(info.get("week_start") or "")
    if w != week:
      freeze = freeze_info_for_week(rr["model_id"], week)
      if freeze:
        info = freeze
        w = str(info.get("week_start") or "")
    if info and w == week and info.get("ok"):
      pr_status = "READY"
    elif info and w == week and info.get("ok") is False:
      pr_status = "FAIL"
    elif info and w and w != week:
      pr_status = "STALE"
    elif info:
      pr_status = "PARTIAL"
    else:
      pr_status = "PENDING"
    status_rows.append(_row(rr["book"], rr["label"], rr["model_id"], info, pr_status))

  ready_n = sum(1 for r in status_rows if r["status"] == "READY")
  return {
    "week": week,
    "mode": mode,
    "trade_week": str(this_week_start().date()),
    "next_week": str(next_week_start().date()),
    "rows": status_rows,
    "ready_n": ready_n,
  }


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
  try:
    from strategy_mode import frozen_enabled
    if frozen_enabled():
      out.update(skipped=True, reason="frozen_mode")
      return out
  except Exception:
    pass
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
