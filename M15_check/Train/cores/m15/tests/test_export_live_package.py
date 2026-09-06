"""TrainApp → Trade .tmpkg uses shared package_format (schedule required)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from gui.export_live_package import export_model_tmpkg, export_readiness, trade_app_root


def _desk(runtime: Path) -> dict:
  return {
    "id": "e21",
    "symbol": "EURUSD",
    "tf": "M15",
    "instance_id": "M15E21",
    "runtime_root": str(runtime),
    "train_weeks": 3,
    "spread_pips": 1.0,
    "slippage_pips": 0.3,
    "max_trades_per_day": 2,
  }


def _model(mid: str, *, use_kb: bool = True) -> dict:
  return {
    "id": mid,
    "label": "ExportTest",
    "mining_search_space": {"rr_ratios": [2.5], "selection_mode": "expectancy_frontier"},
    "train_weeks": 3,
    "use_kb": use_kb,
    "feature_profile": "current",
    "oos_from": "2026-01-01",
    "oos_to": "2026-08-01",
    "total_r": 10.0,
    "kb_pin_path": f"trade_models/{mid}_kb_pin.json",
  }


def _write_assets(runtime: Path, mid: str, *, schedule: bool = True, pin: bool = True) -> None:
  models = runtime / "results" / "trade_models"
  models.mkdir(parents=True)
  if pin:
    (models / f"{mid}_kb_pin.json").write_text('{"pinned": true}\n', encoding="utf-8")
  if schedule:
    payload = {
      "meta": {"model_id": mid, "n_weeks": 1},
      "weekly": [
        {
          "week_start": "2026-01-06",
          "strategy": {
            "name": "test genome",
            "rr_ratio": 2.5,
            "long_rules": [],
            "short_rules": [],
          },
        }
      ],
    }
    (models / f"{mid}_schedule.json").write_text(
      json.dumps(payload, indent=2), encoding="utf-8"
    )


def test_trade_package_format_is_present():
  root = trade_app_root()
  assert (root / "shared" / "package_format.py").is_file(), root


def test_export_tmpkg_roundtrip(tmp_path, monkeypatch):
  runtime = tmp_path / "runtime"
  mid = "tm_export_test_abcdef12"
  _write_assets(runtime, mid)
  monkeypatch.setattr("gui.export_live_package.load_desk", lambda: _desk(runtime))
  model = _model(mid)
  ready = export_readiness(model)
  assert ready["ok"], ready
  assert ready["weeks"] == 1

  out = tmp_path / "out"
  result = export_model_tmpkg(model, out_dir=out)
  path = result["path"]
  assert path.exists()
  assert path.suffix == ".tmpkg"
  assert result["weeks"] == 1

  trade = trade_app_root()
  if str(trade) not in sys.path:
    sys.path.insert(0, str(trade))
  from shared.package_format import extract_package, validate_package_dir

  dest = tmp_path / "extracted"
  extract_package(path, dest)
  assert validate_package_dir(dest) == []
  man = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
  assert man["symbol"] == "EURUSD"
  assert man["timeframe"] == "M15"
  assert man["lab"]["desk"] == "e21"
  assert (dest / "schedule.json").exists()
  assert (dest / "kb_pin.json").exists()


def test_export_fails_without_schedule(tmp_path, monkeypatch):
  runtime = tmp_path / "runtime"
  mid = "tm_export_nosched_11111111"
  _write_assets(runtime, mid, schedule=False)
  monkeypatch.setattr("gui.export_live_package.load_desk", lambda: _desk(runtime))
  model = _model(mid)
  ready = export_readiness(model)
  assert not ready["ok"]
  try:
    export_model_tmpkg(model, out_dir=tmp_path / "out")
  except RuntimeError as exc:
    assert "schedule" in str(exc).lower()
  else:
    raise AssertionError("expected RuntimeError for missing schedule")
