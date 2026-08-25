"""Grid history selector helpers."""
from __future__ import annotations

from gui.views.grid_search import (
  _extract_grid_run_id,
  _resolve_best_row,
  _rows_for_display,
  _sort_rows_for_objective,
)


def test_extract_grid_run_id_from_label_and_raw():
  assert _extract_grid_run_id("__latest__") == "__latest__"
  assert _extract_grid_run_id("gs_20260801_125447") == "gs_20260801_125447"
  assert (
    _extract_grid_run_id(
      "2026-08-01 12:54:47 · `gs_20260801_125447` · 36 combo · best +208.9R"
    )
    == "gs_20260801_125447"
  )
  assert _extract_grid_run_id("") is None


def test_rows_for_display_prefers_history_payload(monkeypatch):
  history = {
    "run_id": "gs_hist",
    "objective": "total_r",
    "rows": [{"key": "a", "total_r": 1.0, "label": "hist"}],
  }
  latest = {
    "run_id": "gs_latest",
    "objective": "total_r",
    "rows": [{"key": "b", "total_r": 9.0, "label": "latest"}],
  }
  monkeypatch.setattr(
    "gui.views.grid_search.load_latest_grid_run", lambda: latest,
  )
  monkeypatch.setattr(
    "gui.views.grid_search.load_job_state", lambda: {"rows": latest["rows"]},
  )
  monkeypatch.setattr(
    "gui.views.grid_search.get_settings",
    lambda: {"grid_objective": "total_r"},
  )
  rows, _obj, src = _rows_for_display(
    {"running": False}, history_run=history,
  )
  assert src is history
  assert rows[0]["label"] == "hist"


def test_rows_for_display_force_latest_ignores_job_rows(monkeypatch):
  latest = {
    "run_id": "gs_latest",
    "objective": "total_r",
    "rows": [{"key": "b", "total_r": 9.0, "label": "latest"}],
  }
  monkeypatch.setattr(
    "gui.views.grid_search.load_latest_grid_run", lambda: latest,
  )
  monkeypatch.setattr(
    "gui.views.grid_search.load_job_state",
    lambda: {
      "rows": [{"key": "job", "total_r": 3.0, "label": "job"}],
      "config": {},
    },
  )
  monkeypatch.setattr(
    "gui.views.grid_search.get_settings",
    lambda: {"grid_objective": "total_r"},
  )
  rows, _obj, src = _rows_for_display(
    {"running": False}, force_latest=True,
  )
  assert src is latest
  assert rows[0]["label"] == "latest"


def test_resolve_best_uses_stored_key_from_same_run():
  rows = [
    {"key": "a", "total_r": 10.0, "win_rate_pct": 40, "train_weeks": 3},
    {"key": "b", "total_r": 50.0, "win_rate_pct": 47.67, "train_weeks": 6},
  ]
  data = {"run_id": "gs_x", "best": dict(rows[1]), "objective": "total_r"}
  best = _resolve_best_row(data, rows, "total_r")
  assert best["key"] == "b"
  assert best["total_r"] == 50.0


def test_sort_rows_for_objective_risk_adjusted():
  rows = [
    {
      "key": "hi_r", "total_r": 200.0, "max_drawdown_r": 40.0,
      "trades_per_week": 8.0, "error": None,
    },
    {
      "key": "safe", "total_r": 100.0, "max_drawdown_r": 5.0,
      "trades_per_week": 8.0, "error": None,
    },
  ]
  ordered = _sort_rows_for_objective(rows, "risk_adjusted")
  assert ordered[0]["key"] == "safe"
