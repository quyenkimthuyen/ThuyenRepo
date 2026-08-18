"""Live risk / loss-guard preferences (persisted across Start)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import RESULTS_DIR
from safety import default_loss_guard_from_roster

PREFS_PATH = RESULTS_DIR / "risk_prefs.json"

# Keys written into mt5_bridge_config.json
RISK_KEYS = (
  "loss_guard_enabled",
  "loss_guard_max_day",
  "loss_guard_max_week",
  "loss_guard_max_day_dd_r",
  "loss_guard_max_week_dd_r",
  "loss_guard_max_day_loss_r",
  "loss_guard_max_week_loss_r",
)


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def default_risk_prefs() -> dict[str, Any]:
  base = default_loss_guard_from_roster()
  # Sensible R limits (0 = off). Day DD ~6R, week DD ~10R as soft defaults.
  base.setdefault("loss_guard_max_day_dd_r", 6.0)
  base.setdefault("loss_guard_max_week_dd_r", 10.0)
  base.setdefault("loss_guard_max_day_loss_r", 0.0)
  base.setdefault("loss_guard_max_week_loss_r", 0.0)
  return {k: base.get(k) for k in RISK_KEYS}


def load_risk_prefs() -> dict[str, Any]:
  data = _read(PREFS_PATH) or {}
  out = default_risk_prefs()
  for k in RISK_KEYS:
    if k in data:
      out[k] = data[k]
  # types
  out["loss_guard_enabled"] = bool(out.get("loss_guard_enabled", True))
  out["loss_guard_max_day"] = int(out.get("loss_guard_max_day") or 0)
  out["loss_guard_max_week"] = int(out.get("loss_guard_max_week") or 0)
  for k in (
    "loss_guard_max_day_dd_r", "loss_guard_max_week_dd_r",
    "loss_guard_max_day_loss_r", "loss_guard_max_week_loss_r",
  ):
    try:
      out[k] = float(out.get(k) or 0)
    except (TypeError, ValueError):
      out[k] = 0.0
  return out


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def worker_config_paths() -> list[Path]:
  return sorted(RESULTS_DIR.glob("mt5_bridge_worker_*.json"))


def apply_loss_guard_to_workers(
  *,
  clear_trip: bool = False,
  **updates: Any,
) -> list[str]:
  """Push Risk-tab prefs into per-book worker JSON (running workers re-read each poll).

  UI Save / disable used to write only ``mt5_bridge_config.json``. Each book worker
  keeps ``mt5_bridge_worker_{book}.json`` — a sticky trip there keeps GBPUSD halted.
  """
  payload: dict[str, Any] = {}
  for k, v in updates.items():
    if k in RISK_KEYS or k.startswith("loss_guard_"):
      payload[k] = v
  if clear_trip or payload.get("loss_guard_enabled") is False:
    payload["loss_guard_tripped"] = False
    payload["loss_guard_tripped_at"] = None
    payload["loss_guard_tripped_reason"] = None
  if not payload:
    return []
  touched: list[str] = []
  for path in worker_config_paths():
    data = _read(path)
    if not isinstance(data, dict):
      continue
    data.update(payload)
    _write(path, data)
    touched.append(path.name)
  return touched


def any_worker_loss_guard_trip() -> dict[str, Any]:
  """First per-book trip latch, if any (global config can look clear)."""
  for path in worker_config_paths():
    data = _read(path) or {}
    if isinstance(data, dict) and data.get("loss_guard_tripped"):
      return {
        "tripped": True,
        "tripped_at": data.get("loss_guard_tripped_at"),
        "tripped_reason": data.get("loss_guard_tripped_reason"),
        "book": path.stem.replace("mt5_bridge_worker_", "", 1),
      }
  return {"tripped": False}


def save_risk_prefs(**updates) -> dict[str, Any]:
  cur = load_risk_prefs()
  for k, v in updates.items():
    if k in RISK_KEYS:
      cur[k] = v
  cur["updated_at"] = _now()
  PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
  PREFS_PATH.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
  try:
    apply_loss_guard_to_workers(
      clear_trip=not bool(cur.get("loss_guard_enabled")),
      **{k: cur[k] for k in RISK_KEYS},
    )
  except Exception:
    pass
  return load_risk_prefs()


def clear_loss_guard_trip() -> dict[str, Any]:
  """Clear tripped latch in live + per-book worker configs (does not Disarm kill-switch)."""
  from bridge_control import save_config
  cfg = save_config(
    loss_guard_tripped=False,
    loss_guard_tripped_at=None,
    loss_guard_tripped_reason=None,
    last_error=None,
  )
  workers = []
  try:
    workers = apply_loss_guard_to_workers(clear_trip=True)
  except Exception:
    workers = []
  return {
    "cleared": True,
    "at": _now(),
    "workers": workers,
    "config": {k: cfg.get(k) for k in (
      "loss_guard_tripped", "loss_guard_enabled", "enabled",
    )},
  }


def risk_status_snapshot() -> dict[str, Any]:
  """UI status: prefs + live config trip + optional journal streaks/DD."""
  prefs = load_risk_prefs()
  from bridge_control import load_config
  from live_config import BRIDGE_DIR
  cfg = load_config()
  merged = {**prefs}
  for k in RISK_KEYS:
    if k in cfg and cfg.get(k) is not None:
      # prefer live runtime for trip flags; prefs for limits if set
      if k.startswith("loss_guard_tripped"):
        merged[k] = cfg.get(k)
  merged["loss_guard_tripped"] = bool(cfg.get("loss_guard_tripped"))
  merged["loss_guard_tripped_at"] = cfg.get("loss_guard_tripped_at")
  merged["loss_guard_tripped_reason"] = cfg.get("loss_guard_tripped_reason")
  book_trip = any_worker_loss_guard_trip()
  if book_trip.get("tripped"):
    merged["loss_guard_tripped"] = True
    merged["loss_guard_tripped_at"] = book_trip.get("tripped_at") or merged.get("loss_guard_tripped_at")
    merged["loss_guard_tripped_reason"] = book_trip.get("tripped_reason") or merged.get("loss_guard_tripped_reason")

  status = {
    "prefs": prefs,
    "tripped": merged["loss_guard_tripped"],
    "tripped_at": merged.get("loss_guard_tripped_at"),
    "tripped_reason": merged.get("loss_guard_tripped_reason"),
    "tripped_book": book_trip.get("book") if book_trip.get("tripped") else None,
    "day_dd_r": None,
    "week_dd_r": None,
    "day_total_r": None,
    "week_total_r": None,
    "day_streak": None,
    "week_streak": None,
  }
  try:
    from runtime_bootstrap import bootstrap_host
    from package_store import load_roster
    rows = [r for r in (load_roster().get("models") or []) if r.get("enabled")]
    if rows:
      bootstrap_host(rows[0].get("symbol") or "EURUSD", rows[0].get("timeframe") or "M15")
    from mt5_bridge.loss_guard import loss_guard_status
    from books import bridge_dir, group_models_by_book
    groups = group_models_by_book(rows) if rows else {}
    cfg_merge = {**prefs, **{k: cfg.get(k) for k in (
      "loss_guard_tripped", "loss_guard_tripped_at", "loss_guard_tripped_reason",
    )}}
    # BUG-09: aggregate across all books (worst DD/streak, sum total R).
    day_dds: list[float] = []
    week_dds: list[float] = []
    day_totals: list[float] = []
    week_totals: list[float] = []
    day_streaks: list[int] = []
    week_streaks: list[int] = []
    book_dirs = []
    if groups:
      for (sym, tf) in groups.keys():
        book_dirs.append(bridge_dir(sym, tf, sim=False))
    else:
      book_dirs.append(BRIDGE_DIR)
    for bdir in book_dirs:
      st = loss_guard_status(cfg_merge, bridge_dir=bdir)
      if st.get("day_dd_r") is not None:
        day_dds.append(float(st["day_dd_r"]))
      if st.get("week_dd_r") is not None:
        week_dds.append(float(st["week_dd_r"]))
      if st.get("day_total_r") is not None:
        day_totals.append(float(st["day_total_r"]))
      if st.get("week_total_r") is not None:
        week_totals.append(float(st["week_total_r"]))
      if st.get("day_streak") is not None:
        day_streaks.append(int(st["day_streak"]))
      if st.get("week_streak") is not None:
        week_streaks.append(int(st["week_streak"]))
    status.update({
      "day_dd_r": max(day_dds) if day_dds else None,
      "week_dd_r": max(week_dds) if week_dds else None,
      "day_total_r": round(sum(day_totals), 4) if day_totals else None,
      "week_total_r": round(sum(week_totals), 4) if week_totals else None,
      "day_streak": max(day_streaks) if day_streaks else None,
      "week_streak": max(week_streaks) if week_streaks else None,
      "books_scanned": len(book_dirs),
    })
  except Exception as exc:
    status["status_error"] = str(exc)
  return status
