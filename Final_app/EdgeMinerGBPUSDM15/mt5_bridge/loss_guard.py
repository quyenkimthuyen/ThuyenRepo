"""Consecutive-loss circuit breaker for MT5 Bridge Live.

Stops the decision service when auto trades lose in a row within a calendar
day and/or week — protects the account if the app / model misbehaves.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mt5_bridge.trade_journal import MODE_AUTO, load_trades, trade_mode


DEFAULT_MAX_DAY = 3
DEFAULT_MAX_WEEK = 5


def default_streak_limit_from_model(
  model: dict | None,
  *,
  fallback: int = DEFAULT_MAX_DAY,
  max_cap: int = 40,
) -> int:
  """Default consecutive-loss limit: ``int(|max_drawdown_r|) + 1`` from Trade Model."""
  raw = None
  if isinstance(model, dict):
    raw = model.get("max_drawdown_r")
    if raw is None:
      oos = model.get("overall_oos") or {}
      if isinstance(oos, dict):
        raw = oos.get("max_drawdown_r")
  if raw is None:
    return max(1, int(fallback))
  try:
    n = int(abs(float(raw))) + 1
  except (TypeError, ValueError):
    return max(1, int(fallback))
  return max(1, min(int(n), int(max_cap)))


def _local_now(now: datetime | None = None) -> datetime:
  if now is not None:
    if now.tzinfo is None:
      return now.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return now.astimezone()
  return datetime.now().astimezone()


def _parse_exit_ts(trade: dict) -> datetime | None:
  raw = trade.get("exit_time") or trade.get("updated_at") or trade.get("entry_time")
  if raw is None or raw == "":
    return None
  try:
    import pandas as pd
    ts = pd.Timestamp(str(raw))
    if getattr(ts, "tzinfo", None) is None:
      # Treat naive broker stamps as local wall clock for day/week buckets.
      return ts.to_pydatetime().replace(tzinfo=_local_now().tzinfo)
    return ts.to_pydatetime().astimezone()
  except Exception:
    return None


def _is_auto_loss(trade: dict) -> bool | None:
  """True=loss, False=non-loss close, None=skip (open / unknown)."""
  if str(trade.get("status") or "").upper() != "CLOSED":
    return None
  if trade_mode(trade) != MODE_AUTO:
    return None
  result = str(trade.get("result") or "").upper()
  if result == "LOSS":
    return True
  if result in ("WIN", "BE"):
    return False
  if trade.get("r") is not None:
    try:
      return float(trade["r"]) < 0
    except (TypeError, ValueError):
      return None
  if trade.get("profit") is not None:
    try:
      return float(trade["profit"]) < 0
    except (TypeError, ValueError):
      return None
  return None


def closed_auto_trades_chronologically(
  trades: list[dict] | None = None,
  *,
  bridge_dir: Path | None = None,
) -> list[dict]:
  trades = trades if trades is not None else load_trades(bridge_dir)
  closed = []
  for t in trades:
    if trade_mode(t) != MODE_AUTO:
      continue
    if str(t.get("status") or "").upper() != "CLOSED":
      continue
    closed.append(t)
  closed.sort(key=lambda t: str(_parse_exit_ts(t) or t.get("exit_time") or ""))
  return closed


def trailing_loss_streak(
  trades: list[dict],
  *,
  window: str,
  now: datetime | None = None,
) -> int:
  """Count trailing consecutive auto LOSSes inside day or ISO week window."""
  now_local = _local_now(now)
  window_l = str(window or "day").lower()
  selected: list[dict] = []
  for t in trades:
    ts = _parse_exit_ts(t)
    if ts is None:
      continue
    ts_local = ts.astimezone(now_local.tzinfo)
    if window_l == "day":
      if ts_local.date() != now_local.date():
        continue
    elif window_l in ("week", "iso_week"):
      if ts_local.isocalendar()[:2] != now_local.isocalendar()[:2]:
        continue
    else:
      # rolling 7*24h fallback
      if ts_local < now_local - timedelta(days=7):
        continue
    selected.append(t)

  streak = 0
  for t in reversed(selected):
    flag = _is_auto_loss(t)
    if flag is True:
      streak += 1
      continue
    if flag is False:
      break
    # unknown closed result — stop streak conservatively
    break
  return streak


def _trades_in_window(
  trades: list[dict],
  *,
  window: str,
  now: datetime | None = None,
) -> list[dict]:
  now_local = _local_now(now)
  window_l = str(window or "day").lower()
  selected: list[dict] = []
  for t in trades:
    ts = _parse_exit_ts(t)
    if ts is None:
      continue
    ts_local = ts.astimezone(now_local.tzinfo)
    if window_l == "day":
      if ts_local.date() != now_local.date():
        continue
    elif window_l in ("week", "iso_week"):
      if ts_local.isocalendar()[:2] != now_local.isocalendar()[:2]:
        continue
    else:
      if ts_local < now_local - timedelta(days=7):
        continue
    selected.append(t)
  return selected


def window_total_r(
  trades: list[dict],
  *,
  window: str,
  now: datetime | None = None,
) -> float:
  """Sum of closed auto trade R in day/week window."""
  total = 0.0
  for t in _trades_in_window(trades, window=window, now=now):
    try:
      if t.get("r") is not None:
        total += float(t["r"])
    except (TypeError, ValueError):
      continue
  return round(total, 4)


def window_drawdown_r(
  trades: list[dict],
  *,
  window: str,
  now: datetime | None = None,
) -> float:
  """Peak-to-trough drawdown (R) of closed auto equity within day/week."""
  eq = peak = 0.0
  dd = 0.0
  for t in _trades_in_window(trades, window=window, now=now):
    try:
      r = float(t["r"]) if t.get("r") is not None else 0.0
    except (TypeError, ValueError):
      continue
    eq += r
    peak = max(peak, eq)
    dd = max(dd, peak - eq)
  return round(dd, 4)


def evaluate_loss_guard(
  cfg: dict | None,
  *,
  bridge_dir: Path | None = None,
  trades: list[dict] | None = None,
  now: datetime | None = None,
) -> dict[str, Any] | None:
  """
  Return a trip payload when risk limits hit.

  Limits (any can be 0 = disabled):
  - ``loss_guard_max_day`` / ``loss_guard_max_week``: consecutive auto losses
  - ``loss_guard_max_day_dd_r`` / ``loss_guard_max_week_dd_r``: peak-to-trough DD (R)
  - ``loss_guard_max_day_loss_r`` / ``loss_guard_max_week_loss_r``: total R loss
    (trip when window sum(R) <= -limit)
  """
  cfg = cfg or {}
  if not bool(cfg.get("loss_guard_enabled", False)):
    return None

  max_day = int(cfg.get("loss_guard_max_day") or 0)
  max_week = int(cfg.get("loss_guard_max_week") or 0)
  max_day_dd = float(cfg.get("loss_guard_max_day_dd_r") or 0)
  max_week_dd = float(cfg.get("loss_guard_max_week_dd_r") or 0)
  max_day_loss = float(cfg.get("loss_guard_max_day_loss_r") or 0)
  max_week_loss = float(cfg.get("loss_guard_max_week_loss_r") or 0)
  if (
    max_day <= 0 and max_week <= 0
    and max_day_dd <= 0 and max_week_dd <= 0
    and max_day_loss <= 0 and max_week_loss <= 0
  ):
    return None

  closed = closed_auto_trades_chronologically(trades, bridge_dir=bridge_dir)
  day_streak = trailing_loss_streak(closed, window="day", now=now) if max_day > 0 else 0
  week_streak = trailing_loss_streak(closed, window="week", now=now) if max_week > 0 else 0
  day_dd = window_drawdown_r(closed, window="day", now=now) if max_day_dd > 0 else 0.0
  week_dd = window_drawdown_r(closed, window="week", now=now) if max_week_dd > 0 else 0.0
  day_r = window_total_r(closed, window="day", now=now)
  week_r = window_total_r(closed, window="week", now=now)

  status = {
    "day_streak": day_streak,
    "week_streak": week_streak,
    "day_dd_r": day_dd,
    "week_dd_r": week_dd,
    "day_total_r": day_r,
    "week_total_r": week_r,
    "max_day": max_day,
    "max_week": max_week,
    "max_day_dd_r": max_day_dd,
    "max_week_dd_r": max_week_dd,
    "max_day_loss_r": max_day_loss,
    "max_week_loss_r": max_week_loss,
    "enabled": True,
  }

  tripped = None
  if max_day_dd > 0 and day_dd + 1e-9 >= max_day_dd:
    tripped = {
      "scope": "day_dd",
      "value": day_dd,
      "limit": max_day_dd,
      "reason": (
        f"Risk guard: DD ngày {day_dd:.2f}R ≥ ngưỡng {max_day_dd:.2f}R — dừng service."
      ),
    }
  elif max_week_dd > 0 and week_dd + 1e-9 >= max_week_dd:
    tripped = {
      "scope": "week_dd",
      "value": week_dd,
      "limit": max_week_dd,
      "reason": (
        f"Risk guard: DD tuần {week_dd:.2f}R ≥ ngưỡng {max_week_dd:.2f}R — dừng service."
      ),
    }
  elif max_day_loss > 0 and day_r <= -max_day_loss + 1e-9:
    tripped = {
      "scope": "day_loss",
      "value": day_r,
      "limit": max_day_loss,
      "reason": (
        f"Risk guard: lỗ ngày {day_r:.2f}R ≤ -{max_day_loss:.2f}R — dừng service."
      ),
    }
  elif max_week_loss > 0 and week_r <= -max_week_loss + 1e-9:
    tripped = {
      "scope": "week_loss",
      "value": week_r,
      "limit": max_week_loss,
      "reason": (
        f"Risk guard: lỗ tuần {week_r:.2f}R ≤ -{max_week_loss:.2f}R — dừng service."
      ),
    }
  elif max_day > 0 and day_streak >= max_day:
    tripped = {
      "scope": "day",
      "streak": day_streak,
      "limit": max_day,
      "reason": (
        f"Loss guard: {day_streak} lệnh auto thua liên tiếp trong ngày "
        f"(ngưỡng {max_day}) — dừng service."
      ),
    }
  elif max_week > 0 and week_streak >= max_week:
    tripped = {
      "scope": "week",
      "streak": week_streak,
      "limit": max_week,
      "reason": (
        f"Loss guard: {week_streak} lệnh auto thua liên tiếp trong tuần "
        f"(ngưỡng {max_week}) — dừng service."
      ),
    }

  if tripped is None:
    return None
  return {**status, **tripped}


def loss_guard_status(
  cfg: dict | None,
  *,
  bridge_dir: Path | None = None,
  trades: list[dict] | None = None,
  now: datetime | None = None,
) -> dict[str, Any]:
  """Non-tripping snapshot for UI (streaks + DD + limits)."""
  cfg = cfg or {}
  max_day = int(cfg.get("loss_guard_max_day") or 0)
  max_week = int(cfg.get("loss_guard_max_week") or 0)
  max_day_dd = float(cfg.get("loss_guard_max_day_dd_r") or 0)
  max_week_dd = float(cfg.get("loss_guard_max_week_dd_r") or 0)
  max_day_loss = float(cfg.get("loss_guard_max_day_loss_r") or 0)
  max_week_loss = float(cfg.get("loss_guard_max_week_loss_r") or 0)
  enabled = bool(cfg.get("loss_guard_enabled", False))
  closed = closed_auto_trades_chronologically(trades, bridge_dir=bridge_dir) if enabled else []
  day_streak = trailing_loss_streak(closed, window="day", now=now) if enabled and max_day > 0 else 0
  week_streak = trailing_loss_streak(closed, window="week", now=now) if enabled and max_week > 0 else 0
  day_dd = window_drawdown_r(closed, window="day", now=now) if enabled else 0.0
  week_dd = window_drawdown_r(closed, window="week", now=now) if enabled else 0.0
  day_r = window_total_r(closed, window="day", now=now) if enabled else 0.0
  week_r = window_total_r(closed, window="week", now=now) if enabled else 0.0
  return {
    "enabled": enabled,
    "max_day": max_day,
    "max_week": max_week,
    "max_day_dd_r": max_day_dd,
    "max_week_dd_r": max_week_dd,
    "max_day_loss_r": max_day_loss,
    "max_week_loss_r": max_week_loss,
    "day_streak": day_streak,
    "week_streak": week_streak,
    "day_dd_r": day_dd,
    "week_dd_r": week_dd,
    "day_total_r": day_r,
    "week_total_r": week_r,
    "tripped": bool(cfg.get("loss_guard_tripped")),
    "tripped_at": cfg.get("loss_guard_tripped_at"),
    "tripped_reason": cfg.get("loss_guard_tripped_reason"),
  }


def build_flat_halt_decision(
  bar: dict | None,
  *,
  reason: str,
  model_id: str | None = None,
) -> dict:
  bar = bar or {}
  now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  return {
    "action": "FLAT",
    "ok": True,
    "symbol": bar.get("symbol") or "GBPUSD",
    "bar_time": bar.get("time") or bar.get("bar_time"),
    "reason": reason,
    "halt": True,
    "halt_source": "loss_guard",
    "model_id": model_id,
    "updated_at": now,
    "signal_id": None,
    "entry": None,
    "sl": None,
    "tp": None,
  }


def apply_loss_guard_halt(
  trip: dict,
  *,
  bridge_dir: Path | None = None,
  bar: dict | None = None,
  model_id: str | None = None,
  model_ids: list[str] | None = None,
) -> dict:
  """Persist halt, force FLAT decision(s), disable service config."""
  from mt5_bridge.background import save_config
  from mt5_bridge.comm_log import append_event
  from mt5_bridge.protocol import (
    atomic_write_json,
    decision_path,
    ensure_bridge_dir,
    normalize_model_ids,
    write_model_decision,
    write_status,
  )

  bridge_dir = ensure_bridge_dir(bridge_dir)
  reason = str(trip.get("reason") or "Loss guard tripped")
  now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  save_config(
    enabled=False,
    loss_guard_tripped=True,
    loss_guard_tripped_at=now,
    loss_guard_tripped_reason=reason,
    last_error=reason,
    last_action="FLAT",
    last_run_at=now,
  )
  ids = normalize_model_ids(model_ids, fallback=model_id)
  primary = ids[0] if ids else model_id
  decision = build_flat_halt_decision(bar, reason=reason, model_id=primary)
  if ids:
    for mid in ids:
      d = build_flat_halt_decision(bar, reason=reason, model_id=mid)
      write_model_decision(
        d, bridge_dir=bridge_dir, mirror_primary=True, primary_model_id=primary,
      )
  else:
    atomic_write_json(decision_path(bridge_dir), decision)
  write_status(
    bridge_dir,
    state="halted",
    model_id=primary,
    model_ids=ids,
    error=reason,
    last_action="FLAT",
    reason=reason,
    halt_source="loss_guard",
    day_streak=trip.get("day_streak"),
    week_streak=trip.get("week_streak"),
  )
  append_event(
    "system",
    "loss_guard_halt",
    bridge_dir=bridge_dir,
    summary=reason,
    payload=trip,
  )
  return decision
