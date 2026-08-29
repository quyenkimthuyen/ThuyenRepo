"""BUG-05: flatten/kill must discover all book bridge dirs even if roster parse fails."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))


def test_flatten_discovers_bridge_dirs_from_disk_when_roster_raises(tmp_path, monkeypatch):
  import json
  import live_config
  import safety as safety_mod

  monkeypatch.setattr(safety_mod, "RESULTS_DIR", tmp_path)
  monkeypatch.setattr(safety_mod, "BRIDGE_DIR", tmp_path / "bridge_live")

  mt5 = tmp_path / "mt5"
  book = mt5 / "bridge_live_eurusd_m15"
  book.mkdir(parents=True)
  monkeypatch.setattr(live_config, "MT5_ROOT", mt5)

  def boom():
    raise RuntimeError("corrupt roster")

  monkeypatch.setattr(safety_mod, "load_roster", boom)

  safety_mod.write_flatten_command(reason="test")
  assert (book / "command.json").exists()
  cmd = json.loads((book / "command.json").read_text(encoding="utf-8"))
  assert cmd["action"] == "FLAT"
  # Legacy bridge_live also gets a command
  assert (tmp_path / "bridge_live" / "command.json").exists()
