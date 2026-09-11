"""Trade Model Tpw: store from grid, derive from n / OOS span if missing."""
from __future__ import annotations

from gui.trade_model import realized_trades_per_week


def test_realized_tpw_prefers_stored_field():
  m = {
    "n_trades": 87,
    "trades_per_week": 3.35,
    "oos_from": "2026-01-01",
    "oos_to": "2026-06-30",
  }
  assert realized_trades_per_week(m) == 3.35


def test_realized_tpw_from_n_and_oos_span():
  m = {
    "n_trades": 87,
    "oos_from": "2026-01-01",
    "oos_to": "2026-06-30",
  }
  tpw = realized_trades_per_week(m)
  assert tpw is not None
  # 180 days / 7 ≈ 25.71 weeks → ~3.38
  assert 3.2 <= tpw <= 3.5


def test_realized_tpw_oos_report_wins():
  m = {"n_trades": 87, "oos_from": "2026-01-01", "oos_to": "2026-06-30"}
  oos = {"trades_per_week": 3.27, "n_trades": 85}
  assert realized_trades_per_week(m, oos) == 3.27


def test_realized_tpw_none_without_n():
  assert realized_trades_per_week({"oos_from": "2026-01-01", "oos_to": "2026-06-30"}) is None
