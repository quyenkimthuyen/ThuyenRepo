from __future__ import annotations

import json
from pathlib import Path

from mt5_bridge.protocol import DEFAULT_MAGIC as M15_MAGIC
from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT as M15_BRIDGE_PORT
from paper_live_monitor_server import DEFAULT_PAPER_MONITOR_PORT as M15_PAPER_PORT

M15_ROOT = Path(__file__).resolve().parents[1]
H1_ROOT = Path(r"C:\Work\ThuyenRepo\EdgeMinerH1")


def test_dual_runtime_resources_are_unique():
  from importlib.util import module_from_spec, spec_from_file_location

  protocol_spec = spec_from_file_location("h1_protocol", H1_ROOT / "mt5_bridge" / "protocol.py")
  h1_protocol = module_from_spec(protocol_spec)
  protocol_spec.loader.exec_module(h1_protocol)
  bridge_spec = spec_from_file_location(
    "h1_live_monitor", H1_ROOT / "mt5_bridge" / "live_monitor_server.py",
  )
  h1_live_monitor = module_from_spec(bridge_spec)
  bridge_spec.loader.exec_module(h1_live_monitor)
  paper_spec = spec_from_file_location(
    "h1_paper_monitor", H1_ROOT / "paper_live_monitor_server.py",
  )
  h1_paper_monitor = module_from_spec(paper_spec)
  paper_spec.loader.exec_module(h1_paper_monitor)

  assert M15_MAGIC == 20260724
  assert h1_protocol.DEFAULT_MAGIC == 20260725
  assert h1_protocol.DEFAULT_TIMEFRAME == "H1"
  assert h1_protocol.INSTANCE_ID == "H1"
  assert h1_protocol.BRIDGE_DIR == H1_ROOT / "mt5" / "bridge_h1"
  assert len({
    M15_BRIDGE_PORT, M15_PAPER_PORT,
    h1_live_monitor.DEFAULT_MONITOR_PORT,
    h1_paper_monitor.DEFAULT_PAPER_MONITOR_PORT,
  }) == 4


def test_h1_config_never_points_to_m15_bridge():
  config = json.loads(
    (H1_ROOT / "results" / "mt5_bridge_config.json").read_text(encoding="utf-8-sig"),
  )
  assert Path(config["bridge_dir"]) == H1_ROOT / "mt5" / "bridge_h1"


def test_process_scripts_are_repo_scoped():
  for root in (M15_ROOT, H1_ROOT):
    app_script = (root / "scripts" / "run_app_windows.ps1").read_text(encoding="utf-8-sig")
    deploy_script = (
      root / "scripts" / "deploy_xm_forgebridge.ps1"
    ).read_text(encoding="utf-8-sig")
    assert '-match "gui[/\\\\]app\\.py"' not in app_script
    assert "$escapedAppPath" in app_script
    assert "$escapedBridge" in deploy_script


def test_eas_use_magic_and_hedging_guards():
  m15 = (M15_ROOT / "mt5" / "Experts" / "ForgeBridge.mq5").read_text(encoding="utf-8")
  h1 = (H1_ROOT / "mt5" / "Experts" / "ForgeBridge.mq5").read_text(encoding="utf-8")
  assert 'const string INSTANCE_ID = "M15"' in m15
  assert 'const string INSTANCE_ID = "H1"' in h1
  assert "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING" in m15
  assert "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING" in h1
  assert 'InpBridgeSubdir   = "bridge_h1"' in h1
  assert "InpMagic          = 20260725" in h1
