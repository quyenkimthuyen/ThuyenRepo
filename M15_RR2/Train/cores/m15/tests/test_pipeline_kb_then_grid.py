"""Pipeline học KB → Grid must publish Grid Search job_state (not only latest.json)."""
from __future__ import annotations

import gui.grid_search_background as gsb
from gui.grid_search_engine import GridSpec


def _inline_state(**extra):
  state = {
    "status": "running",
    "runner": "inline",
    "run_id": "gs_pipe",
    "total": 6,
    "done": 2,
    "rows": [],
    "current_label": "combo 2",
  }
  state.update(extra)
  return state


def test_inline_pipeline_grid_counts_as_running(monkeypatch, tmp_path):
  monkeypatch.setattr(gsb, "JOB_STATE_PATH", tmp_path / "job_state.json")
  monkeypatch.setattr(gsb, "_thread", None)
  gsb._write_json(gsb.JOB_STATE_PATH, _inline_state())

  assert gsb.is_grid_running() is True
  status = gsb.get_grid_status()
  assert status["running"] is True
  assert status["status"] == "running"
  assert status["done"] == 2


def test_inline_without_thread_is_not_interrupted(monkeypatch, tmp_path):
  monkeypatch.setattr(gsb, "JOB_STATE_PATH", tmp_path / "job_state.json")
  monkeypatch.setattr(gsb, "_thread", None)
  gsb._write_json(gsb.JOB_STATE_PATH, _inline_state())

  status = gsb.get_grid_status()
  assert status["status"] != "interrupted"


def test_ensure_does_not_spawn_when_pipeline_owns_inline(monkeypatch, tmp_path):
  monkeypatch.setattr(gsb, "JOB_STATE_PATH", tmp_path / "job_state.json")
  monkeypatch.setattr(gsb, "_thread", None)
  gsb._write_json(gsb.JOB_STATE_PATH, _inline_state())
  monkeypatch.setattr(
    "gui.long_task_background.is_task_running", lambda: True,
  )
  monkeypatch.setattr(
    "gui.long_task_background.load_job_state",
    lambda: {"job_type": "kb_then_grid", "status": "running"},
  )

  gsb.ensure_grid_worker_running()
  assert gsb._thread is None
  assert (gsb.load_job_state() or {}).get("status") == "running"


def test_ensure_clears_stale_inline_after_restart(monkeypatch, tmp_path):
  monkeypatch.setattr(gsb, "JOB_STATE_PATH", tmp_path / "job_state.json")
  monkeypatch.setattr(gsb, "_thread", None)
  gsb._write_json(gsb.JOB_STATE_PATH, _inline_state())
  monkeypatch.setattr(
    "gui.long_task_background.is_task_running", lambda: False,
  )
  monkeypatch.setattr(
    "gui.long_task_background.load_job_state",
    lambda: {"job_type": "kb_then_grid", "status": "interrupted"},
  )

  gsb.ensure_grid_worker_running()
  state = gsb.load_job_state() or {}
  assert state.get("status") == "interrupted"
  assert state.get("runner") is None


def test_kb_then_grid_worker_publishes_grid_job_state(monkeypatch, tmp_path):
  monkeypatch.setattr(gsb, "JOB_STATE_PATH", tmp_path / "job_state.json")
  monkeypatch.setattr(gsb, "_thread", None)
  monkeypatch.setattr(gsb, "RUNS_DIR", tmp_path)

  spec = GridSpec(
    train_weeks=8,
    use_kb=True,
    kb_profile="era_2025_h1",
    kb_snapshot=1,
    oos_from="2026-01-01",
    oos_to="2026-06-30",
    mining_preset="eur_fill_ss_more",
  )
  row = {
    "key": spec.key(),
    "label": spec.label(),
    "total_r": 1.5,
    "win_rate_pct": 40.0,
    "error": None,
  }

  monkeypatch.setattr(
    "gui.app_settings.get_settings",
    lambda: {
      "learning_loops": 3,
      "grid_objective": "quality",
      "learning_era_keys": ["2025-h1"],
    },
  )
  monkeypatch.setattr(
    "gui.app_settings.resolve_learning_eras",
    lambda _s=None: [{
      "kb_profile": "era_2025_h1",
      "label": "2025 H1",
      "learn_from": "2025-01-01",
      "learn_until": "2025-06-30",
    }],
  )
  monkeypatch.setattr(
    "gui.app_settings.settings_grid_signature", lambda _s=None: "sig",
  )
  monkeypatch.setattr(
    "gui.grid_search_engine.expected_grid_count_from_settings", lambda _s=None: 1,
  )
  monkeypatch.setattr(
    "gui.grid_search_engine.build_grid_from_settings",
    lambda _s=None: ([spec], {"train_weeks": [8]}),
  )
  monkeypatch.setattr(
    "gui.era_compare.ensure_profile_learned",
    lambda *_a, **_k: {"skipped": False},
  )
  monkeypatch.setattr(
    "gui.grid_search_engine.run_grid",
    lambda specs, **_k: [row],
  )
  saved = {}

  def fake_save(rows, *, config, objective, run_id=None):
    saved["run_id"] = run_id or "gs_saved"
    saved["rows"] = rows
    saved["config"] = config
    return saved["run_id"]

  monkeypatch.setattr("gui.grid_search_engine.save_grid_run", fake_save)
  monkeypatch.setattr(gsb, "is_grid_running", lambda: False)

  from gui.long_task_background import JobCancelled, _worker_kb_then_grid

  monkeypatch.setattr(
    "gui.long_task_background._check_cancel", lambda: None,
  )
  monkeypatch.setattr(
    "gui.long_task_background._update_progress", lambda *_a, **_k: None,
  )
  finished = {}

  def fake_finish(state, *, status, result=None, error=None):
    finished["status"] = status
    finished["result"] = result
    finished["error"] = error
    state["status"] = status

  monkeypatch.setattr("gui.long_task_background._finish", fake_finish)

  state = {
    "status": "running",
    "job_type": "kb_then_grid",
    "params": {"reset_kb": True, "objective": "quality"},
    "done": 0,
    "total": 2,
  }
  _worker_kb_then_grid(state)

  assert finished.get("status") == "completed"
  assert finished["result"]["n_combos"] == 1
  grid_job = gsb.load_job_state() or {}
  assert grid_job.get("status") == "completed"
  assert grid_job.get("run_id")
  assert grid_job.get("runner") is None
  assert saved.get("rows") == [row]
  assert saved.get("config", {}).get("source") == "kb_then_grid"
