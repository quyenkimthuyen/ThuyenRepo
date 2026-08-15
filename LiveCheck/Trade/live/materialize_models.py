"""Materialize installed packages → live/results trade_models store for BridgeEngine."""
from __future__ import annotations

import json
import os
import shutil
import time
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
  payload = json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n"
  last: Exception | None = None
  for i in range(8):
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{i}")
    try:
      tmp.write_text(payload, encoding="utf-8")
      os.replace(tmp, path)
      return
    except OSError as exc:
      last = exc
      try:
        if tmp.exists():
          tmp.unlink()
      except OSError:
        pass
      time.sleep(0.05 * (i + 1))
  if last:
    raise last


def _safe_copy2(src: Path, dest: Path) -> None:
  """Copy with retries — multi-worker Start races on the same kb_pin/schedule files."""
  dest.parent.mkdir(parents=True, exist_ok=True)
  try:
    if dest.exists():
      ss, ds = src.stat(), dest.stat()
      if ss.st_size == ds.st_size and abs(ss.st_mtime - ds.st_mtime) < 2.0:
        return
  except OSError:
    pass

  last: Exception | None = None
  for i in range(10):
    tmp = dest.with_suffix(dest.suffix + f".tmp.{os.getpid()}.{i}")
    try:
      shutil.copy2(src, tmp)
      os.replace(tmp, dest)
      return
    except OSError as exc:
      last = exc
      try:
        if tmp.exists():
          tmp.unlink()
      except OSError:
        pass
      time.sleep(0.05 * (i + 1))

  # Another worker likely finished the same copy — keep existing dest if present.
  if dest.exists() and dest.stat().st_size > 0:
    print(f"[materialize] WARN copy busy, keeping {dest.name}: {last}", flush=True)
    return
  if last:
    raise last



def enabled_roster_rows(roster: dict | None = None) -> list[dict]:
  from package_store import save_roster, sanitize_roster_models

  data = roster or load_roster()
  models = list(data.get("models") or [])
  cleaned, warnings = sanitize_roster_models(models)
  if warnings:
    # Persist force-disabled incomplete packages so UI/roster stay consistent.
    save_roster(cleaned, active_book=data.get("active_book"))
    for w in warnings:
      print(f"[materialize] {w}", flush=True)
  return [r for r in cleaned if r.get("enabled") and r.get("install_id")]



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
      _safe_copy2(src_pin, dest_pin)
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
          _safe_copy2(lab_sched, pkg / "schedule.json")
          sched_src = pkg / "schedule.json"
          print(f"[materialize] backfilled schedule from {desk.name} -> {install_id}", flush=True)
      except Exception as exc:
        print(f"[materialize] schedule backfill failed {install_id}: {exc}", flush=True)
    if not sched_src.exists():
      raise ValueError(
        f"{install_id}: missing schedule.json — re-export .tmpkg from Lab with "
        f"frozen schedule (export_model_schedule.py / --ensure-schedule). "
        f"Incomplete packages cannot be enabled for Live/Replay parity."
      )
    # Validate weekly genomes before copying into Live store
    try:
      from shared.package_format import validate_schedule_payload
      sched_data = _read(sched_src) or {}
      sched_errs = validate_schedule_payload(sched_data)
      if sched_errs:
        raise ValueError(f"{install_id}: " + "; ".join(sched_errs))
    except ValueError:
      raise
    except Exception as exc:
      raise ValueError(f"{install_id}: schedule.json unreadable: {exc}") from exc
    _safe_copy2(sched_src, models_dir / f"{mid}_schedule.json")
    # Drop remine overrides so Live/Sim prefer frozen OOS genomes
    live_weeks = models_dir / f"{mid}_live_weeks.json"
    if live_weeks.exists():
      try:
        live_weeks.unlink()
      except OSError:
        pass

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
