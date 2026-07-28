"""Dual-runtime contract for EdgeLiveEURH1M15 (H1+M15 Live/Sim in one app)."""
from __future__ import annotations

from pathlib import Path

from runtime_profiles import PROFILES, all_profiles, get_profile
from mt5_bridge.live_monitor_server import (
  DEFAULT_MONITOR_PORT,
  H1_MONITOR_PORT,
  H1_SIM_MONITOR_PORT,
  SIM_MONITOR_PORT,
  monitor_port_for,
)
from mt5_bridge.protocol import BRIDGE_DIR, BRIDGE_SIM_DIR, bridge_dir_for

ROOT = Path(__file__).resolve().parents[1]


def test_four_profiles_are_unique():
  profiles = all_profiles()
  assert len(profiles) == 4
  magics = {p.magic for p in profiles}
  ports = {p.monitor_port for p in profiles}
  dirs = {p.bridge_subdir for p in profiles}
  assert len(magics) == 4
  assert len(ports) == 4
  assert len(dirs) == 4
  assert magics == {20260724, 20260725, 20260726, 20260727}
  assert ports == {8765, 8865, 8876, 8877}
  assert dirs == {"bridge_m15", "bridge_sim_m15", "bridge_h1", "bridge_sim_h1"}


def test_bridge_dir_names_are_consistent():
  assert BRIDGE_DIR.name == "bridge_m15"
  assert BRIDGE_SIM_DIR.name == "bridge_sim_m15"
  assert bridge_dir_for("H1", "live").name == "bridge_h1"
  assert bridge_dir_for("H1", "sim").name == "bridge_sim_h1"
  assert bridge_dir_for("M15", "live").name == "bridge_m15"
  assert bridge_dir_for("M15", "sim").name == "bridge_sim_m15"
  for name in ("bridge_m15", "bridge_sim_m15", "bridge_h1", "bridge_sim_h1"):
    assert (ROOT / "mt5" / name).is_dir()


def test_monitor_ports_match_profiles():
  assert DEFAULT_MONITOR_PORT == 8765
  assert SIM_MONITOR_PORT == 8876
  assert H1_MONITOR_PORT == 8865
  assert H1_SIM_MONITOR_PORT == 8877
  assert monitor_port_for("M15", "live") == 8765
  assert monitor_port_for("M15", "sim") == 8876
  assert monitor_port_for("H1", "live") == 8865
  assert monitor_port_for("H1", "sim") == 8877


def test_tf_scoped_results():
  from config import set_active_tf
  from tf_context import REPORT_DIR
  set_active_tf("H1")
  assert Path(REPORT_DIR).name == "h1"
  set_active_tf("M15")
  assert Path(REPORT_DIR).name == "m15"


def test_no_paper_modules():
  assert not (ROOT / "paper_monitor.py").exists()
  assert not (ROOT / "paper_service.py").exists()
  assert not (ROOT / "gui" / "views" / "paper_monitor.py").exists()


def test_eas_use_consistent_bridge_subdirs():
  m15 = (ROOT / "mt5" / "Experts" / "ForgeBridgeM15.mq5").read_text(encoding="utf-8")
  m15_sim = (ROOT / "mt5" / "Experts" / "ForgeBridgeM15Sim.mq5").read_text(encoding="utf-8")
  h1 = (ROOT / "mt5" / "Experts" / "ForgeBridgeH1.mq5").read_text(encoding="utf-8")
  h1_sim = (ROOT / "mt5" / "Experts" / "ForgeBridgeH1Sim.mq5").read_text(encoding="utf-8")
  assert 'InpBridgeSubdir   = "bridge_m15"' in m15
  assert 'InpBridgeSubdir   = "bridge_sim_m15"' in m15_sim
  assert 'InpBridgeSubdir   = "bridge_h1"' in h1
  assert 'InpBridgeSubdir   = "bridge_sim_h1"' in h1_sim
  assert "InpMagic          = 20260724" in m15
  assert "InpMagic          = 20260726" in m15_sim
  assert "InpMagic          = 20260725" in h1
  assert "InpMagic          = 20260727" in h1_sim
  assert 'const string INSTANCE_ID = "M15"' in m15
  assert 'const string INSTANCE_ID = "H1"' in h1


def test_deploy_script_covers_all_four_eas():
  deploy = (ROOT / "scripts" / "deploy_xm_forgebridge.ps1").read_text(encoding="utf-8-sig")
  for name in (
    "ForgeBridgeM15", "ForgeBridgeM15Sim",
    "ForgeBridgeH1", "ForgeBridgeH1Sim",
  ):
    assert name in deploy
  for sub in ("bridge_m15", "bridge_sim_m15", "bridge_h1", "bridge_sim_h1"):
    assert sub in deploy


def test_deploy_all_script_exists():
  all_script = ROOT / "scripts" / "deploy_all_forgebridge.ps1"
  assert all_script.is_file()
  text = all_script.read_text(encoding="utf-8-sig")
  assert "M15" in text and "H1" in text
  assert "Live" in text and "HistoryFeed" in text
  assert "deploy_xm_forgebridge.ps1" in text


def test_ea_deploy_helper_lists_four_eas():
  from gui.ea_deploy import ALL_EA_LABELS, DEPLOY_ALL
  assert len(ALL_EA_LABELS) == 4
  assert DEPLOY_ALL.is_file()
  assert "ForgeBridgeH1Sim" in ALL_EA_LABELS
