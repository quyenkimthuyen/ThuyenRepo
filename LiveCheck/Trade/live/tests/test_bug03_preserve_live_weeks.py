"""BUG-03: materialize must not delete weekend pre-remine live_weeks."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))


def test_reset_keeps_live_weeks_by_default(tmp_path, monkeypatch):
  import reset_data as rd

  monkeypatch.setattr(rd, "RESULTS_DIR", tmp_path)
  monkeypatch.setattr(rd, "MT5_ROOT", tmp_path / "mt5")
  monkeypatch.setattr(rd, "BRIDGE_DIR", tmp_path / "mt5" / "bridge_live")
  monkeypatch.setattr(rd, "BRIDGE_SIM_DIR", tmp_path / "mt5" / "bridge_sim")
  (tmp_path / "mt5").mkdir()
  tm = tmp_path / "trade_models"
  tm.mkdir()
  weeks = tm / "tm_x_live_weeks.json"
  weeks.write_text(json.dumps({"weekly": [{"week_start": "2026-08-17"}]}), encoding="utf-8")
  (tm / "tm_x_schedule.json").write_text("{}", encoding="utf-8")

  out = rd.reset_live_data(
    stop_services=False,
    journal=False,
    sim_parity=False,
    runtime=True,
    ohlc_cache=False,
    include_packages=False,
    reseed_ohlc=False,
    disarm_kill=False,
  )
  assert weeks.exists(), "frozen remine must survive Reset"
  assert "tm_x_live_weeks.json" in (out.get("live_weeks_kept") or [])
  assert not (tm / "tm_x_schedule.json").exists()

  out2 = rd.reset_live_data(
    stop_services=False,
    journal=False,
    sim_parity=False,
    runtime=True,
    ohlc_cache=False,
    include_packages=False,
    reseed_ohlc=False,
    disarm_kill=False,
    keep_live_weeks=False,
  )
  assert not weeks.exists()
  assert out2.get("live_weeks_kept") == []


def test_materialize_preserves_existing_live_weeks(tmp_path, monkeypatch):
  import materialize_models as mm

  models_dir = tmp_path / "trade_models"
  models_dir.mkdir()
  installed = tmp_path / "installed"
  pkg = installed / "inst_a"
  pkg.mkdir(parents=True)
  mid = "tm_keep_weeks"

  (pkg / "manifest.json").write_text(json.dumps({
    "model_id": mid, "symbol": "EURUSD", "timeframe": "M15", "label": "A",
  }) + "\n", encoding="utf-8")
  (pkg / "model.json").write_text(json.dumps({
    "id": mid, "symbol": "EURUSD", "timeframe": "M15", "use_kb": False,
  }) + "\n", encoding="utf-8")
  (pkg / "schedule.json").write_text(json.dumps({
    "meta": {"model_id": mid},
    "weekly": [{"week_start": "2026-01-05", "strategy": {"name": "x", "rules": []}}],
  }) + "\n", encoding="utf-8")

  live_weeks = models_dir / f"{mid}_live_weeks.json"
  live_weeks.write_text(json.dumps({
    "meta": {"model_id": mid, "source": "weekend_preremine"},
    "weekly": [{"week_start": "2026-08-17", "strategy": {"name": "frozen", "rules": []}}],
  }) + "\n", encoding="utf-8")

  monkeypatch.setattr(mm, "RESULTS_DIR", tmp_path)
  monkeypatch.setattr(mm, "INSTALLED_DIR", installed)

  # Avoid shared.package_format hard validation dependency differences
  with patch("shared.package_format.validate_schedule_payload", return_value=[]):
    rows = [{
      "install_id": "inst_a",
      "model_id": mid,
      "enabled": True,
      "risk_pct": 1.0,
      "symbol": "EURUSD",
      "timeframe": "M15",
    }]
    mm._materialize_rows(rows)

  assert live_weeks.exists(), "weekend pre-remine live_weeks must survive materialize"
  data = json.loads(live_weeks.read_text(encoding="utf-8"))
  assert data["weekly"][0]["week_start"] == "2026-08-17"
