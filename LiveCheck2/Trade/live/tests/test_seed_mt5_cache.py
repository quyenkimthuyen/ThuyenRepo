"""OHLC seed must find LiveCheck2 Train runtime parquet (g23/e21)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))

_SPEC = importlib.util.spec_from_file_location(
  "seed_mt5_cache", LIVE / "scripts" / "seed_mt5_cache.py",
)
assert _SPEC and _SPEC.loader
seed_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(seed_mod)


def _fake_parquet(path: Path, size: int = 2048) -> Path:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_bytes(b"PAR1" + b"\x00" * (size - 8) + b"PAR1")
  return path


def test_train_runtime_candidates_prefer_g23(tmp_path, monkeypatch):
  monkeypatch.setattr(seed_mod, "FINAL", tmp_path)
  g23 = _fake_parquet(tmp_path / "Train" / "runtime" / "g23" / "data" / "mt5_gbpusd_m15.parquet")
  paths = seed_mod.train_runtime_candidates("GBPUSD", "M15")
  assert g23 in paths
  assert paths[0] == g23


def test_find_source_uses_train_runtime_when_host_desk_has_no_data(tmp_path, monkeypatch):
  monkeypatch.setattr(seed_mod, "FINAL", tmp_path)

  def _no_desk(symbol, timeframe):
    raise FileNotFoundError("no EdgeMiner desk")

  monkeypatch.setattr(seed_mod, "resolve_host_desk", _no_desk)
  src = _fake_parquet(
    tmp_path / "Train" / "runtime" / "g23" / "data" / "mt5_gbpusd_m15.parquet",
    size=4096,
  )
  found = seed_mod.find_source("GBPUSD", "M15")
  assert found.resolve() == src.resolve()


def test_find_source_gbpusd_m15_from_livecheck2_train():
  src = Path(r"C:\Work\ThuyenRepo\LiveCheck2\Train\runtime\g23\data\mt5_gbpusd_m15.parquet")
  if not src.exists():
    pytest.skip("Train g23 parquet not present")
  found = seed_mod.find_source("GBPUSD", "M15")
  assert seed_mod._looks_like_parquet(found)
  assert "gbpusd" in found.name.lower()
