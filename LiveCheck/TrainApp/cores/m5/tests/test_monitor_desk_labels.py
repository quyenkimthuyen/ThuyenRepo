"""R-06: monitor chart titles/labels must follow desk symbol + TF."""
from __future__ import annotations

import config
from mt5_bridge import live_monitor_server


def test_desk_chart_label_uses_config(monkeypatch):
  monkeypatch.setattr(config, "DEFAULT_PAIR", "GBP/USD")
  monkeypatch.setattr(config, "DEFAULT_TF", "M5")
  sym, tf = live_monitor_server._desk_chart_label()
  assert sym == "GBPUSD"
  assert tf == "M5"


def test_chart_html_title_includes_desk_symbol(monkeypatch):
  monkeypatch.setattr(config, "DEFAULT_PAIR", "GBP/USD")
  monkeypatch.setattr(config, "DEFAULT_TF", "M5")
  html = live_monitor_server._chart_html(100, mode="mt5")
  assert "GBPUSD M5 · XM MT5 live" in html
  assert "EURUSD M5 · XM MT5 live" not in html
  html_cmp = live_monitor_server._chart_html(100, mode="compare")
  assert "GBPUSD M5 · Compare Trade" in html_cmp
