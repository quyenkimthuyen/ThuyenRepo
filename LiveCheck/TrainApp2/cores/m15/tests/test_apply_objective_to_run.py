"""Re-rank existing Grid runs when objective changes."""
from __future__ import annotations

from gui.grid_search_engine import apply_objective_to_run


def test_apply_objective_reorders_and_updates_best():
  payload = {
    "run_id": "gs_test_obj",
    "objective": "total_r",
    "rows": [
      {
        "key": "a",
        "label": "high_r",
        "total_r": 100.0,
        "win_rate_pct": 40.0,
        "profit_factor": 1.2,
        "max_drawdown_r": 20.0,
        "n_trades": 50,
      },
      {
        "key": "b",
        "label": "high_wr",
        "total_r": 50.0,
        "win_rate_pct": 80.0,
        "profit_factor": 1.1,
        "max_drawdown_r": 5.0,
        "n_trades": 40,
      },
    ],
  }
  out = apply_objective_to_run(payload, "win_rate_pct", persist=False)
  assert out is not None
  assert out["objective"] == "win_rate_pct"
  assert out["best"]["key"] == "b"
  assert out["rows"][0]["key"] == "b"
  assert out["rows"][1]["key"] == "a"


def test_apply_objective_keeps_errors_last():
  payload = {
    "run_id": "gs_err",
    "objective": "total_r",
    "rows": [
      {"key": "ok", "total_r": 1.0, "win_rate_pct": 50.0, "profit_factor": 1.0, "max_drawdown_r": 1.0},
      {"key": "bad", "error": "boom"},
    ],
  }
  out = apply_objective_to_run(payload, "total_r", persist=False)
  assert out["rows"][-1]["key"] == "bad"
  assert out["best"]["key"] == "ok"
