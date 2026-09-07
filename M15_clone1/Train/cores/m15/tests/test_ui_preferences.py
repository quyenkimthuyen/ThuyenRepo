from __future__ import annotations

import json
import multiprocessing
from datetime import date
from types import SimpleNamespace

from gui import ui_preferences as prefs


def _write_preference_in_process(path: str, key: str) -> None:
  from pathlib import Path
  from gui import ui_preferences
  ui_preferences.PREFERENCES_PATH = Path(path)
  for value in range(10):
    ui_preferences.set_preference(key, value)


def test_preferences_round_trip_and_json_safe(tmp_path, monkeypatch):
  path = tmp_path / "ui_preferences.json"
  monkeypatch.setattr(prefs, "PREFERENCES_PATH", path)

  prefs.set_preference("chart.range", "7 ngày")
  prefs.set_preference("filter.date", date(2026, 7, 22))

  assert prefs.get_preference("chart.range") == "7 ngày"
  assert prefs.get_preference("filter.date") == "2026-07-22"
  assert not path.with_suffix(".json.tmp").exists()


def test_corrupt_preferences_fall_back_without_overwrite(tmp_path):
  path = tmp_path / "ui_preferences.json"
  path.write_text("{broken", encoding="utf-8")

  assert prefs.load_preferences(path) == {}
  assert path.read_text(encoding="utf-8") == "{broken"


def test_restore_widget_validates_dynamic_options(tmp_path, monkeypatch):
  path = tmp_path / "ui_preferences.json"
  path.write_text(json.dumps({"model": "deleted"}), encoding="utf-8")
  monkeypatch.setattr(prefs, "PREFERENCES_PATH", path)
  monkeypatch.setattr(prefs, "st", SimpleNamespace(session_state={}))

  value = prefs.restore_widget(
    "model_widget", "current",
    preference_key="model",
    options=["current", "other"],
  )

  assert value == "current"
  assert prefs.get_preference("model") == "current"


def test_restore_multiselect_drops_invalid_saved_values(tmp_path, monkeypatch):
  path = tmp_path / "ui_preferences.json"
  path.write_text(json.dumps({"eras": ["valid", "deleted"]}), encoding="utf-8")
  monkeypatch.setattr(prefs, "PREFERENCES_PATH", path)
  monkeypatch.setattr(prefs, "st", SimpleNamespace(session_state={}))

  value = prefs.restore_widget(
    "era_widget", ["valid"],
    preference_key="eras",
    options=["valid", "other"],
    multiple=True,
  )

  assert value == ["valid"]


def test_concurrent_process_writes_preserve_all_keys(tmp_path):
  path = tmp_path / "ui_preferences.json"
  ctx = multiprocessing.get_context("spawn")
  workers = [
    ctx.Process(target=_write_preference_in_process, args=(str(path), f"key_{i}"))
    for i in range(3)
  ]
  for worker in workers:
    worker.start()
  for worker in workers:
    worker.join(20)
    assert worker.exitcode == 0

  data = prefs.load_preferences(path)
  assert data == {"key_0": 9, "key_1": 9, "key_2": 9}
