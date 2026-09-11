"""BUG-08: concurrent imports must not share a single _staging directory."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))


def _make_tmpkg(path: Path, *, model_id: str, symbol: str = "EURUSD") -> Path:
  staging = path.parent / f"_pkg_{model_id}"
  staging.mkdir(parents=True, exist_ok=True)
  manifest = {
    "format": "edgeminer.trade_model_package",
    "package_version": 1,
    "version": 1,
    "model_id": model_id,
    "symbol": symbol,
    "timeframe": "M15",
    "label": model_id,
    "files": ["manifest.json", "model.json", "schedule.json", "metrics.json"],
  }
  model = {
    "id": model_id,
    "label": model_id,
    "symbol": symbol,
    "timeframe": "M15",
    "mining_search_space": {"space": "grid"},
    "train_weeks": 6,
    "feature_profile": "current",
    "use_kb": False,
  }
  schedule = {
    "meta": {"model_id": model_id},
    "weekly": [{"week_start": "2026-01-05", "strategy": {"name": "s", "rules": []}}],
  }
  (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
  (staging / "model.json").write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
  (staging / "schedule.json").write_text(json.dumps(schedule, indent=2) + "\n", encoding="utf-8")
  (staging / "metrics.json").write_text("{}\n", encoding="utf-8")
  from shared.package_format import _sha256_file
  lines = []
  for name in manifest["files"]:
    fp = staging / name
    if fp.exists():
      lines.append(f"{_sha256_file(fp)}  {name}")
  (staging / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
  with zipfile.ZipFile(path, "w") as zf:
    for p in staging.iterdir():
      zf.write(p, arcname=p.name)
  return path


def test_import_uses_unique_staging_not_shared_folder(tmp_path, monkeypatch):
  import import_trade_package as imp

  installed = tmp_path / "installed_models"
  installed.mkdir()
  monkeypatch.setattr(imp, "INSTALLED_DIR", installed)

  pkg = _make_tmpkg(tmp_path / "a.tmpkg", model_id="tm_a")
  # Spy: import_one must not use a fixed "_staging" path that another import can rmtree
  seen: list[Path] = []
  real_extract = imp.extract_package

  def _wrap(tmpkg, dest_dir):
    seen.append(Path(dest_dir))
    assert Path(dest_dir).name != "_staging", "shared _staging is racy"
    assert "_staging_" in Path(dest_dir).name or Path(dest_dir).name.startswith(".staging")
    return real_extract(tmpkg, dest_dir)

  monkeypatch.setattr(imp, "extract_package", _wrap)
  dest = imp.import_one(pkg)
  assert dest.exists()
  assert seen, "extract_package was not called"
  assert not (installed / "_staging").exists()
