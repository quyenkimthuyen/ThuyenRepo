"""Materialize installed packages → live/results trade_models store for BridgeEngine."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from live_config import INSTALLED_DIR, RESULTS_DIR
from package_store import load_roster
from runtime_host import normalize_symbol, normalize_timeframe


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def enabled_roster_rows(roster: dict | None = None) -> list[dict]:
  data = roster or load_roster()
  rows = [r for r in (data.get("models") or []) if r.get("enabled") and r.get("install_id")]
  return rows


def assert_homogeneous_roster(rows: list[dict]) -> tuple[str, str]:
  """Live v1: one chart / one EA → all enabled models same symbol+TF."""
  if not rows:
    raise ValueError("No enabled models in roster")
  symbols = {normalize_symbol(r.get("symbol")) for r in rows}
  tfs = {normalize_timeframe(r.get("timeframe")) for r in rows}
  if len(symbols) != 1 or len(tfs) != 1:
    raise ValueError(
      f"Enabled roster must share one symbol+TF (got symbols={sorted(symbols)} tfs={sorted(tfs)}). "
      "Attach separate charts/EAs for mixed books."
    )
  return next(iter(symbols)), next(iter(tfs))


def _enrich_model(model: dict, manifest: dict) -> dict:
  m = dict(model)
  tf = normalize_timeframe(manifest.get("timeframe") or m.get("timeframe") or "M5")
  sym = normalize_symbol(manifest.get("symbol") or m.get("symbol") or "EURUSD")
  m["id"] = m.get("id") or manifest.get("model_id")
  m["label"] = m.get("label") or manifest.get("label") or m["id"]
  m["symbol"] = sym
  m["timeframe"] = tf
  m["data_source"] = m.get("data_source") or "mt5_ea"
  m["data_timeframe"] = tf
  schema = int(m.get("feature_schema") or 0)
  if schema < 3:
    m["feature_schema"] = 3
  if not m.get("feature_profile"):
    m["feature_profile"] = (
      manifest.get("feature_profile")
      or ("m5_parity" if tf == "M5" else "current")
    )
  return m


def materialize_enabled(*, roster: dict | None = None) -> dict[str, Any]:
  """Copy package models + kb_pin (+ schedule) into live/results for BridgeEngine.

  Returns summary: {symbol, timeframe, model_ids, models_path, host_key}.
  """
  rows = enabled_roster_rows(roster)
  symbol, timeframe = assert_homogeneous_roster(rows)

  models_dir = RESULTS_DIR / "trade_models"
  models_dir.mkdir(parents=True, exist_ok=True)
  models: list[dict] = []
  labels: dict[str, str] = {}
  risk_by_id: dict[str, float] = {}

  for row in rows:
    install_id = row["install_id"]
    pkg = INSTALLED_DIR / install_id
    if not pkg.is_dir():
      raise FileNotFoundError(f"Installed package missing: {pkg}")
    manifest = _read(pkg / "manifest.json") or {}
    model = _read(pkg / "model.json")
    if not model:
      raise ValueError(f"{install_id}: missing model.json")
    m = _enrich_model(model, manifest)
    mid = str(m["id"])
    if row.get("model_id") and str(row["model_id"]) != mid:
      # Prefer roster model_id if set (should match)
      m["id"] = str(row["model_id"])
      mid = m["id"]

    if m.get("use_kb", True):
      src_pin = pkg / "kb_pin.json"
      if not src_pin.exists():
        raise ValueError(f"{install_id}: use_kb but kb_pin.json missing")
      dest_pin = models_dir / f"{mid}_kb_pin.json"
      shutil.copy2(src_pin, dest_pin)
      m["kb_pin_path"] = f"trade_models/{mid}_kb_pin.json"
      if manifest.get("kb_fingerprint"):
        m["kb_fingerprint"] = manifest["kb_fingerprint"]

    sched_src = pkg / "schedule.json"
    if sched_src.exists():
      shutil.copy2(sched_src, models_dir / f"{mid}_schedule.json")

    models.append(m)
    labels[mid] = str(m.get("label") or mid)
    risk_by_id[mid] = float(row.get("risk_pct") or 1.0)

  store_path = RESULTS_DIR / "trade_models.json"
  _write(store_path, {"models": models, "updated_from": "live_materialize"})
  if models:
    _write(RESULTS_DIR / "active_trade_model.json", {"id": models[0]["id"]})

  return {
    "symbol": symbol,
    "timeframe": timeframe,
    "model_ids": [m["id"] for m in models],
    "labels": labels,
    "risk_by_id": risk_by_id,
    "models_path": str(store_path),
    "n": len(models),
  }
