"""Live OHLC seed uses EA bars.json, not Train, unless --allow-lab."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
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


def _write_bars(path: Path, n: int = 40) -> Path:
  path.parent.mkdir(parents=True, exist_ok=True)
  start = datetime(2026, 7, 6, 8, 45)
  bars = []
  for i in range(n):
    t = start + timedelta(minutes=15 * i)
    px = 1.14 + i * 0.00001
    bars.append({
      "time": t.strftime("%Y.%m.%d %H:%M"),
      "open": px,
      "high": px + 0.0002,
      "low": px - 0.0002,
      "close": px + 0.00005,
      "tick_volume": 100,
      "spread_points": 19,
    })
  path.write_text(json.dumps({"symbol": "EURUSD", "period": "M15", "bars": bars}), encoding="utf-8")
  return path


def test_train_runtime_candidates_prefer_g23(tmp_path, monkeypatch):
  monkeypatch.setattr(seed_mod, "FINAL", tmp_path)
  g23 = _fake_parquet(tmp_path / "Train" / "runtime" / "g23" / "data" / "mt5_gbpusd_m15.parquet")
  paths = seed_mod.train_runtime_candidates("GBPUSD", "M15")
  assert g23 in paths
  assert paths[0] == g23


def test_seed_does_not_copy_train_by_default(tmp_path, monkeypatch):
  monkeypatch.setattr(seed_mod, "RESULTS_DIR", tmp_path / "results")
  monkeypatch.setattr(seed_mod, "FINAL", tmp_path)
  _fake_parquet(tmp_path / "Train" / "runtime" / "g23" / "data" / "mt5_gbpusd_m15.parquet", size=4096)

  def _no_desk(symbol, timeframe):
    raise FileNotFoundError("no EdgeMiner desk")

  monkeypatch.setattr(seed_mod, "resolve_host_desk", _no_desk)
  monkeypatch.setattr(
    seed_mod,
    "live_bars_json_path",
    lambda symbol, timeframe: tmp_path / "missing" / "bars.json",
  )
  with pytest.raises(FileNotFoundError, match="bars.json"):
    seed_mod.seed("GBPUSD", "M15")
  assert not seed_mod.cache_path("GBPUSD", "M15").exists()


def test_allow_lab_copies_train(tmp_path, monkeypatch):
  monkeypatch.setattr(seed_mod, "RESULTS_DIR", tmp_path / "results")
  monkeypatch.setattr(seed_mod, "FINAL", tmp_path)

  def _no_desk(symbol, timeframe):
    raise FileNotFoundError("no EdgeMiner desk")

  monkeypatch.setattr(seed_mod, "resolve_host_desk", _no_desk)
  monkeypatch.setattr(
    seed_mod,
    "live_bars_json_path",
    lambda symbol, timeframe: tmp_path / "missing" / "bars.json",
  )
  src = _fake_parquet(
    tmp_path / "Train" / "runtime" / "g23" / "data" / "mt5_gbpusd_m15.parquet",
    size=4096,
  )
  info = seed_mod.seed("GBPUSD", "M15", allow_lab=True)
  dest = Path(info["dest"])
  assert dest.exists()
  assert info["source_kind"] == "lab"
  assert Path(info["source"]).resolve() == src.resolve()


def test_seed_from_live_bars_json(tmp_path, monkeypatch):
  monkeypatch.setattr(seed_mod, "RESULTS_DIR", tmp_path / "results")
  bars = _write_bars(tmp_path / "bridge" / "bars.json", n=48)
  monkeypatch.setattr(seed_mod, "live_bars_json_path", lambda symbol, timeframe: bars)
  info = seed_mod.seed("EURUSD", "M15")
  assert info["source_kind"] == "live_bars_json"
  dest = Path(info["dest"])
  df = pd.read_parquet(dest)
  assert len(df) == 48
  assert "SpreadPoints" in df.columns


def test_existing_live_cache_not_overwritten(tmp_path, monkeypatch):
  monkeypatch.setattr(seed_mod, "RESULTS_DIR", tmp_path / "results")
  dest = seed_mod.cache_path("EURUSD", "M15")
  _fake_parquet(dest, size=8192)
  bars = _write_bars(tmp_path / "bridge" / "bars.json")
  monkeypatch.setattr(seed_mod, "live_bars_json_path", lambda symbol, timeframe: bars)
  info = seed_mod.seed("EURUSD", "M15")
  assert info.get("reused") is True
  assert info["source_kind"] == "existing_live"
  assert dest.stat().st_size == 8192
