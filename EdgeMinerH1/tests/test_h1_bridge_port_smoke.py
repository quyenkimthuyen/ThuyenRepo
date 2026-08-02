"""H1 dual-runtime / Bridge port smoke checks.

Fail loud on the regressions that previously broke Simulate BUY/SELL and dual deploy.
Run from EdgeMinerH1:
  python -m pytest tests/test_h1_bridge_port_smoke.py -q
"""
from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

H1_ROOT = Path(__file__).resolve().parents[1]
M15_ROOT = H1_ROOT.parent / "EdgeMinerM15"


def test_bridge_identity_and_ports_unique():
  from mt5_bridge.protocol import (
    BRIDGE_DIR,
    BRIDGE_SIM_DIR,
    DEFAULT_MAGIC,
    DEFAULT_SIM_MAGIC,
    DEFAULT_TIMEFRAME,
    INSTANCE_ID,
  )
  from mt5_bridge.live_monitor_server import DEFAULT_MONITOR_PORT, SIM_MONITOR_PORT

  assert INSTANCE_ID == "H1"
  assert DEFAULT_TIMEFRAME == "H1"
  assert BRIDGE_DIR.name == "bridge_h1"
  assert BRIDGE_SIM_DIR.name == "bridge_sim_h1"
  assert DEFAULT_MAGIC == 20260725
  assert DEFAULT_SIM_MAGIC == 20260727
  assert DEFAULT_MONITOR_PORT == 8865
  assert SIM_MONITOR_PORT == 8877

  if M15_ROOT.exists():
    import importlib.util

    def _load(name: str, path: Path):
      spec = importlib.util.spec_from_file_location(name, path)
      mod = importlib.util.module_from_spec(spec)
      assert spec.loader is not None
      spec.loader.exec_module(mod)
      return mod

    m15_proto = _load("m15_proto", M15_ROOT / "mt5_bridge" / "protocol.py")
    m15_mon = _load("m15_mon", M15_ROOT / "mt5_bridge" / "live_monitor_server.py")
    ports = {
      DEFAULT_MONITOR_PORT,
      SIM_MONITOR_PORT,
      m15_mon.DEFAULT_MONITOR_PORT,
      m15_mon.SIM_MONITOR_PORT,
    }
    assert len(ports) == 4
    assert m15_proto.BRIDGE_DIR.name == "bridge"
    assert m15_proto.BRIDGE_SIM_DIR.name == "bridge_sim"


def test_active_model_passes_bridge_guards():
  from mt5_bridge.models import get_model_run_params, resolve_model

  m = resolve_model()
  assert m is not None, "no active H1 trade model"
  assert m.get("data_source") == "mt5_ea"
  assert str(m.get("data_timeframe") or "").upper() == "H1"
  assert int(m.get("feature_schema") or 0) >= 2
  params = get_model_run_params(m)
  assert int(params["train_months"]) >= 1
  assert params.get("feature_profile") in ("current", "legacy")


def test_optimizer_accepts_search_space_kwarg():
  from optimizer import optimize_on_window

  sig = inspect.signature(optimize_on_window)
  assert "search_space" in sig.parameters


def test_eas_and_deploy_names():
  live = (H1_ROOT / "mt5" / "Experts" / "ForgeBridgeH1.mq5").read_text(encoding="utf-8")
  sim = (H1_ROOT / "mt5" / "Experts" / "ForgeBridgeH1Sim.mq5").read_text(encoding="utf-8")
  deploy = (H1_ROOT / "scripts" / "deploy_xm_forgebridge.ps1").read_text(encoding="utf-8-sig")
  assert 'InpBridgeSubdir   = "bridge_h1"' in live
  assert "InpMagic          = 20260725" in live
  assert 'InpBridgeSubdir   = "bridge_sim_h1"' in sim
  assert "InpMagic          = 20260727" in sim
  assert 'InpMode = BRIDGE_HISTORY_FEED' in sim
  assert '$EaNameLive = "ForgeBridgeH1"' in deploy
  assert '$EaNameSim = "ForgeBridgeH1Sim"' in deploy
  assert "Compile ONLY the EA" in deploy
  assert "Attached exactly one EA" in deploy
  assert "refusing to overwrite" in deploy
  assert "refusing to attach onto M15" in deploy or "period_size=60" in deploy


def test_run_dual_expected_keys_valid_pythonish():
  text = (H1_ROOT / "scripts" / "run_dual_edgeminer.ps1").read_text(encoding="utf-8-sig")
  assert 'M15 = @{ Period = "M15"' in text
  assert 'H1 = @{ Period = "H1"' in text
  assert text.count('H1 = @{ Period = "H1"') == 1
  assert "$Expected.M15.Magic -eq $Expected.H1.Magic" in text
  assert "Read-Connection" in text and "$Expected.M15" in text


def test_decide_for_bar_not_legacy_blocked():
  """One real decide call must not hit the old feature_schema blocker."""
  from mt5_bridge.engine import BridgeEngine
  from mt5_bridge.protocol import BRIDGE_SIM_DIR

  bar_path = BRIDGE_SIM_DIR / "bar.json"
  if not bar_path.exists():
    return
  bar = json.loads(bar_path.read_text(encoding="utf-8"))
  eng = BridgeEngine(bridge_dir=BRIDGE_SIM_DIR)
  d = eng.decide_for_bar(bar)
  assert d.get("reason") not in {
    "legacy_data_source_blocked",
    "legacy_feature_schema",
    "wrong_timeframe_model",
    "no_active_model",
  }
  assert d.get("action") in {"BUY", "SELL", "FLAT", "HOLD"}


def test_model_from_grid_row_ast_has_required_fields():
  src = (H1_ROOT / "gui" / "trade_model.py").read_text(encoding="utf-8")
  tree = ast.parse(src)
  fn = next(
    n for n in tree.body
    if isinstance(n, ast.FunctionDef) and n.name == "model_from_grid_row"
  )
  dump = ast.dump(fn)
  for key in (
    "feature_profile",
    "mining_search_space",
    "max_trades_per_week",
    "feature_schema",
  ):
    assert key in dump, f"model_from_grid_row missing {key}"
