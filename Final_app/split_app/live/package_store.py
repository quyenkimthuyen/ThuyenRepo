"""Installed package store + live roster."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import INSTALLED_DIR, LIVE_ROOT, ROSTER_PATH

_SPLIT = LIVE_ROOT.parent
if str(_SPLIT) not in sys.path:
  sys.path.insert(0, str(_SPLIT))

from shared.package_format import (  # noqa: E402
  package_has_usable_schedule,
  repair_package_crlf,
  schedule_weekly_count,
  validate_package_dir,
)


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  # Unique temp avoids parallel writers colliding on the same ``.tmp`` name.
  tmp = path.with_name(f"{path.stem}.{os.getpid()}.{time.time_ns()}.tmp")
  payload = json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
  last_exc: OSError | None = None
  for attempt in range(8):
    try:
      tmp.write_text(payload, encoding="utf-8")
      tmp.replace(path)
      return
    except OSError as exc:
      last_exc = exc
      # Windows: parallel replay books can contend on live_roster.json
      if getattr(exc, "winerror", None) != 32 and getattr(exc, "errno", None) not in (11, 16):
        try:
          tmp.unlink(missing_ok=True)
        except OSError:
          pass
        raise
      time.sleep(0.05 * (attempt + 1))
  try:
    tmp.unlink(missing_ok=True)
  except OSError:
    pass
  if last_exc:
    raise last_exc
  raise OSError(f"cannot write {path}")


def package_ready(install_id: str | Path) -> dict[str, Any]:
  """Check whether an installed package is complete enough for Live use."""
  if isinstance(install_id, Path):
    dest = install_id
    iid = dest.name
  else:
    iid = str(install_id or "").strip()
    dest = INSTALLED_DIR / iid
  if not dest.is_dir():
    return {
      "install_id": iid,
      "ready": False,
      "has_schedule": False,
      "schedule_weeks": 0,
      "error": f"not installed: {iid}",
    }
  # Windows Git checkout often CRLF-izes JSON and breaks SHA256SUMS — repair in place.
  repair_package_crlf(dest)
  errs = validate_package_dir(dest)
  sched = _read(dest / "schedule.json") or {}
  n_w = schedule_weekly_count(sched) if isinstance(sched, dict) else 0
  has = package_has_usable_schedule(dest)
  return {
    "install_id": iid,
    "ready": not errs and has,
    "has_schedule": has,
    "schedule_weeks": n_w,
    "error": "; ".join(errs) if errs else None,
  }


def list_installed() -> list[dict]:
  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
  rows = []
  for d in sorted(INSTALLED_DIR.iterdir()):
    if not d.is_dir() or d.name.startswith("_"):
      continue
    man = _read(d / "manifest.json") or {}
    model = _read(d / "model.json") or {}
    ready = package_ready(d)
    rows.append({
      "install_id": d.name,
      "path": str(d),
      "model_id": man.get("model_id") or model.get("id"),
      "label": man.get("label") or model.get("label"),
      "symbol": man.get("symbol"),
      "timeframe": man.get("timeframe"),
      "oos_from": man.get("oos_from"),
      "oos_to": man.get("oos_to"),
      "lab": man.get("lab"),
      "kb_fingerprint": man.get("kb_fingerprint"),
      "installed_at": (_read(d / "install_meta.json") or {}).get("installed_at"),
      "has_schedule": ready.get("has_schedule"),
      "schedule_weeks": ready.get("schedule_weeks"),
      "ready": ready.get("ready"),
      "ready_error": ready.get("error"),
    })
  return rows


def available_books(installed: list[dict] | None = None) -> list[dict]:
  """Internal grouping helper (symbol, timeframe)."""
  rows = installed if installed is not None else list_installed()
  seen: dict[tuple[str, str], int] = {}
  for r in rows:
    sym = str(r.get("symbol") or "").upper()
    tf = str(r.get("timeframe") or "").upper()
    if not sym or not tf:
      continue
    key = (sym, tf)
    seen[key] = seen.get(key, 0) + 1
  return [
    {"symbol": s, "timeframe": t, "n": n, "key": f"{s} {t}"}
    for (s, t), n in sorted(seen.items())
  ]


def load_roster() -> dict:
  data = _read(ROSTER_PATH)
  if not data:
    return {"updated_at": None, "models": []}
  return data


def sanitize_roster_models(models: list[dict]) -> tuple[list[dict], list[str]]:
  """Force-disable incomplete packages; return (models, warnings)."""
  out: list[dict] = []
  warnings: list[str] = []
  for row in models:
    r = dict(row)
    iid = str(r.get("install_id") or "")
    if not iid:
      out.append(r)
      continue
    info = package_ready(iid)
    r["has_schedule"] = info.get("has_schedule")
    r["schedule_weeks"] = info.get("schedule_weeks")
    r["ready"] = info.get("ready")
    if r.get("enabled") and not info.get("ready"):
      r["enabled"] = False
      warnings.append(
        f"{r.get('label') or iid}: disabled — {info.get('error') or 'incomplete package'}"
      )
    out.append(r)
  return out, warnings


def save_roster(models: list[dict], *, active_book: dict | None = None) -> dict:
  """Persist roster. Incomplete packages cannot stay enabled."""
  models, _warnings = sanitize_roster_models(models)
  prev = load_roster()
  payload: dict[str, Any] = {"updated_at": _now(), "models": models}
  if active_book is not None:
    payload["active_book"] = active_book
  elif prev.get("active_book") is not None:
    payload["active_book"] = prev.get("active_book")
  _write(ROSTER_PATH, payload)
  return payload


def default_roster_from_installed(*, active_book: dict | None = None) -> list[dict]:
  """Installed models — only READY packages default to On."""
  rows = []
  for inst in list_installed():
    ready = bool(inst.get("ready"))
    rows.append({
      "install_id": inst["install_id"],
      "model_id": inst["model_id"],
      "label": inst["label"],
      "symbol": inst["symbol"],
      "timeframe": inst["timeframe"],
      "enabled": ready,
      "ready": ready,
      "has_schedule": inst.get("has_schedule"),
      "schedule_weeks": inst.get("schedule_weeks"),
      "risk_pct": 1.0,
      "magic": None,
    })
  return rows


def get_installed(install_id: str) -> dict | None:
  iid = str(install_id or "").strip()
  if not iid:
    return None
  for row in list_installed():
    if row.get("install_id") == iid:
      return row
  return None


def delete_installed(
  install_id: str,
  *,
  update_roster: bool = True,
) -> dict[str, Any]:
  """Remove an imported package folder and drop it from the live roster.

  Does not stop a running bridge — caller should warn if the model is On/running.
  """
  import shutil

  iid = str(install_id or "").strip()
  if not iid or iid.startswith("_") or "/" in iid or "\\" in iid or ".." in iid:
    raise ValueError(f"Invalid install_id: {install_id!r}")

  dest = INSTALLED_DIR / iid
  if not dest.is_dir():
    raise FileNotFoundError(f"Not installed: {iid}")

  info = get_installed(iid) or {"install_id": iid}
  shutil.rmtree(dest)

  removed_from_roster = 0
  roster_after: list[dict] = []
  if update_roster:
    roster = load_roster()
    models = list(roster.get("models") or [])
    kept = [m for m in models if str(m.get("install_id") or "") != iid]
    removed_from_roster = len(models) - len(kept)
    save_roster(kept, active_book=roster.get("active_book"))
    roster_after = kept

  try:
    from debug_log import log_event
    log_event(
      "model_deleted",
      summary=f"deleted {iid} ({info.get('label') or info.get('model_id')})",
      payload={
        "install_id": iid,
        "model_id": info.get("model_id"),
        "label": info.get("label"),
        "symbol": info.get("symbol"),
        "timeframe": info.get("timeframe"),
        "removed_from_roster": removed_from_roster,
      },
      source="package_store",
    )
  except Exception:
    pass

  return {
    "ok": True,
    "install_id": iid,
    "path": str(dest),
    "label": info.get("label"),
    "model_id": info.get("model_id"),
    "removed_from_roster": removed_from_roster,
    "roster_n": len(roster_after) if update_roster else None,
  }
