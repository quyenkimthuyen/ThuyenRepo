"""BUG-09/10: canonical MT5 data must be mt5_ea and pair must match desk."""
from __future__ import annotations

import pytest

import config
import data_loader


def _ok_meta(**overrides):
  meta = {
    "source": "mt5_ea",
    "timeframe": getattr(config, "DEFAULT_TF", "M5"),
    "pair": str(getattr(config, "DEFAULT_PAIR", "EUR/USD")).upper().replace("/", ""),
    "broker": "XM",
    "fingerprint": "abc",
    "bars": 10,
    "start": "2025-01-01",
    "end": "2025-02-01",
  }
  meta.update(overrides)
  return meta


def test_require_canonical_rejects_mt5_api(tmp_path, monkeypatch):
  meta_path = tmp_path / "meta.json"
  monkeypatch.setattr(data_loader, "META_PATH", meta_path)
  from mt5_bridge.protocol import atomic_write_json

  atomic_write_json(meta_path, _ok_meta(source="mt5_api"))
  with pytest.raises(RuntimeError, match="chưa được xác nhận"):
    data_loader.require_canonical_mt5_data()


def test_require_canonical_rejects_wrong_pair(tmp_path, monkeypatch):
  meta_path = tmp_path / "meta.json"
  monkeypatch.setattr(data_loader, "META_PATH", meta_path)
  monkeypatch.setattr(config, "DEFAULT_PAIR", "GBP/USD")
  from mt5_bridge.protocol import atomic_write_json

  atomic_write_json(meta_path, _ok_meta(pair="EURUSD"))
  with pytest.raises(RuntimeError, match="pair lệch"):
    data_loader.require_canonical_mt5_data()


def test_require_canonical_accepts_matching_pair(tmp_path, monkeypatch):
  meta_path = tmp_path / "meta.json"
  monkeypatch.setattr(data_loader, "META_PATH", meta_path)
  monkeypatch.setattr(config, "DEFAULT_PAIR", "GBP/USD")
  from mt5_bridge.protocol import atomic_write_json

  atomic_write_json(meta_path, _ok_meta(pair="GBPUSD"))
  meta = data_loader.require_canonical_mt5_data()
  assert meta["pair"] == "GBPUSD"
