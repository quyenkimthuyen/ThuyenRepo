"""BUG-04: extend host loss_guard with DD(R) / total loss(R) trips.

LiveCheck Train desks only implement consecutive-loss streaks. Live UI stores
``loss_guard_max_*_dd_r`` / ``loss_guard_max_*_loss_r`` — wire them here.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


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
      return ts.to_pydatetime().replace(tzinfo=_local_now().tzinfo)
    return ts.to_pydatetime().astimezone()
  except Exception:
    return None


def trades_in_window(
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
  total = 0.0
  for t in trades_in_window(trades, window=window, now=now):
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
  eq = peak = 0.0
  dd = 0.0
  for t in trades_in_window(trades, window=window, now=now):
    try:
      r = float(t["r"]) if t.get("r") is not None else 0.0
    except (TypeError, ValueError):
      continue
    eq += r
    peak = max(peak, eq)
    dd = max(dd, peak - eq)
  return round(dd, 4)


def evaluate_loss_guard_extended(
  host_lg: Any,
  cfg: dict | None,
  *,
  bridge_dir: Path | None = None,
  trades: list[dict] | None = None,
  now: datetime | None = None,
) -> dict[str, Any] | None:
  """Streak + DD(R) + total loss(R) — same contract as Final_app loss_guard."""
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

  closed = host_lg.closed_auto_trades_chronologically(trades, bridge_dir=bridge_dir)
  day_streak = host_lg.trailing_loss_streak(closed, window="day", now=now) if max_day > 0 else 0
  week_streak = host_lg.trailing_loss_streak(closed, window="week", now=now) if max_week > 0 else 0
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


def loss_guard_status_extended(
  host_lg: Any,
  cfg: dict | None,
  *,
  bridge_dir: Path | None = None,
  trades: list[dict] | None = None,
  now: datetime | None = None,
) -> dict[str, Any]:
  cfg = cfg or {}
  max_day = int(cfg.get("loss_guard_max_day") or 0)
  max_week = int(cfg.get("loss_guard_max_week") or 0)
  max_day_dd = float(cfg.get("loss_guard_max_day_dd_r") or 0)
  max_week_dd = float(cfg.get("loss_guard_max_week_dd_r") or 0)
  max_day_loss = float(cfg.get("loss_guard_max_day_loss_r") or 0)
  max_week_loss = float(cfg.get("loss_guard_max_week_loss_r") or 0)
  enabled = bool(cfg.get("loss_guard_enabled", False))
  closed = (
    host_lg.closed_auto_trades_chronologically(trades, bridge_dir=bridge_dir)
    if enabled else []
  )
  day_streak = host_lg.trailing_loss_streak(closed, window="day", now=now) if enabled and max_day > 0 else 0
  week_streak = host_lg.trailing_loss_streak(closed, window="week", now=now) if enabled and max_week > 0 else 0
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


def patch_host_loss_guard(lg_module: Any) -> bool:
  """Replace host evaluate/status with DD-aware versions. Idempotent."""
  if getattr(lg_module, "_live_dd_ext", False):
    return False
  # Final_app already has DD — leave as-is
  if hasattr(lg_module, "window_drawdown_r") and hasattr(lg_module, "window_total_r"):
    lg_module._live_dd_ext = True
    return False

  def evaluate_loss_guard(cfg=None, *, bridge_dir=None, trades=None, now=None):  # noqa: ANN001
    return evaluate_loss_guard_extended(
      lg_module, cfg, bridge_dir=bridge_dir, trades=trades, now=now,
    )

  def loss_guard_status(cfg=None, *, bridge_dir=None, trades=None, now=None):  # noqa: ANN001
    return loss_guard_status_extended(
      lg_module, cfg, bridge_dir=bridge_dir, trades=trades, now=now,
    )

  lg_module.window_drawdown_r = window_drawdown_r
  lg_module.window_total_r = window_total_r
  lg_module.evaluate_loss_guard = evaluate_loss_guard
  lg_module.loss_guard_status = loss_guard_status
  lg_module._live_dd_ext = True
  return True
