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


def save_risk_prefs(**updates) -> dict[str, Any]:
  cur = load_risk_prefs()
  for k, v in updates.items():
    if k in RISK_KEYS:
      cur[k] = v
  cur["updated_at"] = _now()
  PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
  PREFS_PATH.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
  return load_risk_prefs()


def clear_loss_guard_trip() -> dict[str, Any]:
  """Clear tripped latch in live bridge config (does not Disarm kill-switch)."""
  from bridge_control import load_config, save_config
  cfg = save_config(
    loss_guard_tripped=False,
    loss_guard_tripped_at=None,
    loss_guard_tripped_reason=None,
    last_error=None,
    enabled=False,  # user must Start again deliberately
  )
  return {
    "cleared": True,
    "at": _now(),
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

  status = {
    "prefs": prefs,
    "tripped": merged["loss_guard_tripped"],
    "tripped_at": merged.get("loss_guard_tripped_at"),
    "tripped_reason": merged.get("loss_guard_tripped_reason"),
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
    # Aggregate across live bridge dirs
    from books import bridge_dir, group_models_by_book
    groups = group_models_by_book(rows) if rows else {}
    # Use primary + merge trades mentally via first book for snapshot simplicity
    bdir = BRIDGE_DIR
    if groups:
      (sym, tf) = next(iter(groups.keys()))
      bdir = bridge_dir(sym, tf, sim=False)
    st = loss_guard_status({**prefs, **{k: cfg.get(k) for k in (
      "loss_guard_tripped", "loss_guard_tripped_at", "loss_guard_tripped_reason",
    )}}, bridge_dir=bdir)
    status.update({
      "day_dd_r": st.get("day_dd_r"),
      "week_dd_r": st.get("week_dd_r"),
      "day_total_r": st.get("day_total_r"),
      "week_total_r": st.get("week_total_r"),
      "day_streak": st.get("day_streak"),
      "week_streak": st.get("week_streak"),
    })
  except Exception as exc:
    status["status_error"] = str(exc)
  return status
