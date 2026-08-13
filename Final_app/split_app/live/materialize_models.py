"""Materialize installed packages → live/results trade_models store for BridgeEngine."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from books import group_models_by_book
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
  return [r for r in (data.get("models") or []) if r.get("enabled") and r.get("install_id")]


def assert_homogeneous_roster(rows: list[dict]) -> tuple[str, str]:
  """Assert one symbol+TF (used for a single worker / chart)."""
  if not rows:
    raise ValueError("No enabled models")
  symbols = {normalize_symbol(r.get("symbol")) for r in rows}
  tfs = {normalize_timeframe(r.get("timeframe")) for r in rows}
  if len(symbols) != 1 or len(tfs) != 1:
    raise ValueError(
      f"Group must share one symbol+TF (got symbols={sorted(symbols)} tfs={sorted(tfs)})"
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


def _materialize_rows(rows: list[dict]) -> tuple[list[dict], dict[str, str], dict[str, float]]:
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
    sym = normalize_symbol(m.get("symbol"))
    tf = normalize_timeframe(m.get("timeframe"))
    if row.get("model_id") and str(row["model_id"]) != mid:
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
    if not sched_src.exists():
      # Fallback: copy from Final_app host desk if promote already froze a schedule
      try:
        from runtime_host import resolve_host_desk
        desk = resolve_host_desk(sym, tf)
        lab_sched = desk / "results" / "trade_models" / f"{mid}_schedule.json"
        if lab_sched.exists():
          shutil.copy2(lab_sched, pkg / "schedule.json")
          sched_src = pkg / "schedule.json"
          print(f"[materialize] backfilled schedule from {desk.name} → {install_id}", flush=True)
      except Exception as exc:
        print(f"[materialize] schedule backfill failed {install_id}: {exc}", flush=True)
    if sched_src.exists():
      shutil.copy2(sched_src, models_dir / f"{mid}_schedule.json")
      # Drop remine overrides so Live/Sim prefer frozen OOS genomes
      live_weeks = models_dir / f"{mid}_live_weeks.json"
      if live_weeks.exists():
        try:
          live_weeks.unlink()
        except OSError:
          pass
    else:
      print(
        f"[materialize] WARN {install_id}: no schedule.json — "
        "simulate will remine weekly and will NOT match lab OOS metrics",
        flush=True,
      )

    # Ensure bridge engine accepts this TF (desk checks data_timeframe)
    m["data_source"] = "mt5_ea"
    m["data_timeframe"] = tf
    m["feature_schema"] = max(int(m.get("feature_schema") or 0), 3)

    models.append(m)
    labels[mid] = str(m.get("label") or mid)
    risk_by_id[mid] = float(row.get("risk_pct") or 1.0)

  return models, labels, risk_by_id


def materialize_enabled(*, roster: dict | None = None) -> dict[str, Any]:
  """Materialize all enabled models (any mix of symbol/TF) into one store.

  Returns groups for multi-worker start:
    { n, model_ids, labels, risk_by_id, models_path, groups: [{symbol,timeframe,model_ids,rows}] }
  """
  rows = enabled_roster_rows(roster)
  if not rows:
    raise ValueError("No enabled models — turn at least one model On")

  models, labels, risk_by_id = _materialize_rows(rows)
  store_path = RESULTS_DIR / "trade_models.json"
  _write(store_path, {"models": models, "updated_from": "live_materialize"})
  if models:
    _write(RESULTS_DIR / "active_trade_model.json", {"id": models[0]["id"]})

  groups_out = []
  for (sym, tf), grow in group_models_by_book(rows).items():
    groups_out.append({
      "symbol": sym,
      "timeframe": tf,
      "model_ids": [str(r.get("model_id")) for r in grow],
      "rows": grow,
      "n": len(grow),
    })

  return {
    "model_ids": [m["id"] for m in models],
    "labels": labels,
    "risk_by_id": risk_by_id,
    "models_path": str(store_path),
    "n": len(models),
    "groups": groups_out,
    # compat for callers expecting single book
    "symbol": groups_out[0]["symbol"] if groups_out else None,
    "timeframe": groups_out[0]["timeframe"] if groups_out else None,
  }
