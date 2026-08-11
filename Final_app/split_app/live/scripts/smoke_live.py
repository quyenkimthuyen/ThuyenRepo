#!/usr/bin/env python3
"""E2E smoke tests for Live split_app (no MT5 required for most checks)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))


def _ok(name: str) -> None:
  print(f"  OK  {name}")


def _fail(name: str, msg: str) -> None:
  print(f"FAIL  {name}: {msg}")
  raise SystemExit(1)


def main() -> int:
  print("=== Live smoke ===")

  # 1) Host resolution
  from runtime_host import resolve_host_desk
  desk = resolve_host_desk("EURUSD", "M5")
  assert desk.name == "EdgeMinerEURUSDM5", desk
  _ok(f"host desk {desk.name}")

  # 2) Roster + materialize demo package
  from package_store import default_roster_from_installed, list_installed, save_roster
  from magic_allocator import assign_magics
  from materialize_models import materialize_enabled

  installed = list_installed()
  if not installed:
    _fail("installed", "no demo package — import packages_out demo first")
  rows = assign_magics(default_roster_from_installed(), sim=False)
  save_roster(rows)
  mat = materialize_enabled()
  assert mat["n"] >= 1, mat
  assert mat["symbol"] == "EURUSD" and mat["timeframe"] == "M5", mat
  store = json.loads((LIVE / "results" / "trade_models.json").read_text(encoding="utf-8"))
  m0 = store["models"][0]
  assert m0.get("data_source") == "mt5_ea", m0
  assert m0.get("data_timeframe") == "M5", m0
  assert int(m0.get("feature_schema") or 0) >= 3, m0
  pin = LIVE / "results" / "trade_models" / f"{m0['id']}_kb_pin.json"
  assert pin.exists(), pin
  _ok(f"materialize {mat['model_ids']}")

  # 3) Chart validation — mismatch + match
  from chart_validate import validate_chart_vs_roster
  from live_config import BRIDGE_DIR

  BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
  bad = BRIDGE_DIR / "connection.json"
  bad.write_text(
    json.dumps({"symbol": "GBPUSD", "period": "M15", "connected": True}) + "\n",
    encoding="utf-8",
  )
  check = validate_chart_vs_roster(require_ea_online=False)
  assert not check["ok"], check
  _ok("chart mismatch detected")

  bad.write_text(
    json.dumps({"symbol": "EURUSD", "period": "M5", "connected": True}) + "\n",
    encoding="utf-8",
  )
  check = validate_chart_vs_roster(require_ea_online=True)
  assert check["ok"], check
  _ok("chart match OK")

  # 4) Flatten + kill-switch (no long-running bridge)
  from safety import (
    arm_kill_switch,
    disarm_kill_switch,
    is_kill_switch_armed,
    write_flatten_command,
  )
  from bridge_control import prepare_runtime, status, stop_bridge

  flat = write_flatten_command(reason="smoke_flatten")
  assert (BRIDGE_DIR / "command.json").exists()
  assert flat["action"] == "FLAT"
  _ok("flatten command")

  prep = prepare_runtime(require_chart=True)
  assert prep["materialize"]["n"] >= 1
  _ok("prepare_runtime")

  arm_kill_switch(reason="smoke_kill", flatten=True)
  assert is_kill_switch_armed()
  try:
    prepare_runtime()
    _fail("kill_switch", "prepare should refuse when armed")
  except RuntimeError:
    _ok("kill-switch blocks start")
  disarm_kill_switch()
  assert not is_kill_switch_armed()
  _ok("kill-switch disarm")

  # 5) Bootstrap host + resolve model (remine stack import)
  from runtime_bootstrap import bootstrap_host
  bootstrap_host("EURUSD", "M5", force=True)
  from mt5_bridge.models import get_model_by_id, get_model_run_params

  mid = mat["model_ids"][0]
  model = get_model_by_id(mid)
  assert model is not None, mid
  params = get_model_run_params(model)
  assert params.get("kb_pin_path"), params
  assert params.get("mining_search_space"), params
  _ok(f"BridgeEngine model resolve {mid}")

  # 6) BridgeEngine construct (no history yet — should not crash)
  from mt5_bridge.engine import BridgeEngine
  from shared.constants import LIVE_MAGIC_BASE

  eng = BridgeEngine(
    model_id=mid,
    risk_pct=1.0,
    magic=int(LIVE_MAGIC_BASE),
    bridge_dir=BRIDGE_DIR,
  )
  assert eng.model_id == mid
  assert eng._model.get("data_timeframe") == "M5"
  cache = Path(eng.mt5_cache)
  assert "split_app/live" in str(cache).replace("\\", "/"), cache
  _ok(f"BridgeEngine construct cache={cache.name}")

  # 7) Service --once (no cache → exit 0 syncing)
  import subprocess
  svc = LIVE / "scripts" / "mt5_bridge_service_live.py"
  # Remove cache if any so --once returns quickly
  cache_glob = list((LIVE / "results" / "data").glob("mt5_*.parquet")) if (LIVE / "results" / "data").exists() else []
  r = subprocess.run(
    [
      sys.executable, str(svc),
      "--symbol", "EURUSD", "--timeframe", "M5",
      "--model-ids", mid,
      "--bridge-dir", str(BRIDGE_DIR),
      "--once",
    ],
    cwd=str(LIVE),
    capture_output=True,
    text=True,
    timeout=120,
  )
  print(r.stdout[-800:] if r.stdout else "")
  if r.returncode not in (0,):
    print(r.stderr[-800:] if r.stderr else "")
    _fail("service --once", f"exit {r.returncode}")
  _ok("service --once")

  stop_bridge()
  st = status()
  assert not st["running"]
  _ok("stop_bridge")

  # 8) Journal helpers
  from journal_view import journal_summary
  journal_summary()
  _ok("journal_summary")

  # 9) EA PeriodTag present
  ea = SPLIT / "mt5" / "Experts" / "ForgeBridgeLive.mq5"
  ea_txt = ea.read_text(encoding="utf-8")
  assert "PeriodTag()" in ea_txt
  assert '"period\":\"M15\"' not in ea_txt.replace("PeriodTag()", "")
  _ok("EA PeriodTag")

  # 10) Deploy script identity
  dep = LIVE / "scripts" / "deploy_live_ea.ps1"
  dep_txt = dep.read_text(encoding="utf-8")
  for needle in ("ForgeBridgeLive", "bridge_live", "20263001", "EdgeMinerLive", "bridge_control"):
    assert needle in dep_txt, needle
  _ok("deploy_live_ea.ps1")

  print("=== ALL SMOKE PASSED ===")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
