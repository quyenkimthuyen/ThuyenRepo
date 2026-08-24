"""Copied TrainApp2 folder must remap stale absolute paths."""
from __future__ import annotations

from pathlib import Path

from app_paths import get_core_root, get_root, relocate_under_root

ROOT = Path(__file__).resolve().parents[3]


def test_relocate_maps_old_train_bridge_into_this_runtime(tmp_path):
  runtime = tmp_path / "runtime" / "e31"
  runtime.mkdir(parents=True)
  stale = r"C:\Work\ThuyenRepo\LiveCheck\Train\M5\EdgeMinerEURUSDM5\mt5\bridge_m5e31"
  got = relocate_under_root(stale, root=runtime)
  assert got == (runtime / "mt5" / "bridge_m5e31").resolve()


def test_get_root_ignores_stale_runtime_env(monkeypatch):
  monkeypatch.setenv("TRAINAPP_ROOT", str(ROOT))
  monkeypatch.setenv("TRAINAPP_DESK", "e31")
  monkeypatch.setenv("TRAINAPP_RUNTIME", r"C:\OtherMachine\old\runtime\e31")
  assert get_root() == (ROOT / "runtime" / "e31").resolve()


def test_get_core_root_ignores_stale_core_env(monkeypatch):
  monkeypatch.setenv("TRAINAPP_ROOT", str(ROOT))
  monkeypatch.setenv("TRAINAPP_CORE", r"D:\somewhere\else\cores\m5")
  assert get_core_root() == Path(__file__).resolve().parents[1]
