"""Tests for MT5 Bridge consecutive-loss circuit breaker."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from mt5_bridge.loss_guard import (
  evaluate_loss_guard,
  trailing_loss_streak,
  closed_auto_trades_chronologically,
)
from mt5_bridge.trade_journal import MODE_AUTO, MODE_MANUAL


def _closed(result: str, when: datetime, *, mode: str = MODE_AUTO, r: float | None = None) -> dict:
  return {
    "status": "CLOSED",
    "result": result,
    "mode": mode,
    "r": r if r is not None else (-1.0 if result == "LOSS" else 1.0),
    "exit_time": when.isoformat(timespec="seconds"),
  }


def test_resolve_loss_guard_limits_refresh_keeps_config():
  from gui.views.mt5_bridge import resolve_loss_guard_limits

  day, week, reset = resolve_loss_guard_limits(
    prev_model_id=None,
    model_id="tm_a",
    cfg_max_day=7,
    cfg_max_week=12,
    suggested=3,
  )
  assert (day, week, reset) == (7, 12, False)


def test_resolve_loss_guard_limits_model_change_resets_to_suggested():
  from gui.views.mt5_bridge import resolve_loss_guard_limits

  day, week, reset = resolve_loss_guard_limits(
    prev_model_id="tm_old",
    model_id="tm_new",
    cfg_max_day=7,
    cfg_max_week=12,
    suggested=4,
  )
  assert (day, week, reset) == (4, 4, True)


def test_resolve_loss_guard_limits_same_model_keeps_widgets_via_cfg_fallback():
  from gui.views.mt5_bridge import resolve_loss_guard_limits

  day, week, reset = resolve_loss_guard_limits(
    prev_model_id="tm_a",
    model_id="tm_a",
    cfg_max_day=9,
    cfg_max_week=11,
    suggested=3,
  )
  assert (day, week, reset) == (9, 11, False)

  now = datetime.now().astimezone().replace(hour=15, minute=0, second=0, microsecond=0)
  today = now
  yesterday = now - timedelta(days=1)
  trades = [
    _closed("LOSS", yesterday),
    _closed("LOSS", yesterday),
    _closed("LOSS", today - timedelta(hours=3), mode=MODE_MANUAL),
    _closed("WIN", today - timedelta(hours=2)),
    _closed("LOSS", today - timedelta(hours=1)),
    _closed("LOSS", today - timedelta(minutes=30)),
  ]
  closed = closed_auto_trades_chronologically(trades)
  assert trailing_loss_streak(closed, window="day", now=now) == 2


def test_evaluate_loss_guard_trips_on_day_limit():
  now = datetime.now().astimezone().replace(hour=18, minute=0, second=0, microsecond=0)
  trades = [
    _closed("LOSS", now - timedelta(hours=2)),
    _closed("LOSS", now - timedelta(hours=1)),
    _closed("LOSS", now - timedelta(minutes=10)),
  ]
  trip = evaluate_loss_guard(
    {
      "loss_guard_enabled": True,
      "loss_guard_max_day": 3,
      "loss_guard_max_week": 5,
    },
    trades=trades,
    now=now,
  )
  assert trip is not None
  assert trip["scope"] == "day"
  assert trip["streak"] == 3


def test_evaluate_loss_guard_week_when_day_not_hit():
  now = datetime.now().astimezone()
  # Move to Wednesday of current ISO week at noon
  weekday = now.isoweekday()  # Mon=1
  now = (now - timedelta(days=weekday - 3)).replace(
    hour=12, minute=0, second=0, microsecond=0,
  )
  monday = now - timedelta(days=now.isoweekday() - 1)
  trades = [
    _closed("LOSS", monday),
    _closed("LOSS", monday + timedelta(hours=1)),
    _closed("LOSS", monday + timedelta(hours=2)),
    _closed("LOSS", now - timedelta(hours=2)),
    _closed("LOSS", now - timedelta(hours=1)),
  ]
  trip = evaluate_loss_guard(
    {
      "loss_guard_enabled": True,
      "loss_guard_max_day": 3,  # today only 2 losses
      "loss_guard_max_week": 5,
    },
    trades=trades,
    now=now,
  )
  assert trip is not None
  assert trip["scope"] == "week"
  assert trip["streak"] == 5


def test_guard_disabled_returns_none():
  now = datetime.now().astimezone()
  trades = [_closed("LOSS", now), _closed("LOSS", now), _closed("LOSS", now)]
  assert evaluate_loss_guard(
    {"loss_guard_enabled": False, "loss_guard_max_day": 2},
    trades=trades,
    now=now,
  ) is None


def test_win_breaks_trailing_streak():
  now = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0)
  trades = [
    _closed("LOSS", now - timedelta(hours=3)),
    _closed("LOSS", now - timedelta(hours=2)),
    _closed("WIN", now - timedelta(hours=1)),
    _closed("LOSS", now - timedelta(minutes=20)),
  ]
  closed = closed_auto_trades_chronologically(trades)
  assert trailing_loss_streak(closed, window="day", now=now) == 1


def test_default_streak_limit_from_model_dd():
  from mt5_bridge.loss_guard import default_streak_limit_from_model
  assert default_streak_limit_from_model({"max_drawdown_r": 11.35}) == 12
  assert default_streak_limit_from_model({"max_drawdown_r": 2.53}) == 3
  assert default_streak_limit_from_model({"max_drawdown_r": 0.4}) == 1
  assert default_streak_limit_from_model({}) == 3
