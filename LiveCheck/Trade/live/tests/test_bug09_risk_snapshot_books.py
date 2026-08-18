"""BUG-09: risk_status_snapshot must aggregate metrics across all books."""
from __future__ import annotations

import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))

import risk_prefs as rp  # noqa: E402


def test_risk_snapshot_aggregates_worst_dd_across_books(monkeypatch):
  monkeypatch.setattr(rp, "load_risk_prefs", lambda: {
    "loss_guard_enabled": True,
    "loss_guard_max_day": 3,
    "loss_guard_max_week": 5,
    "loss_guard_max_day_dd_r": 6.0,
    "loss_guard_max_week_dd_r": 10.0,
    "loss_guard_max_day_loss_r": 0.0,
    "loss_guard_max_week_loss_r": 0.0,
  })
  monkeypatch.setattr(rp, "any_worker_loss_guard_trip", lambda: {"tripped": False})

  import bridge_control
  monkeypatch.setattr(bridge_control, "load_config", lambda: {"loss_guard_tripped": False})

  rows = [
    {"enabled": True, "model_id": "a", "symbol": "EURUSD", "timeframe": "M15"},
    {"enabled": True, "model_id": "b", "symbol": "GBPUSD", "timeframe": "M15"},
  ]
  import package_store
  monkeypatch.setattr(package_store, "load_roster", lambda: {"models": rows})

  import runtime_bootstrap
  monkeypatch.setattr(runtime_bootstrap, "bootstrap_host", lambda *a, **k: Path("."))

  calls: list[str] = []

  def fake_status(cfg, bridge_dir=None, **kwargs):
    name = Path(bridge_dir).name if bridge_dir else ""
    calls.append(name)
    if "gbpusd" in name:
      return {
        "day_dd_r": 7.5, "week_dd_r": 8.0,
        "day_total_r": -5.0, "week_total_r": -6.0,
        "day_streak": 2, "week_streak": 2,
      }
    return {
      "day_dd_r": 1.0, "week_dd_r": 1.5,
      "day_total_r": 0.5, "week_total_r": 1.0,
      "day_streak": 0, "week_streak": 1,
    }

  import types
  fake_lg = types.SimpleNamespace(loss_guard_status=fake_status)
  # Inject before risk_status_snapshot does `from mt5_bridge.loss_guard import ...`
  sys.modules["mt5_bridge"] = types.SimpleNamespace(loss_guard=fake_lg)
  sys.modules["mt5_bridge.loss_guard"] = fake_lg

  import books

  def bridge_dir(sym, tf, sim=False):
    return Path(f"/tmp/bridge_live_{str(sym).lower()}_{str(tf).lower()}")

  def group_models_by_book(rs):
    out = {}
    for r in rs:
      key = (r["symbol"], r["timeframe"])
      out.setdefault(key, []).append(r)
    return out

  monkeypatch.setattr(books, "bridge_dir", bridge_dir)
  monkeypatch.setattr(books, "group_models_by_book", group_models_by_book)

  snap = rp.risk_status_snapshot()
  assert len(calls) >= 2
  assert any("gbpusd" in c for c in calls)
  assert snap["day_dd_r"] == 7.5
  assert snap["week_dd_r"] == 8.0
  assert snap["day_streak"] == 2
  assert snap["day_total_r"] == -4.5
  assert snap.get("books_scanned") == 2
