"""BUG-04: DD(R) / loss(R) guards must trip (not streak-only)."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))

from loss_guard_ext import (  # noqa: E402
  evaluate_loss_guard_extended,
  window_drawdown_r,
  window_total_r,
)


def _today_trades(rs: list[float]) -> list[dict]:
  day = datetime.now().astimezone().strftime("%Y-%m-%d")
  out = []
  for i, r in enumerate(rs):
    out.append({
      "status": "CLOSED",
      "result": "LOSS" if r < 0 else ("WIN" if r > 0 else "BE"),
      "r": r,
      "exit_time": f"{day}T10:{i:02d}:00",
      "mode": "auto",
    })
  return out


def test_window_drawdown_r_peak_to_trough():
  # +2, -3, +1 → equity 2, -1, 0 → DD = 3
  trades = _today_trades([2.0, -3.0, 1.0])
  assert window_drawdown_r(trades, window="day") == pytest.approx(3.0)
  assert window_total_r(trades, window="day") == pytest.approx(0.0)


def test_dd_guard_trips_without_streak():
  """W/L/W/L pattern — streak never hits 3, but DD can exceed 6R."""
  # +1, -4, +1, -4 → equity 1,-3,-2,-6 → peak 1, DD=7
  trades = _today_trades([1.0, -4.0, 1.0, -4.0])

  host = SimpleNamespace(
    closed_auto_trades_chronologically=lambda trades=None, bridge_dir=None: trades or [],
    trailing_loss_streak=lambda closed, window="day", now=None: 1,  # never trips streak
  )
  trip = evaluate_loss_guard_extended(
    host,
    {
      "loss_guard_enabled": True,
      "loss_guard_max_day": 3,
      "loss_guard_max_week": 5,
      "loss_guard_max_day_dd_r": 6.0,
      "loss_guard_max_week_dd_r": 10.0,
      "loss_guard_max_day_loss_r": 0.0,
      "loss_guard_max_week_loss_r": 0.0,
    },
    trades=trades,
  )
  assert trip is not None
  assert trip["scope"] == "day_dd"
  assert trip["value"] >= 6.0
  assert trip.get("per_model") is True


def test_day_loss_r_trips():
  trades = _today_trades([-2.0, -2.0, 0.5])  # total -3.5
  host = SimpleNamespace(
    closed_auto_trades_chronologically=lambda trades=None, bridge_dir=None: trades or [],
    trailing_loss_streak=lambda *a, **k: 0,
  )
  trip = evaluate_loss_guard_extended(
    host,
    {
      "loss_guard_enabled": True,
      "loss_guard_max_day": 0,
      "loss_guard_max_week": 0,
      "loss_guard_max_day_dd_r": 0.0,
      "loss_guard_max_week_dd_r": 0.0,
      "loss_guard_max_day_loss_r": 3.0,
      "loss_guard_max_week_loss_r": 0.0,
    },
    trades=trades,
  )
  assert trip is not None
  assert trip["scope"] == "day_loss"
  assert trip.get("per_model") is False
  assert trip["value"] == pytest.approx(-3.5)


def test_day_loss_is_sum_across_models():
  """Two models each −2R: neither hits 3R alone, desk sum −4R trips all."""
  day = datetime.now().astimezone().strftime("%Y-%m-%d")
  trades = [
    {
      "status": "CLOSED", "result": "LOSS", "r": -2.0, "model_id": "a",
      "exit_time": f"{day}T10:00:00", "mode": "auto",
    },
    {
      "status": "CLOSED", "result": "LOSS", "r": -2.0, "model_id": "b",
      "exit_time": f"{day}T10:01:00", "mode": "auto",
    },
  ]
  host = SimpleNamespace(
    closed_auto_trades_chronologically=lambda trades=None, bridge_dir=None: trades or [],
    trailing_loss_streak=lambda *a, **k: 0,
  )
  trip = evaluate_loss_guard_extended(
    host,
    {
      "loss_guard_enabled": True,
      "loss_guard_max_day_dd_r": 0.0,
      "loss_guard_max_week_dd_r": 0.0,
      "loss_guard_max_day_loss_r": 3.0,
    },
    trades=trades,
  )
  assert trip is not None
  assert trip["scope"] == "day_loss"
  assert trip.get("per_model") is False
  assert trip["value"] == pytest.approx(-4.0)


def test_dd_trips_only_the_bad_model():
  """Two models in one book: only the one with DD ≥ 6R is halted."""
  day = datetime.now().astimezone().strftime("%Y-%m-%d")
  trades = []
  for i, r in enumerate([-1.0, -1.0, -1.0]):
    trades.append({
      "status": "CLOSED",
      "result": "LOSS",
      "r": r,
      "model_id": "good",
      "exit_time": f"{day}T10:{i:02d}:00",
      "mode": "auto",
    })
  for i, r in enumerate([-2.0, -2.0, -2.0, -2.0]):
    trades.append({
      "status": "CLOSED",
      "result": "LOSS",
      "r": r,
      "model_id": "bad",
      "exit_time": f"{day}T11:{i:02d}:00",
      "mode": "auto",
    })
  host = SimpleNamespace(
    closed_auto_trades_chronologically=lambda trades=None, bridge_dir=None: trades or [],
    trailing_loss_streak=lambda *a, **k: 0,
  )
  trip = evaluate_loss_guard_extended(
    host,
    {
      "loss_guard_enabled": True,
      "loss_guard_max_day_dd_r": 6.0,
      "loss_guard_max_week_dd_r": 10.0,
      "loss_guard_max_day_loss_r": 0.0,
    },
    trades=trades,
  )
  assert trip is not None
  assert trip["per_model"] is True
  assert trip["model_id"] == "bad"
  assert trip["scope"] == "day_dd"
  assert trip["value"] >= 6.0

