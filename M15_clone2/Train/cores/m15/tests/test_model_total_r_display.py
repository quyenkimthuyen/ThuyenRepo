"""Canonical Total R resolution for Trade Model banners."""
from __future__ import annotations

from gui.trade_model import format_model_total_r_text, resolve_model_total_r


def test_resolve_prefers_model_oos_report_over_grid():
  m = {
    "id": "tm_x",
    "total_r": 125.071,
    "oos_from": "2026-04-01",
    "oos_to": "2026-12-31",
  }
  report = {"overall_oos": {"total_r": 69.406}, "oos_start": "2026-04-01", "config": {}}
  resolved = resolve_model_total_r(m, report=report, load_report=False)
  assert resolved["source"] == "oos"
  assert resolved["value"] == 69.406
  assert "OOS" in format_model_total_r_text(resolved)


def test_resolve_falls_back_to_grid_when_no_report():
  m = {
    "id": "tm_x",
    "total_r": 125.071,
    "oos_from": "2026-04-01",
    "oos_to": "2026-12-31",
  }
  resolved = resolve_model_total_r(m, report=None, load_report=False)
  assert resolved["source"] == "grid"
  assert resolved["value"] == 125.071
  assert "Grid" in format_model_total_r_text(resolved)


def test_resolve_empty_model():
  assert resolve_model_total_r(None)["value"] is None
  assert resolve_model_total_r({})["value"] is None
