"""Tests for runtime max-trades-per-day limits."""
from __future__ import annotations

from mt5_bridge.risk_limits import model_default_max_trades, resolve_max_trades_per_day


def test_resolve_max_trades_bridge_override_wins():
  cfg = {"max_trades_per_day_by_model": {"tm_a": 1}}
  assert resolve_max_trades_per_day("tm_a", 5, model={"max_trades_per_day": 3}, cfg=cfg) == 1


def test_resolve_max_trades_falls_back_to_model():
  assert resolve_max_trades_per_day("tm_a", 5, model={"max_trades_per_day": 3}, cfg={}) == 3


def test_resolve_max_trades_falls_back_to_strategy():
  assert resolve_max_trades_per_day("tm_a", 4, model={}, cfg={}) == 4


def test_model_default_max_trades():
  assert model_default_max_trades({}) >= 1
  assert model_default_max_trades({"max_trades_per_day": 7}) == 7
