"""BUG-09: risk_status_snapshot must read DD / day R from Live journals."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVE))

import risk_prefs as rp  # noqa: E402


def _write_trades(path: Path, rows: list[dict]) -> None:
  path.mkdir(parents=True, exist_ok=True)
  (path / "trades.json").write_text(
    json.dumps({"trades": rows}, indent=2) + "\n", encoding="utf-8",
  )


def test_risk_snapshot_aggregates_worst_dd_across_books(monkeypatch, tmp_path):
  monkeypatch.setattr(rp, "load_risk_prefs", lambda: {
    "loss_guard_enabled": True,
    "loss_guard_max_day": 0,
    "loss_guard_max_week": 0,
    "loss_guard_max_day_dd_r": 6.0,
    "loss_guard_max_week_dd_r": 10.0,
    "loss_guard_max_day_loss_r": 0.0,
    "loss_guard_max_week_loss_r": 0.0,
  })
  monkeypatch.setattr(rp, "any_worker_loss_guard_trip", lambda: {"tripped": False})
  monkeypatch.setattr(rp, "_halted_models_from_workers", lambda: [])

  import bridge_control
  monkeypatch.setattr(bridge_control, "load_config", lambda: {"loss_guard_tripped": False})

  day = datetime.now().astimezone().strftime("%Y-%m-%d")
  eurusd = tmp_path / "bridge_live_eurusd_m15"
  gbpusd = tmp_path / "bridge_live_gbpusd_m15"
  _write_trades(eurusd, [{
    "status": "CLOSED",
    "mode": "auto",
    "model_id": "tm_eur",
    "r": 1.0,
    "result": "WIN",
    "exit_time": f"{day}T10:00:00",
  }])
  _write_trades(gbpusd, [
    {
      "status": "CLOSED",
      "mode": "auto",
      "model_id": "tm_gbp",
      "r": -4.0,
      "result": "LOSS",
      "exit_time": f"{day}T10:00:00",
    },
    {
      "status": "CLOSED",
      "mode": "auto",
      "model_id": "tm_gbp",
      "r": -4.0,
      "result": "LOSS",
      "exit_time": f"{day}T10:05:00",
    },
  ])
  monkeypatch.setattr(rp, "_risk_bridge_dirs", lambda: [eurusd, gbpusd])

  snap = rp.risk_status_snapshot()
  assert snap.get("status_error") is None
  assert snap["books_scanned"] == 2
  assert snap["day_dd_r"] == 8.0
  assert snap["week_dd_r"] == 8.0
  assert snap["day_total_r"] == -8.0
  assert snap["desk_day_total_r"] == -7.0
  assert snap["worst_dd_model"] == "tm_gbp"
