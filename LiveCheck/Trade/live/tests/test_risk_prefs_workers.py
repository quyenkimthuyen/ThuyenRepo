"""Risk-tab disable/clear must unlatch per-book worker configs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
if str(LIVE) not in sys.path:
  sys.path.insert(0, str(LIVE))

import risk_prefs as rp  # noqa: E402


def _write(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_disable_guard_clears_book_trip(tmp_path, monkeypatch):
  monkeypatch.setattr(rp, "RESULTS_DIR", tmp_path)
  monkeypatch.setattr(rp, "PREFS_PATH", tmp_path / "risk_prefs.json")
  worker = tmp_path / "mt5_bridge_worker_gbpusd_m15.json"
  _write(
    worker,
    {
      "enabled": True,
      "service_pid": 1,
      "loss_guard_enabled": True,
      "loss_guard_max_day": 3,
      "loss_guard_tripped": True,
      "loss_guard_tripped_reason": "3 losses",
    },
  )
  rp.save_risk_prefs(loss_guard_enabled=False, loss_guard_max_day=16)
  data = json.loads(worker.read_text(encoding="utf-8"))
  assert data["loss_guard_enabled"] is False
  assert data["loss_guard_tripped"] is False
  assert data["loss_guard_tripped_reason"] is None
  assert data["service_pid"] == 1
  assert data["loss_guard_max_day"] == 16


def test_clear_trip_updates_worker(tmp_path, monkeypatch):
  monkeypatch.setattr(rp, "RESULTS_DIR", tmp_path)
  worker = tmp_path / "mt5_bridge_worker_gbpusd_m15.json"
  _write(worker, {"loss_guard_tripped": True, "loss_guard_tripped_reason": "x"})
  touched = rp.apply_loss_guard_to_workers(clear_trip=True)
  assert touched == ["mt5_bridge_worker_gbpusd_m15.json"]
  data = json.loads(worker.read_text(encoding="utf-8"))
  assert data["loss_guard_tripped"] is False
