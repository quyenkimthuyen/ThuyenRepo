"""BUG-02: paper_fill._desk_symbol must recognize M5G* (G33) as GBPUSD."""
from __future__ import annotations

from pathlib import Path

import config
import mt5_bridge.protocol as protocol
from mt5_bridge import paper_fill


def test_desk_symbol_m5g33_is_gbpusd(monkeypatch):
  """INSTANCE_ID=M5G33 + runtime name g33 (no 'GBP') must still be GBPUSD."""
  monkeypatch.setattr(config, "DEFAULT_PAIR", "")
  monkeypatch.setattr(protocol, "INSTANCE_ID", "M5G33")
  monkeypatch.setattr(protocol, "ROOT", Path("/tmp/runtime/g33"))
  assert paper_fill._desk_symbol() == "GBPUSD"


def test_desk_symbol_m15g23_is_gbpusd(monkeypatch):
  monkeypatch.setattr(config, "DEFAULT_PAIR", "")
  monkeypatch.setattr(protocol, "INSTANCE_ID", "M15G23")
  monkeypatch.setattr(protocol, "ROOT", Path("/tmp/runtime/g23"))
  assert paper_fill._desk_symbol() == "GBPUSD"


def test_desk_symbol_m5e31_is_eurusd(monkeypatch):
  monkeypatch.setattr(config, "DEFAULT_PAIR", "")
  monkeypatch.setattr(protocol, "INSTANCE_ID", "M5E31")
  monkeypatch.setattr(protocol, "ROOT", Path("/tmp/runtime/e31"))
  assert paper_fill._desk_symbol() == "EURUSD"


def test_desk_symbol_prefers_config_pair(monkeypatch):
  monkeypatch.setattr(config, "DEFAULT_PAIR", "GBP/USD")
  monkeypatch.setattr(protocol, "INSTANCE_ID", "M5E31")
  monkeypatch.setattr(protocol, "ROOT", Path("/tmp/runtime/e31"))
  assert paper_fill._desk_symbol() == "GBPUSD"


def test_journal_symbol_falls_back_to_desk(monkeypatch):
  """BUG-13: missing fill.symbol must not hardcode EURUSD on GBP desk."""
  monkeypatch.setattr(config, "DEFAULT_PAIR", "GBP/USD")
  assert paper_fill.journal_symbol({}) == "GBPUSD"
  assert paper_fill.journal_symbol({"symbol": "EURUSD"}) == "EURUSD"
