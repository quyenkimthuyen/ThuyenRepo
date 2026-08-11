"""Live file-protocol order pipeline — bar → decision → fake EA fill → journal.

No MT5. Proves App `_cycle` can write EA-openable decisions and ingest open/close
fills end-to-end (the gap left by Live/Sim decision-parity tests).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mt5_bridge import background as bridge_bg
from mt5_bridge.paper_fill import PaperBook
from mt5_bridge.protocol import (
  atomic_write_json,
  bar_path,
  command_path,
  decision_path,
  decision_path_for,
  fill_path,
  read_json,
  status_path,
  write_manual_close_command,
  write_manual_market_command,
)
from mt5_bridge.trade_journal import load_trades, save_trades


MODEL_ID = "tm_live_pipeline"
MAGIC = 20261021


# --- helpers -----------------------------------------------------------------


def _ea_openable_fields(decision: dict) -> None:
  """Mirror ForgeBridge OpenFromDecision gates (Python side)."""
  action = str(decision.get("action") or "").upper()
  assert action in ("BUY", "SELL"), f"EA would skip action={action!r}"
  assert str(decision.get("signal_id") or ""), "EA needs signal_id"
  assert str(decision.get("bar_time") or decision.get("time") or ""), "EA WaitDecision needs bar_time"
  sl = float(decision.get("sl") or 0)
  tp = float(decision.get("tp") or 0)
  assert sl > 0 and tp > 0, f"EA rejects missing sl/tp: sl={sl} tp={tp}"
  assert decision.get("magic") is not None
  assert decision.get("model_id")


class StubEngine:
  """Minimal BridgeEngine stand-in for `_cycle` (no remine / parquet)."""

  def __init__(self, model_id: str = MODEL_ID, magic: int = MAGIC, risk_pct: float = 1.0):
    self.model_id = model_id
    self.magic = int(magic)
    self.risk_pct = float(risk_pct)
    self._last_decision: dict | None = None
    self._queue: list[dict] = []
    self._default_action = "FLAT"

  @property
  def conditions_fp(self) -> str:
    return "stub_live_pipeline_fp"

  def describe_conditions(self) -> dict:
    return {"source": "stub", "model_id": self.model_id}

  def enqueue(self, *decisions: dict) -> None:
    self._queue.extend(decisions)

  def decide_for_bar(self, bar: dict) -> dict:
    bar_time = str(bar.get("time") or bar.get("bar_time") or "")
    if self._queue:
      base = dict(self._queue.pop(0))
    else:
      base = {"action": self._default_action, "reason": "stub_idle"}
    action = str(base.get("action") or "FLAT").upper()
    decision = {
      "action": action,
      "reason": base.get("reason") or f"stub_{action.lower()}",
      "signal_id": base.get("signal_id") or (
        f"sig_{action}_{bar_time.replace(' ', '_').replace('.', '')}" if action in ("BUY", "SELL") else None
      ),
      "bar_time": base.get("bar_time") or bar_time,
      "entry": base.get("entry"),
      "sl": base.get("sl"),
      "tp": base.get("tp"),
      "rr": base.get("rr", 2.0),
      "exit_mode": base.get("exit_mode", "full"),
      "max_hold_bars": base.get("max_hold_bars", 96),
      "model_id": self.model_id,
      "magic": self.magic,
      "risk_pct": self.risk_pct,
      "conditions_fp": self.conditions_fp,
      "strategy_name": base.get("strategy_name") or "StubStrategy",
      "week_start": base.get("week_start") or "2026-01-05",
    }
    if action in ("BUY", "SELL"):
      entry = float(decision["entry"] if decision["entry"] is not None else bar.get("close") or 1.1000)
      decision["entry"] = entry
      if decision["sl"] is None:
        decision["sl"] = entry - 0.0010 if action == "BUY" else entry + 0.0010
      if decision["tp"] is None:
        decision["tp"] = entry + 0.0020 if action == "BUY" else entry - 0.0020
    self._last_decision = decision
    return decision


def _buy_decision(**overrides) -> dict:
  d = {
    "action": "BUY",
    "reason": "stub_signal",
    "signal_id": "sig_buy_live_1",
    "entry": 1.1000,
    "sl": 1.0990,
    "tp": 1.1020,
    "rr": 2.0,
  }
  d.update(overrides)
  return d


def _bar(time: str, close: float = 1.1000) -> dict:
  return {
    "symbol": "EURUSD",
    "time": time,
    "open": close,
    "high": close + 0.0005,
    "low": close - 0.0005,
    "close": close,
    "tick_volume": 100,
  }


def _open_fill(*, signal_id: str, magic: int = MAGIC, model_id: str = MODEL_ID, **extra) -> dict:
  fill = {
    "ok": True,
    "event": "open",
    "detail": "opened",
    "reason": "opened",
    "action": "BUY",
    "signal_id": signal_id,
    "ticket": 900001,
    "price": 1.10005,
    "sl": 1.09905,
    "tp": 1.10205,
    "lots": 0.1,
    "bar_time": "2026.03.10 10:00",
    "symbol": "EURUSD",
    "model_id": model_id,
    "magic": magic,
    "source": "strategy",
  }
  fill.update(extra)
  return fill


def _close_fill(*, signal_id: str, magic: int = MAGIC, model_id: str = MODEL_ID, **extra) -> dict:
  fill = {
    "ok": True,
    "event": "close",
    "detail": "closed",
    "reason": "tp",
    "action": "BUY",
    "signal_id": signal_id,
    "ticket": 900001,
    "price": 1.10205,
    "sl": 1.09905,
    "tp": 1.10205,
    "lots": 0.1,
    "profit": 20.0,
    "bar_time": "2026.03.10 12:00",
    "symbol": "EURUSD",
    "model_id": model_id,
    "magic": magic,
    "source": "strategy",
  }
  fill.update(extra)
  return fill


@pytest.fixture
def live_pipeline_env(tmp_path: Path, monkeypatch):
  bridge = tmp_path / "bridge"
  bridge.mkdir()
  cfg_path = tmp_path / "mt5_bridge_config.json"
  monkeypatch.setattr(bridge_bg, "CONFIG_PATH", cfg_path)
  bridge_bg._stop.clear()
  bridge_bg.save_config(
    enabled=True,
    model_id=MODEL_ID,
    model_ids=[MODEL_ID],
    risk_pct=1.0,
    poll_sec=2.0,
    bridge_dir=str(bridge),
    loss_guard_enabled=False,
    loss_guard_tripped=False,
    loss_guard_tripped_at=None,
    loss_guard_tripped_reason=None,
    last_error=None,
  )
  save_trades([], bridge)
  eng = StubEngine()
  return {"bridge": bridge, "eng": eng}


# --- tests -------------------------------------------------------------------


def test_cycle_writes_ea_openable_buy_decision(live_pipeline_env):
  bridge = live_pipeline_env["bridge"]
  eng = live_pipeline_env["eng"]
  eng.enqueue(_buy_decision())

  atomic_write_json(bar_path(bridge), _bar("2026.03.10 10:00"))
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, None, None)

  assert last_bar == "2026.03.10 10:00"
  decision = read_json(decision_path(bridge))
  assert decision is not None
  _ea_openable_fields(decision)
  assert decision["action"] == "BUY"
  assert decision["signal_id"] == "sig_buy_live_1"
  assert decision["bar_time"] == "2026.03.10 10:00"

  per_model = read_json(decision_path_for(MODEL_ID, bridge))
  assert per_model is not None
  assert per_model["signal_id"] == decision["signal_id"]

  status = read_json(status_path(bridge))
  assert status is not None
  assert status.get("state") == "decided"
  assert status.get("last_action") == "BUY"


def test_fake_ea_open_then_hold_on_next_bar(live_pipeline_env):
  bridge = live_pipeline_env["bridge"]
  eng = live_pipeline_env["eng"]
  eng.enqueue(_buy_decision())

  atomic_write_json(bar_path(bridge), _bar("2026.03.10 10:00"))
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, None, None)
  decision = read_json(decision_path(bridge))
  sid = decision["signal_id"]

  # Fake EA OrderSend → fill.json (same bar still on disk)
  atomic_write_json(fill_path(bridge), _open_fill(signal_id=sid))
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, last_bar, last_fill)

  trades = load_trades(bridge)
  assert len(trades) == 1
  assert trades[0]["status"] == "OPEN"
  assert trades[0]["signal_id"] == sid
  assert trades[0]["direction"] == "BUY"
  assert trades[0]["magic"] == MAGIC

  # Same bar fingerprint → idle (no rewrite storm)
  before = read_json(decision_path(bridge))
  last_bar2, last_fill2 = bridge_bg._cycle({MODEL_ID: eng}, bridge, last_bar, last_fill)
  assert last_bar2 == last_bar
  assert read_json(decision_path(bridge))["signal_id"] == before["signal_id"]

  # Next bar while position open → HOLD
  eng.enqueue({"action": "HOLD", "reason": "position_open", "signal_id": None})
  atomic_write_json(bar_path(bridge), _bar("2026.03.10 10:15", close=1.1005))
  last_bar3, _ = bridge_bg._cycle({MODEL_ID: eng}, bridge, last_bar2, last_fill2)

  hold = read_json(decision_path(bridge))
  assert hold is not None
  assert str(hold.get("action")).upper() == "HOLD"
  assert last_bar3 == "2026.03.10 10:15"
  assert load_trades(bridge)[0]["status"] == "OPEN"


def test_fake_ea_close_and_sticky_fill_dedupe_via_cycle(live_pipeline_env):
  bridge = live_pipeline_env["bridge"]
  eng = live_pipeline_env["eng"]
  eng.enqueue(_buy_decision())

  atomic_write_json(bar_path(bridge), _bar("2026.03.10 10:00"))
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, None, None)
  sid = read_json(decision_path(bridge))["signal_id"]

  atomic_write_json(fill_path(bridge), _open_fill(signal_id=sid))
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, last_bar, last_fill)
  assert load_trades(bridge)[0]["status"] == "OPEN"

  close = _close_fill(signal_id=sid)
  atomic_write_json(fill_path(bridge), close)
  # New bar so cycle is not idle-only; fill ingest runs before bar decide
  eng.enqueue({"action": "FLAT", "reason": "flat_after_close"})
  atomic_write_json(bar_path(bridge), _bar("2026.03.10 12:00", close=1.1020))
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, last_bar, last_fill)

  trades = load_trades(bridge)
  assert len(trades) == 1
  assert trades[0]["status"] == "CLOSED"
  assert trades[0]["r"] is not None
  assert float(trades[0]["r"]) > 0

  # Sticky fill.json re-read must not duplicate (Live restart / poll)
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, last_bar, last_fill)
  last_bar, last_fill = bridge_bg._cycle({MODEL_ID: eng}, bridge, last_bar, last_fill)
  assert len(load_trades(bridge)) == 1
  assert load_trades(bridge)[0]["status"] == "CLOSED"


def test_manual_market_and_close_command_shape(tmp_path: Path):
  bridge = tmp_path / "bridge_cmd"
  bridge.mkdir()

  market = write_manual_market_command(
    "BUY",
    sl=1.0990,
    tp=1.1020,
    signal_id="manual_test_pipeline",
    bridge_dir=bridge,
    magic=MAGIC,
    model_id=MODEL_ID,
  )
  on_disk = read_json(command_path(bridge))
  assert on_disk is not None
  assert on_disk["cmd"] == "market"
  assert on_disk["action"] == "BUY"
  assert float(on_disk["sl"]) == 1.0990
  assert float(on_disk["tp"]) == 1.1020
  assert on_disk["signal_id"] == "manual_test_pipeline"
  assert market["signal_id"] == on_disk["signal_id"]

  close = write_manual_close_command(
    signal_id="manual_close_pipeline",
    bridge_dir=bridge,
    magic=MAGIC,
  )
  on_disk2 = read_json(command_path(bridge))
  assert on_disk2["cmd"] == "close"
  assert on_disk2["action"] == "FLAT"
  assert on_disk2["signal_id"] == "manual_close_pipeline"
  assert close["cmd"] == "close"


def test_paperbook_opens_from_live_shaped_buy(tmp_path: Path):
  """Decision geometry → paper open (execution without OrderSend)."""
  bridge = tmp_path / "bridge_paper"
  bridge.mkdir()
  save_trades([], bridge)

  decision = {
    "action": "BUY",
    "signal_id": "sig_paper_live_1",
    "entry": 1.1000,
    "sl": 1.0990,
    "tp": 1.1020,
    "rr": 2.0,
    "exit_mode": "full",
    "max_hold_bars": 96,
    "model_id": MODEL_ID,
    "magic": MAGIC,
    "bar_time": "2026.03.10 10:00",
  }
  _ea_openable_fields(decision)

  book = PaperBook(bridge_dir=bridge, model_id=MODEL_ID)
  book.queue_decision(decision)
  # Entry at *next* bar open (HistoryFeed / Live paper convention)
  fills = book.on_bar(
    open_=1.1002,
    high=1.1008,
    low=1.0998,
    close=1.1004,
    bar_time="2026.03.10 10:15",
  )
  assert len(fills) == 1
  assert fills[0]["event"] == "open"
  assert fills[0]["action"] == "BUY"
  assert float(fills[0]["sl"]) > 0
  assert float(fills[0]["tp"]) > 0
  assert float(fills[0]["sl"]) < float(fills[0]["price"]) < float(fills[0]["tp"])

  trades = load_trades(bridge)
  assert len(trades) == 1
  assert trades[0]["status"] == "OPEN"
  assert trades[0]["signal_id"] == "sig_paper_live_1"


def test_multi_model_fill_routes_by_magic(tmp_path: Path, monkeypatch):
  bridge = tmp_path / "bridge_mm"
  bridge.mkdir()
  cfg_path = tmp_path / "mt5_bridge_config_mm.json"
  monkeypatch.setattr(bridge_bg, "CONFIG_PATH", cfg_path)
  bridge_bg._stop.clear()
  mid_a, mid_b = "tm_a", "tm_b"
  mag_a, mag_b = 20261021, 20261022
  bridge_bg.save_config(
    enabled=True,
    model_id=mid_a,
    model_ids=[mid_a, mid_b],
    risk_pct=1.0,
    bridge_dir=str(bridge),
    loss_guard_enabled=False,
    loss_guard_tripped=False,
  )
  save_trades([], bridge)

  eng_a = StubEngine(model_id=mid_a, magic=mag_a)
  eng_b = StubEngine(model_id=mid_b, magic=mag_b)
  eng_a.enqueue(_buy_decision(signal_id="sig_a"))
  eng_b.enqueue(_buy_decision(signal_id="sig_b", entry=1.1000, sl=1.0990, tp=1.1020))

  from mt5_bridge.protocol import write_models_roster

  write_models_roster(
    [mid_a, mid_b],
    risk_pct=1.0,
    bridge_dir=bridge,
    base_magic=mag_a,
  )

  atomic_write_json(bar_path(bridge), _bar("2026.03.10 10:00"))
  last_bar, last_fill = bridge_bg._cycle(
    {mid_a: eng_a, mid_b: eng_b}, bridge, None, None,
  )
  assert read_json(decision_path_for(mid_a, bridge))["signal_id"] == "sig_a"
  assert read_json(decision_path_for(mid_b, bridge))["signal_id"] == "sig_b"

  # Only model B fills — journal row must carry B's model_id/magic
  atomic_write_json(
    fill_path(bridge),
    _open_fill(signal_id="sig_b", magic=mag_b, model_id=mid_b, ticket=900002),
  )
  bridge_bg._cycle({mid_a: eng_a, mid_b: eng_b}, bridge, last_bar, last_fill)

  trades = load_trades(bridge)
  assert len(trades) == 1
  assert trades[0]["model_id"] == mid_b
  assert int(trades[0]["magic"]) == mag_b
  assert trades[0]["signal_id"] == "sig_b"
