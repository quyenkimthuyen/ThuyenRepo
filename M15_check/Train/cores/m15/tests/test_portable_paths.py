"""Copied TrainApp2 folder must remap stale absolute paths."""
from __future__ import annotations

import json
from pathlib import Path

from app_paths import get_core_root, get_root, relocate_under_root

ROOT = Path(__file__).resolve().parents[3]


def test_relocate_maps_old_train_bridge_into_this_runtime(tmp_path, monkeypatch):
  runtime = tmp_path / "runtime" / "e21"
  runtime.mkdir(parents=True)
  stale = r"C:\Work\ThuyenRepo\LiveCheck\Train\M15\EdgeMinerEURUSDM15\mt5\bridge_m15e21"
  got = relocate_under_root(stale, root=runtime)
  assert got == (runtime / "mt5" / "bridge_m15e21").resolve()


def test_relocate_remaps_existing_sibling_clone_bridge(tmp_path):
  sibling = tmp_path / "M15" / "Train" / "runtime" / "e21" / "mt5" / "bridge_lc2_e21"
  sibling.mkdir(parents=True)
  runtime = tmp_path / "M15_check" / "Train" / "runtime" / "e21"
  runtime.mkdir(parents=True)
  got = relocate_under_root(str(sibling), root=runtime)
  assert got == (runtime / "mt5" / "bridge_lc2_e21").resolve()


def test_relocate_keeps_this_copy_bridge_when_root_arg_is_other_desk():
  runtime = ROOT / "runtime" / "e21"
  mt5 = runtime / "mt5"
  if not mt5.is_dir():
    return
  local = next((p for p in mt5.iterdir() if p.is_dir() and p.name.startswith("bridge")), None)
  if local is None:
    return
  other_root = ROOT / "runtime" / "g23"
  got = relocate_under_root(str(local), root=other_root)
  assert got == local.resolve()


def test_relocate_maps_missing_stale_path(tmp_path):
  runtime = tmp_path / "runtime" / "e21"
  runtime.mkdir(parents=True)
  stale = tmp_path / "missing_clone" / "mt5" / "bridge_lc2_e21"
  got = relocate_under_root(str(stale), root=runtime)
  assert got == (runtime / "mt5" / "bridge_lc2_e21").resolve()


def test_relocate_keeps_path_already_under_root(tmp_path):
  runtime = tmp_path / "runtime" / "e21"
  local = runtime / "mt5" / "bridge_m15e21"
  local.mkdir(parents=True)
  got = relocate_under_root(str(local), root=runtime)
  assert got == local.resolve()


def test_get_root_ignores_stale_runtime_env(tmp_path, monkeypatch):
  monkeypatch.setenv("TRAINAPP_ROOT", str(ROOT))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  monkeypatch.setenv("TRAINAPP_RUNTIME", r"C:\OtherMachine\old\runtime\e21")
  assert get_root() == (ROOT / "runtime" / "e21").resolve()


def test_get_root_ignores_sibling_clone_trainapp_root(monkeypatch):
  monkeypatch.setenv("TRAINAPP_ROOT", str(ROOT.parent.parent / "M15" / "Train"))
  monkeypatch.setenv("TRAINAPP_DESK", "e21")
  monkeypatch.delenv("TRAINAPP_RUNTIME", raising=False)
  assert get_root() == (ROOT / "runtime" / "e21").resolve()


def test_get_core_root_ignores_stale_core_env(monkeypatch):
  monkeypatch.setenv("TRAINAPP_ROOT", str(ROOT))
  monkeypatch.setenv("TRAINAPP_CORE", r"D:\somewhere\else\cores\m15")
  assert get_core_root() == Path(__file__).resolve().parents[1]


def test_heal_rewrites_stale_json(tmp_path):
  import sys
  sys.path.insert(0, str(ROOT))
  from desk_context import heal_runtime_paths

  runtime = tmp_path / "e21"
  results = runtime / "results"
  results.mkdir(parents=True)
  cfg = results / "mt5_bridge_config.json"
  cfg.write_text(
    '{"bridge_dir": "C:\\\\Old\\\\Train\\\\mt5\\\\bridge_m15e21"}\n',
    encoding="utf-8",
  )
  n = heal_runtime_paths(runtime)
  assert n == 1
  text = cfg.read_text(encoding="utf-8")
  assert "bridge_m15e21" in text
  assert "C:\\\\Old" not in text
  assert "mt5/bridge_m15e21" in text.replace("\\\\", "/")


def test_heal_rewrites_existing_sibling_and_clone_bridge_leaf(tmp_path):
  import sys
  sys.path.insert(0, str(ROOT))
  from desk_context import heal_runtime_paths

  sibling = tmp_path / "M15" / "Train" / "runtime" / "e21" / "mt5" / "bridge_lc2_e21"
  sibling.mkdir(parents=True)
  runtime = tmp_path / "e21"
  results = runtime / "results"
  results.mkdir(parents=True)
  cfg = results / "mt5_bridge_config.json"
  cfg.write_text(
    json.dumps({"bridge_dir": str(sibling)}) + "\n",
    encoding="utf-8",
  )
  n = heal_runtime_paths(runtime, bridge_subdir="bridge_lc2_e21_check")
  assert n == 1
  text = cfg.read_text(encoding="utf-8").replace("\\\\", "/")
  assert "bridge_lc2_e21_check" in text
  assert str(sibling).replace("\\", "/") not in text


def test_bridge_dir_display_stale_windows_absolute(tmp_path, monkeypatch):
  import sys
  sys.path.insert(0, str(ROOT / "cores" / "m15"))
  from mt5_bridge.protocol import bridge_dir_display

  runtime = tmp_path / "runtime" / "e21"
  bridge = runtime / "mt5" / "bridge_m15e21"
  bridge.mkdir(parents=True)
  stale = r"C:\Work\ThuyenRepo\LiveCheck\TrainApp2\runtime\e21\mt5\bridge_m15e21"
  monkeypatch.setattr(
    "mt5_bridge.protocol.ROOT",
    runtime,
    raising=False,
  )
  assert bridge_dir_display(stale) == "mt5/bridge_m15e21"
  assert bridge_dir_display(f"mt5/{stale}") == "mt5/bridge_m15e21"
