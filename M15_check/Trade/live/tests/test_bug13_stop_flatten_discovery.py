"""BUG-13: stop_bridge(flatten=True) must discover all bridge_live_* dirs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))


def test_stop_bridge_flatten_discovers_disk_books_beyond_workers(tmp_path, monkeypatch):
  import bridge_control as bc
  import live_config
  import safety as safety_mod

  monkeypatch.setattr(bc, "RESULTS_DIR", tmp_path)
  monkeypatch.setattr(bc, "BRIDGE_DIR", tmp_path / "bridge_live")
  monkeypatch.setattr(safety_mod, "RESULTS_DIR", tmp_path)
  monkeypatch.setattr(safety_mod, "BRIDGE_DIR", tmp_path / "bridge_live")

  mt5 = tmp_path / "mt5"
  known = mt5 / "bridge_live_eurusd_m15"
  orphan = mt5 / "bridge_live_gbpusd_m15"
  known.mkdir(parents=True)
  orphan.mkdir(parents=True)
  monkeypatch.setattr(live_config, "MT5_ROOT", mt5)

  monkeypatch.setattr(
    bc,
    "load_workers",
    lambda sim=False: {
      "workers": [
        {
          "pid": None,
          "key": "eurusd_m15",
          "symbol": "EURUSD",
          "timeframe": "M15",
          "bridge_dir": str(known),
        }
      ]
    },
  )
  monkeypatch.setattr(bc, "_kill_pid", lambda pid: None)
  monkeypatch.setattr(bc, "save_workers", lambda workers, sim=False: None)
  monkeypatch.setattr(bc, "save_config", lambda **kw: None)
  monkeypatch.setattr(bc, "load_config", lambda: {})
  monkeypatch.setattr(safety_mod, "load_roster", lambda: {"models": []})

  bc.stop_bridge(flatten=True, sync_autostart=False)

  assert (known / "command.json").exists()
  assert (orphan / "command.json").exists(), (
    "Stop+flatten must still FLAT orphan book dirs on disk (BUG-13)"
  )
  cmd = json.loads((orphan / "command.json").read_text(encoding="utf-8"))
  assert cmd["action"] == "FLAT"
  assert cmd.get("cmd") == "close"
