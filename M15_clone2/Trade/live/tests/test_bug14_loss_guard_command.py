"""BUG-14: loss-guard halt must write command.json so EA closes open tickets."""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from types import SimpleNamespace

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))


def test_patched_apply_loss_guard_halt_writes_close_command(tmp_path, monkeypatch):
  import loss_guard_ext as ext

  bdir = tmp_path / "bridge_live_eurusd_m15"
  bdir.mkdir(parents=True)
  cfg = {"loss_guard_tripped": False}

  def fake_apply(trip, *, bridge_dir=None, bar=None, model_id=None, model_ids=None):
    cfg["loss_guard_tripped"] = True
    (Path(bridge_dir) / "decision.json").write_text(
      json.dumps({"action": "FLAT", "halt": True}),
      encoding="utf-8",
    )
    return {"action": "FLAT", "halt": True}

  written: list[dict] = []

  def fake_write_close(*, signal_id=None, bridge_dir=None, reason="x", **extra):
    payload = {
      "cmd": "close",
      "action": "FLAT",
      "signal_id": signal_id or "x",
      "reason": reason,
    }
    Path(bridge_dir).mkdir(parents=True, exist_ok=True)
    (Path(bridge_dir) / "command.json").write_text(
      json.dumps(payload), encoding="utf-8",
    )
    written.append(payload)
    return payload

  # Stub host package — bootstrap path is not required for unit patch test.
  pkg = types.ModuleType("mt5_bridge")
  bg = types.ModuleType("mt5_bridge.background")
  bg.load_config = lambda: dict(cfg)
  proto = types.ModuleType("mt5_bridge.protocol")
  proto.write_manual_close_command = fake_write_close
  monkeypatch.setitem(sys.modules, "mt5_bridge", pkg)
  monkeypatch.setitem(sys.modules, "mt5_bridge.background", bg)
  monkeypatch.setitem(sys.modules, "mt5_bridge.protocol", proto)

  lg = SimpleNamespace(
    apply_loss_guard_halt=fake_apply,
    window_drawdown_r=lambda *a, **k: 0.0,
    window_total_r=lambda *a, **k: 0.0,
    _live_dd_ext=True,  # DD already present — halt-close patch must still apply
  )

  assert ext.patch_host_loss_guard(lg) is True
  assert getattr(lg, "_live_halt_close", False)

  trip = {"reason": "day DD hit", "day_streak": 0}
  lg.apply_loss_guard_halt(trip, bridge_dir=bdir, model_id="tm_a")

  assert (bdir / "command.json").exists(), "halt must write command.json (BUG-14)"
  cmd = json.loads((bdir / "command.json").read_text(encoding="utf-8"))
  assert cmd["cmd"] == "close"
  assert cmd["action"] == "FLAT"
  assert written, "write_manual_close_command should be called on first trip"

  # Second apply while already tripped → no duplicate close spam
  written.clear()
  lg.apply_loss_guard_halt(trip, bridge_dir=bdir, model_id="tm_a")
  assert written == []


def test_per_model_halt_skips_book_wide_close(tmp_path, monkeypatch):
  import loss_guard_ext as ext

  bdir = tmp_path / "bridge_live_eurusd_m15"
  bdir.mkdir(parents=True)
  cfg = {"loss_guard_tripped": False, "loss_guard_halted_models": []}

  def fake_apply(trip, *, bridge_dir=None, bar=None, model_id=None, model_ids=None):
    mid = (trip or {}).get("model_id") or model_id
    cfg["loss_guard_halted_models"] = [mid]
    return {"action": "FLAT", "halt": True, "model_id": mid}

  written: list[dict] = []

  def fake_write_close(*, signal_id=None, bridge_dir=None, reason="x", **extra):
    written.append({"signal_id": signal_id, "reason": reason})
    return {}

  pkg = types.ModuleType("mt5_bridge")
  bg = types.ModuleType("mt5_bridge.background")
  bg.load_config = lambda: dict(cfg)
  proto = types.ModuleType("mt5_bridge.protocol")
  proto.write_manual_close_command = fake_write_close
  monkeypatch.setitem(sys.modules, "mt5_bridge", pkg)
  monkeypatch.setitem(sys.modules, "mt5_bridge.background", bg)
  monkeypatch.setitem(sys.modules, "mt5_bridge.protocol", proto)

  lg = SimpleNamespace(
    apply_loss_guard_halt=fake_apply,
    window_drawdown_r=lambda *a, **k: 0.0,
    window_total_r=lambda *a, **k: 0.0,
    _live_dd_ext=True,
  )
  assert ext.patch_host_loss_guard(lg) is True
  lg.apply_loss_guard_halt(
    {"reason": "model DD", "per_model": True, "model_id": "tm_bad"},
    bridge_dir=bdir,
    model_id="tm_bad",
  )
  assert written == []

