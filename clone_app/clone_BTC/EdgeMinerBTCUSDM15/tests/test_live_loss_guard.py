"""Live-mode loss guard — end-to-end halt behavior (config + FLAT + disable)."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mt5_bridge import background as bridge_bg
from mt5_bridge.loss_guard import default_streak_limit_from_model
from mt5_bridge.protocol import decision_path, read_json, status_path
from mt5_bridge.trade_journal import MODE_AUTO, save_trades


def _loss(when: datetime, i: int) -> dict:
  return {
    "id": f"t{i}",
    "ticket": 800000 + i,
    "status": "CLOSED",
    "result": "LOSS",
    "mode": MODE_AUTO,
    "direction": "SELL",
    "r": -1.0,
    "profit": -10.0,
    "exit_time": when.isoformat(timespec="seconds"),
    "entry_time": (when - timedelta(hours=1)).isoformat(timespec="seconds"),
  }


@pytest.fixture
def live_guard_env(tmp_path: Path, monkeypatch):
  """Isolated Live bridge dir + config so tests never touch real service files."""
  bridge = tmp_path / "bridge"
  bridge.mkdir()
  cfg_path = tmp_path / "mt5_bridge_config.json"
  monkeypatch.setattr(bridge_bg, "CONFIG_PATH", cfg_path)
  bridge_bg._stop.clear()
  bridge_bg.save_config(
    enabled=True,
    model_id="tm_test_guard",
    risk_pct=1.0,
    poll_sec=2.0,
    loss_guard_enabled=True,
    loss_guard_max_day=3,
    loss_guard_max_week=5,
    loss_guard_tripped=False,
    loss_guard_tripped_at=None,
    loss_guard_tripped_reason=None,
    last_error=None,
  )
  return {"bridge": bridge, "cfg_path": cfg_path}


def test_live_loss_guard_halts_service_and_writes_flat(live_guard_env):
  bridge = live_guard_env["bridge"]
  now = datetime.now().astimezone().replace(microsecond=0)
  trades = [_loss(now - timedelta(minutes=30 - i), i) for i in range(3)]
  save_trades(trades, bridge)

  bar = {
    "symbol": "BTCUSD",
    "time": now.strftime("%Y.%m.%d %H:%M"),
    "close": 1.0850,
  }
  trip = bridge_bg.check_and_apply_loss_guard(
    bridge_dir=bridge,
    bar=bar,
    model_id="tm_test_guard",
  )

  assert trip is not None
  assert trip["scope"] == "day"
  assert trip["streak"] == 3
  assert bridge_bg._stop.is_set()

  cfg = bridge_bg.load_config()
  assert cfg["enabled"] is False
  assert cfg["loss_guard_tripped"] is True
  assert "thua liên tiếp" in str(cfg.get("loss_guard_tripped_reason") or "")

  decision = read_json(decision_path(bridge))
  assert decision is not None
  assert str(decision.get("action")).upper() == "FLAT"
  assert decision.get("halt") is True
  assert decision.get("halt_source") == "loss_guard"

  status = read_json(status_path(bridge))
  assert status is not None
  assert status.get("state") == "halted"


def test_live_loss_guard_does_not_trip_below_threshold(live_guard_env):
  bridge = live_guard_env["bridge"]
  now = datetime.now().astimezone().replace(microsecond=0)
  save_trades([_loss(now - timedelta(minutes=10), 1), _loss(now, 2)], bridge)

  trip = bridge_bg.check_and_apply_loss_guard(
    bridge_dir=bridge,
    bar={"symbol": "BTCUSD", "time": now.strftime("%Y.%m.%d %H:%M"), "close": 1.08},
    model_id="tm_test_guard",
  )
  assert trip is None
  assert not bridge_bg._stop.is_set()
  cfg = bridge_bg.load_config()
  assert cfg["enabled"] is True
  assert cfg["loss_guard_tripped"] is False
  assert read_json(decision_path(bridge)) is None


def test_live_loss_guard_picks_up_new_threshold_without_restart(live_guard_env):
  """Đổi max_day lúc service 'đang chạy' (config file) → cycle sau dùng ngưỡng mới."""
  bridge = live_guard_env["bridge"]
  now = datetime.now().astimezone().replace(microsecond=0)
  save_trades(
    [_loss(now - timedelta(minutes=20), 1), _loss(now - timedelta(minutes=10), 2), _loss(now, 3)],
    bridge,
  )

  # Still at max_day=3 from fixture → would trip; first lower... wait we have 3 losses.
  # Start with max_day=5 so 3 losses are safe, then tighten to 3.
  bridge_bg.save_config(loss_guard_max_day=5)
  trip = bridge_bg.check_and_apply_loss_guard(bridge_dir=bridge, model_id="tm_test_guard")
  assert trip is None
  assert bridge_bg.load_config()["enabled"] is True

  bridge_bg.save_config(loss_guard_max_day=3)  # user chỉnh setting khi service chạy
  trip2 = bridge_bg.check_and_apply_loss_guard(bridge_dir=bridge, model_id="tm_test_guard")
  assert trip2 is not None
  assert trip2["streak"] == 3
  assert bridge_bg.load_config()["enabled"] is False


def test_live_default_threshold_from_model_max_dd():
  assert default_streak_limit_from_model({"max_drawdown_r": 4.62}) == 5
  assert default_streak_limit_from_model({"max_drawdown_r": 11.35}) == 12
