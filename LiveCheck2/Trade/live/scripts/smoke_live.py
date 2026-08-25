#!/usr/bin/env python3
"""E2E smoke tests for Live split_app (no MT5 required for most checks).

Multi-book aware. Non-destructive to an already-running Live session:
does not stop workers that were running before the smoke started.
"""
from __future__ import annotations

import json
import shutil
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

  from bridge_control import is_running, prepare_runtime, status, stop_bridge

  was_running = bool(is_running())

  # 1) Host resolution
  from runtime_host import resolve_host_desk
  desk = resolve_host_desk("EURUSD", "M5")
  assert desk.name == "EdgeMinerEURUSDM5", desk
  _ok(f"host desk {desk.name}")

  # 2) Roster + materialize (multi-book OK)
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
  groups = list(mat.get("groups") or [])
  assert groups, mat
  m5_group = next(
    (g for g in groups if g.get("symbol") == "EURUSD" and g.get("timeframe") == "M5"),
    None,
  )
  assert m5_group, f"EURUSD M5 group missing in {[(g.get('symbol'), g.get('timeframe')) for g in groups]}"
  mid = str((m5_group.get("model_ids") or [None])[0])
  assert mid, m5_group

  store = json.loads((LIVE / "results" / "trade_models.json").read_text(encoding="utf-8"))
  models_by_id = {str(m.get("id")): m for m in (store.get("models") or [])}
  m0 = models_by_id.get(mid) or store["models"][0]
  assert m0.get("data_source") == "mt5_ea", m0
  assert m0.get("data_timeframe") == "M5", m0
  assert int(m0.get("feature_schema") or 0) >= 3, m0
  pin = LIVE / "results" / "trade_models" / f"{m0['id']}_kb_pin.json"
  assert pin.exists(), pin
  _ok(f"materialize n={mat['n']} groups={len(groups)} m5={mid}")

  # 3) Chart validation on an isolated temp bridge (do not touch live bar.json)
  from chart_validate import validate_chart_vs_roster

  m5_rows = [
    r for r in rows
    if str(r.get("symbol") or "").upper() == "EURUSD"
    and str(r.get("timeframe") or "").upper() == "M5"
    and r.get("enabled")
  ]
  chart_tmp = Path(tempfile.mkdtemp(prefix="smoke_chart_"))
  try:
    (chart_tmp / "connection.json").write_text(
      json.dumps({"symbol": "GBPUSD", "period": "M15", "connected": True}) + "\n",
      encoding="utf-8",
    )
    check = validate_chart_vs_roster(
      bridge_dir=chart_tmp,
      roster_rows=m5_rows,
      require_ea_online=False,
    )
    assert not check["ok"], check
    _ok("chart mismatch detected")

    (chart_tmp / "connection.json").write_text(
      json.dumps({"symbol": "EURUSD", "period": "M5", "connected": True}) + "\n",
      encoding="utf-8",
    )
    check = validate_chart_vs_roster(
      bridge_dir=chart_tmp,
      roster_rows=m5_rows,
      require_ea_online=True,
    )
    assert check["ok"], check
    _ok("chart match OK")
  finally:
    shutil.rmtree(chart_tmp, ignore_errors=True)

  # 4) Flatten + kill-switch
  from safety import (
    arm_kill_switch,
    disarm_kill_switch,
    is_kill_switch_armed,
    write_flatten_command,
  )

  flat = write_flatten_command(reason="smoke_flatten")
  assert flat["action"] == "FLAT"
  _ok("flatten command")

  prep = prepare_runtime(require_chart=False)
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

  # arm_kill_switch stops workers by design — restore Live if it was running.
  if was_running and not is_running():
    from bridge_control import start_bridge
    start_bridge(require_chart=False, auto_deploy_ea=True, skip_preflight=True)
    assert is_running(), "failed to restore live after kill-switch smoke"
    _ok("restored live after kill-switch smoke")

  # 5) Bootstrap host + resolve model (remine stack import)
  from runtime_bootstrap import bootstrap_host
  bootstrap_host("EURUSD", "M5", force=True)
  from mt5_bridge.models import get_model_by_id, get_model_run_params

  model = get_model_by_id(mid)
  assert model is not None, mid
  params = get_model_run_params(model)
  assert params.get("kb_pin_path"), params
  assert params.get("mining_search_space"), params
  _ok(f"BridgeEngine model resolve {mid}")

  # 6) BridgeEngine construct against a temp bridge dir (do not disturb live)
  from mt5_bridge.engine import BridgeEngine
  from shared.constants import LIVE_MAGIC_BASE

  tmp_bridge = Path(tempfile.mkdtemp(prefix="smoke_bridge_"))
  try:
    eng = BridgeEngine(
      model_id=mid,
      risk_pct=1.0,
      magic=int(LIVE_MAGIC_BASE),
      bridge_dir=tmp_bridge,
    )
    assert eng.model_id == mid
    assert eng._model.get("data_timeframe") == "M5"
    cache = Path(eng.mt5_cache)
    assert "split_app/live" in str(cache).replace("\\", "/"), cache
    _ok(f"BridgeEngine construct cache={cache.name}")

    # 7) Service --once on temp bridge (isolated from live workers)
    import subprocess
    svc = LIVE / "scripts" / "mt5_bridge_service_live.py"
    r = subprocess.run(
      [
        sys.executable, str(svc),
        "--symbol", "EURUSD", "--timeframe", "M5",
        "--model-ids", mid,
        "--bridge-dir", str(tmp_bridge),
        "--once",
      ],
      cwd=str(LIVE),
      capture_output=True,
      text=True,
      timeout=180,
    )
    if r.stdout:
      print(r.stdout[-800:])
    if r.returncode not in (0,):
      if r.stderr:
        print(r.stderr[-800:])
      _fail("service --once", f"exit {r.returncode}")
    _ok("service --once")
  finally:
    shutil.rmtree(tmp_bridge, ignore_errors=True)

  # 8) stop_bridge only when we did not interrupt a live session
  if was_running:
    st = status()
    assert st["running"], "live session should still be running"
    _ok("skip stop_bridge (live already running)")
  else:
    stop_bridge()
    st = status()
    assert not st["running"]
    _ok("stop_bridge")

  # 9) Journal helpers
  from journal_view import journal_summary
  journal_summary()
  _ok("journal_summary")

  # 10) EA PeriodTag present
  ea = SPLIT / "mt5" / "Experts" / "ForgeBridgeLive.mq5"
  ea_txt = ea.read_text(encoding="utf-8")
  assert "PeriodTag()" in ea_txt
  assert '"period\":\"M15\"' not in ea_txt.replace("PeriodTag()", "")
  _ok("EA PeriodTag")

  # 11) Deploy script identity
  dep = LIVE / "scripts" / "deploy_live_ea.ps1"
  dep_txt = dep.read_text(encoding="utf-8")
  for needle in ("ForgeBridgeLive", "bridge_live", "20283001", "EdgeMinerLive", "bridge_control", "FromRoster"):
    assert needle in dep_txt, needle
  _ok("deploy_live_ea.ps1")

  # 12) Package CRLF repair / checksum (Windows pull safety)
  from shared.package_format import repair_package_crlf, validate_package_dir
  from live_config import INSTALLED_DIR
  pkg = next(
    (d for d in sorted(INSTALLED_DIR.iterdir()) if d.is_dir() and not d.name.startswith((".", "_"))),
    None,
  )
  assert pkg is not None, "no installed package dir"
  repair_package_crlf(pkg)
  errs = validate_package_dir(pkg)
  assert not errs, errs
  _ok(f"package checksum OK {pkg.name}")

  print("=== ALL SMOKE PASSED ===")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
