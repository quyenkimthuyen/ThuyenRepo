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
    payload["loss_guard_halted_models"] = []
  if clear_trip:
    payload["enabled"] = True
    payload["last_error"] = None
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


def _halted_models_from_workers() -> list[str]:
  seen: list[str] = []
  for path in worker_config_paths():
    data = _read(path) or {}
    if not isinstance(data, dict):
      continue
    for mid in data.get("loss_guard_halted_models") or []:
      sid = str(mid).strip()
      if sid and sid not in seen:
        seen.append(sid)
  return seen


def any_worker_loss_guard_trip() -> dict[str, Any]:
  """First per-book trip latch or halted-model list, if any."""
  for path in worker_config_paths():
    data = _read(path) or {}
    if not isinstance(data, dict):
      continue
    halted = [str(x) for x in (data.get("loss_guard_halted_models") or []) if x]
    if data.get("loss_guard_tripped") or halted:
      return {
        "tripped": True,
        "tripped_at": data.get("loss_guard_tripped_at"),
        "tripped_reason": data.get("loss_guard_tripped_reason"),
        "book": path.stem.replace("mt5_bridge_worker_", "", 1),
        "halted_models": halted,
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
    loss_guard_halted_models=[],
    last_error=None,
    enabled=True,
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


def _risk_bridge_dirs() -> list[Path]:
  dirs: list[Path] = []
  seen: set[str] = set()

  def _add(path: Path) -> None:
    try:
      key = str(path.resolve())
    except OSError:
      key = str(path)
    if key in seen:
      return
    seen.add(key)
    dirs.append(Path(path))

  try:
    from books import bridge_dir, group_models_by_book
    from package_store import load_roster
    rows = [r for r in (load_roster().get("models") or []) if r.get("enabled")]
    groups = group_models_by_book(rows) if rows else {}
    for sym, tf in groups:
      _add(bridge_dir(sym, tf, sim=False))
  except Exception:
    pass
  if not dirs:
    from live_config import MT5_ROOT
    for path in sorted(MT5_ROOT.glob("bridge_live_*")):
      if path.is_dir():
        _add(path)
  return dirs


def journal_risk_metrics(
  bridge_dirs: list[Path] | None = None,
  *,
  now: datetime | None = None,
) -> dict[str, Any]:
  """Per-model DD / day R from Live journals — no host bootstrap required."""
  from journal_view import _is_closed, _trade_r, load_trades
  from loss_guard_ext import group_trades_by_model, window_drawdown_r, window_total_r

  dirs = list(bridge_dirs or [])
  closed: list[dict] = []
  for bdir in dirs:
    for t in load_trades(bdir):
      if not _is_closed(t):
        continue
      row = dict(t)
      r = _trade_r(t)
      if r is not None:
        row["r"] = r
      closed.append(row)

  day_dds: list[float] = []
  week_dds: list[float] = []
  day_rs: list[float] = []
  week_rs: list[float] = []
  worst_dd_model = None
  worst_dd = -1.0
  worst_r_model = None
  worst_r = 0.0
  have_r = False
  for mid, rows in group_trades_by_model(closed).items():
    d = window_drawdown_r(rows, window="day", now=now)
    w = window_drawdown_r(rows, window="week", now=now)
    dr = window_total_r(rows, window="day", now=now)
    wr = window_total_r(rows, window="week", now=now)
    day_dds.append(d)
    week_dds.append(w)
    day_rs.append(dr)
    week_rs.append(wr)
    if d > worst_dd:
      worst_dd = d
      worst_dd_model = mid
    if not have_r or dr < worst_r:
      worst_r = dr
      worst_r_model = mid
      have_r = True
  return {
    "day_dd_r": round(max(day_dds), 4) if day_dds else 0.0,
    "week_dd_r": round(max(week_dds), 4) if week_dds else 0.0,
    "day_total_r": round(min(day_rs), 4) if day_rs else 0.0,
    "desk_day_total_r": round(sum(day_rs), 4) if day_rs else 0.0,
    "week_total_r": round(min(week_rs), 4) if week_rs else 0.0,
    "worst_dd_model": worst_dd_model,
    "worst_day_r_model": worst_r_model,
    "books_scanned": len(dirs),
    "n_closed": len(closed),
  }


def risk_status_snapshot() -> dict[str, Any]:
  """UI status: prefs + live config trip + journal DD / day R per model."""
  prefs = load_risk_prefs()
  from bridge_control import load_config
  cfg = load_config()
  merged = {**prefs}
  for k in RISK_KEYS:
    if k in cfg and cfg.get(k) is not None:
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
  halted_all: list[str] = _halted_models_from_workers()
  if book_trip.get("halted_models"):
    for mid in book_trip["halted_models"]:
      if mid not in halted_all:
        halted_all.append(mid)

  status = {
    "prefs": prefs,
    "tripped": merged["loss_guard_tripped"],
    "tripped_at": merged.get("loss_guard_tripped_at"),
    "tripped_reason": merged.get("loss_guard_tripped_reason"),
    "tripped_book": book_trip.get("book") if book_trip.get("tripped") else None,
    "halted_models": halted_all,
    "day_dd_r": 0.0,
    "week_dd_r": 0.0,
    "day_total_r": 0.0,
    "desk_day_total_r": 0.0,
    "week_total_r": 0.0,
    "worst_dd_model": None,
    "worst_day_r_model": None,
    "day_streak": None,
    "week_streak": None,
  }
  try:
    metrics = journal_risk_metrics(_risk_bridge_dirs())
    status.update(metrics)
    status["halted_models"] = halted_all
  except Exception as exc:
    status["status_error"] = str(exc)
  return status
