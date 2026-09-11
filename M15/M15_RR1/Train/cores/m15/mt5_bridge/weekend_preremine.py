"""Weekend pre-remine for Train Live Bridge — mine *next* broker week early.

Live remines on the first M15 bar of a new week (often Monday open). Pre-remine
on Fri evening / Sat / Sun freezes strategy into ``live_weeks`` so Monday is a
fast cache hit.

Disable: env ``TRAIN_WEEKEND_PREREMINE=0`` or bridge config ``weekend_preremine_enabled=false``.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app_paths import get_root

REPORT_DIR = get_root() / "results"
STATE_PATH = REPORT_DIR / "weekend_preremine.json"
RETRY_SEC = float(os.environ.get("TRAIN_WEEKEND_PREREMINE_RETRY_SEC") or 900)
FRI_START_HOUR = int(os.environ.get("TRAIN_WEEKEND_PREREMINE_FRI_HOUR") or 18)


def _now_local() -> datetime:
  return datetime.now(timezone.utc).astimezone()


def _read_json(path: Path) -> dict[str, Any]:
  if not path.exists():
    return {}
  try:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
  except (OSError, json.JSONDecodeError):
    return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def _enabled_from_config() -> bool:
  env = str(os.environ.get("TRAIN_WEEKEND_PREREMINE") or "").strip().lower()
  if env in ("0", "false", "no", "off"):
    return False
  if env in ("1", "true", "yes", "on"):
    return True
  try:
    from mt5_bridge.background import load_config_cached
    return bool(load_config_cached().get("weekend_preremine_enabled", True))
  except Exception:
    return True


def load_state() -> dict[str, Any]:
  return _read_json(STATE_PATH)


def save_state(data: dict[str, Any]) -> None:
  data["updated_at"] = _now_local().isoformat(timespec="seconds")
  _write_json(STATE_PATH, data)


def this_week_start(now: datetime | pd.Timestamp | None = None) -> pd.Timestamp:
  ts = pd.Timestamp(now or _now_local())
  if getattr(ts, "tzinfo", None) is not None:
    try:
      ts = ts.tz_convert(None)
    except Exception:
      ts = pd.Timestamp(ts.to_pydatetime().replace(tzinfo=None))
  return (ts - pd.Timedelta(days=int(ts.weekday()))).normalize()


def next_week_start(now: datetime | pd.Timestamp | None = None) -> pd.Timestamp:
  return this_week_start(now) + pd.Timedelta(days=7)


def in_weekend_preremine_window(now: datetime | pd.Timestamp | None = None) -> bool:
  """Fri from FRI_START_HOUR, all Saturday, all Sunday (local wall clock)."""
  ts = pd.Timestamp(now or _now_local())
  if getattr(ts, "tzinfo", None) is not None:
    try:
      ts = ts.tz_convert(None)
    except Exception:
      ts = pd.Timestamp(ts.to_pydatetime().replace(tzinfo=None))
  wd = int(ts.weekday())
  if wd >= 5:
    return True
  if wd == 4 and int(ts.hour) >= FRI_START_HOUR:
    return True
  return False


def weekend_preremine_target(now: datetime | pd.Timestamp | None = None) -> pd.Timestamp | None:
  if not _enabled_from_config():
    return None
  if not in_weekend_preremine_window(now):
    return None
  return next_week_start(now)


def quality_status_week(
  now: datetime | pd.Timestamp | None = None,
) -> tuple[str, str]:
  """``(week_start_iso, mode)`` — ``trading`` or ``preremine``."""
  tgt = weekend_preremine_target(now)
  if tgt is not None:
    return str(tgt.date()), "preremine"
  return str(this_week_start(now).date()), "trading"


def _model_done(state: dict[str, Any], *, model_id: str, week: str) -> bool:
  m = (state.get("models") or {}).get(str(model_id)) or {}
  return str(m.get("week_start") or "") == week and bool(m.get("ok"))


def _mark_model(
  state: dict[str, Any],
  *,
  model_id: str,
  week: str,
  ok: bool,
  source: str,
  error: str | None = None,
) -> None:
  models = state.setdefault("models", {})
  models[str(model_id)] = {
    "week_start": week,
    "ok": bool(ok),
    "source": source,
    "error": error,
    "updated_at": _now_local().isoformat(timespec="seconds"),
  }
  state["week_start"] = week


def prune_preremine_to_roster(model_ids: list[str] | None) -> dict[str, Any]:
  """Drop pre-remine rows for models no longer in Bridge roster."""
  ids = {str(x) for x in (model_ids or []) if x}
  state = load_state()
  models = dict(state.get("models") or {})
  dropped = [mid for mid in list(models) if mid not in ids]
  for mid in dropped:
    models.pop(mid, None)
  if dropped:
    state["models"] = models
    save_state(state)
  return {"dropped": dropped, "kept": sorted(models.keys())}


def freeze_info_for_week(model_id: str, week: str) -> dict[str, Any]:
  """Schedule / live_weeks row for one ISO week (status UI)."""
  mid = str(model_id or "").strip()
  week_s = str(week or "")[:10]
  if not mid or not week_s:
    return {}
  try:
    from trade_model_schedule import (
      load_live_weeks,
      load_model_schedule,
      lookup_week_strategy_with_source,
    )
    entry, src = lookup_week_strategy_with_source(mid, week_s)
    if entry and isinstance(entry.get("strategy"), dict):
      return {"week_start": week_s, "ok": True, "source": src or "schedule"}
  except Exception:
    pass
  return {}


def _remine_source_label(source: str | None, *, remine_each_week: bool = True) -> str:
  if source == "schedule":
    return "OOS schedule"
  if source == "live_weeks":
    return "Đã remine live"
  if source == "live_remine":
    return "Remine tuần này"
  if source == "manual_remine":
    return "Remine tay"
  if source == "frozen":
    return "Freeze (OFF)"
  if source == "frozen_first":
    return "Freeze lần đầu"
  if source == "state_done":
    return "Đã pre-remine"
  if source == "pending":
    return "Chờ remine" if remine_each_week else "Chờ freeze"
  return source or "—"


def build_quality_status_table(model_ids: list[str] | None = None) -> dict[str, Any]:
  """Rows for Trade Models weekend / remine status table."""
  week, mode = quality_status_week()
  state = load_state()
  by_model = dict(state.get("models") or {})
  ids = [str(x) for x in (model_ids or []) if x]
  if not ids:
    try:
      from mt5_bridge.background import config_model_ids, load_config_cached
      ids = config_model_ids(load_config_cached())
    except Exception:
      ids = []

  rows: list[dict[str, Any]] = []
  for mid in ids:
    info = dict(by_model.get(mid) or {})
    w = str(info.get("week_start") or "")
    if w != week:
      freeze = freeze_info_for_week(mid, week)
      if freeze:
        info = freeze
        w = str(info.get("week_start") or "")
    if info and w == week and info.get("ok"):
      status = "READY"
    elif info and w == week and info.get("ok") is False:
      status = "FAIL"
    elif info and w and w != week:
      status = "STALE"
    elif info:
      status = "PARTIAL"
    else:
      status = "PENDING"
    src = str(info.get("source") or "—")
    try:
      from mt5_bridge.background import load_config_cached
      from mt5_bridge.models import get_model_by_id
      m = get_model_by_id(mid)
      label = str((m or {}).get("label") or mid)[:42]
      remine_on = bool(load_config_cached().get("remine_each_week", True))
      remine_label = _remine_source_label(src if src != "—" else None, remine_each_week=remine_on)
    except Exception:
      label = mid[:28]
      remine_label = src
    strat_name = "—"
    try:
      from trade_model_schedule import lookup_week_strategy
      hit = lookup_week_strategy(mid, week)
      if hit and isinstance(hit.get("strategy"), dict):
        strat_name = str(hit["strategy"].get("name") or "—")[:36]
    except Exception:
      pass
    rows.append({
      "model_id": mid,
      "model": label,
      "week": week if status != "PENDING" else (w or week),
      "status": status,
      "source": src,
      "remine": remine_label,
      "strategy": strat_name,
      "reason": str(info.get("error") or "—")[:80],
      "updated": str(info.get("updated_at") or "—")[:19],
    })

  ready_n = sum(1 for r in rows if r["status"] == "READY")
  return {
    "week": week,
    "mode": mode,
    "trade_week": str(this_week_start().date()),
    "next_week": str(next_week_start().date()),
    "rows": rows,
    "ready_n": ready_n,
    "in_window": in_weekend_preremine_window(),
    "enabled": _enabled_from_config(),
  }


def maybe_preremine_engines(
  engines: dict[str, Any],
  *,
  bridge_dir: Path | str | None = None,
  force: bool = False,
) -> dict[str, Any]:
  """Pre-remine next week for each engine when in the weekend window."""
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
  state = load_state()
  mids = [str(m) for m in (engines or {}).keys()]
  if not mids:
    out.update(skipped=True, reason="no_engines", week_start=week_s)
    return out

  if all(_model_done(state, model_id=mid, week=week_s) for mid in mids) and not force:
    out.update(skipped=True, reason="already_done", week_start=week_s)
    return out

  last_attempt = state.get("last_attempt_at")
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

  try:
    from mt5_bridge.background import load_config_cached
    remine_each_week = bool(load_config_cached().get("remine_each_week", True))
  except Exception:
    remine_each_week = True

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
          eng.prewarm_week(target)
          src = str(getattr(eng, "_last_remine_source", None) or "schedule")
          row.update(ok=True, source=src, action="cache_warm")
          _mark_model(state, model_id=mid_s, week=week_s, ok=True, source=src)
          results.append(row)
          continue
      if _model_done(state, model_id=mid_s, week=week_s) and not force:
        row.update(ok=True, source="state_done", action="skip")
        results.append(row)
        continue

      if not remine_each_week and getattr(eng, "_frozen_strat", None) is not None:
        row.update(ok=True, source="frozen", action="skip_freeze")
        _mark_model(state, model_id=mid_s, week=week_s, ok=True, source="frozen")
        results.append(row)
        continue

      any_work = True
      print(f"[weekend_preremine] model={mid_s} week={week_s} …", flush=True)
      t0 = time.time()
      eng.prewarm_week(target)
      dt = round(time.time() - t0, 2)
      src = str(getattr(eng, "_last_remine_source", None) or "live_remine")
      ok = bool(getattr(eng, "_last_remine_source", None))
      row.update(ok=ok, source=src, action="prewarm", duration_sec=dt)
      _mark_model(
        state,
        model_id=mid_s,
        week=week_s,
        ok=ok,
        source=src,
        error=None if ok else f"prewarm failed ({src})",
      )
      print(
        f"[weekend_preremine] model={mid_s} week={week_s} src={src} ok={ok} {dt}s",
        flush=True,
      )
    except Exception as exc:
      any_work = True
      row.update(ok=False, source="error", error=str(exc)[:240])
      _mark_model(
        state, model_id=mid_s, week=week_s, ok=False, source="error", error=str(exc)[:240],
      )
      print(f"[weekend_preremine] model={mid_s} FAIL: {exc}", flush=True)
    results.append(row)

  state["last_attempt_at"] = _now_local().isoformat(timespec="seconds")
  state["week_start"] = week_s
  save_state(state)

  out["models"] = results
  out["ok"] = all(bool(r.get("ok")) for r in results) if results else True
  out["any_work"] = any_work

  if any_work or results:
    try:
      from mt5_bridge.comm_log import append_event
      append_event(
        "system",
        "weekend_preremine",
        bridge_dir=bridge_dir,
        summary=(
          f"week={week_s} ok={out['ok']} n={len(results)} work={any_work}"
        ),
        payload={"week_start": week_s, "models": results, "ok": out["ok"]},
      )
    except Exception:
      pass

  return out
