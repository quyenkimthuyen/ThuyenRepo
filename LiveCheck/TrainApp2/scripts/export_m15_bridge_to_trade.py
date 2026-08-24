#!/usr/bin/env python3
"""Restore TrainApp2 M15 Bridge models, then export them into Trade Live.

Correct direction: TrainApp2 desks e21/g23 → Trade.
Reverts the accidental Trade → TrainApp2 import first.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRADE = ROOT.parent / "Trade"
OUT_DIR = TRADE / "packages_out" / "m15_from_trainapp2"

# Original Bridge rosters (suffixes) before the reversed import at 20:49.
E21_SUFFIXES = ("4a4a914b", "17f02183", "0b140e51", "aac3ed9f", "3d3a5f7a")
G23_SUFFIXES = ("2fda252b", "0dc9024d", "3b1c042f", "af189802", "be1c40b6")
E21_MAGICS = {
  "17f02183": 20261021,
  "0b140e51": 20261022,
  "aac3ed9f": 20261023,
  "3d3a5f7a": 20261024,
  "4a4a914b": 20261026,
}
G23_MAGICS = {
  "2fda252b": 20261042,
}
DESK_SUFFIXES = {"e21": E21_SUFFIXES, "g23": G23_SUFFIXES}
DESK_MAGICS = {"e21": E21_MAGICS, "g23": G23_MAGICS}


def _read(path: Path):
  if not path.is_file():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _write(path: Path, data) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  tmp.replace(path)


def _bind_desk(desk: str) -> dict:
  os.environ["TRAINAPP_DESK"] = desk
  os.environ["TRAINAPP_ROOT"] = str(ROOT)
  if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
  from desk_context import apply_desk_env

  cfg = apply_desk_env(desk)
  core = str(Path(cfg["core_root"]).resolve())
  for p in (str(ROOT), core):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def _ids_by_suffix(models: list[dict], suffixes: tuple[str, ...]) -> list[str]:
  by_suf: dict[str, str] = {}
  for row in models:
    mid = str(row.get("id") or "")
    for suf in suffixes:
      if mid.endswith(suf):
        by_suf[suf] = mid
        break
  if len(by_suf) == len(suffixes):
    return [by_suf[s] for s in suffixes]
  # Fallback: the 5 models archived by the reversed import (20:49).
  found = [
    str(row.get("id"))
    for row in models
    if str(row.get("archived_at") or "").startswith("2026-08-24T20:49")
    and str(row.get("source") or "") != "trade_live_import"
    and row.get("id")
  ]
  if len(found) == 5:
    return found
  missing = [s for s in suffixes if s not in by_suf]
  raise SystemExit(f"Cannot find original models for suffixes {missing}")


def _ensure_schedule(models_dir: Path, mid: str) -> dict:
  """Merge OOS schedule + live_weeks so Trade gets the same frozen genomes."""
  sched_path = models_dir / f"{mid}_schedule.json"
  live_path = models_dir / f"{mid}_live_weeks.json"
  sched = _read(sched_path) if sched_path.is_file() else None
  live = _read(live_path) if live_path.is_file() else None
  weekly: dict[str, dict] = {}
  meta = {}
  for src in (sched, live):
    if not isinstance(src, dict):
      continue
    meta = dict(src.get("meta") or meta)
    for row in src.get("weekly") or []:
      if not isinstance(row, dict) or not isinstance(row.get("strategy"), dict):
        continue
      ws = str(row.get("week_start") or "")[:10]
      if ws:
        weekly[ws] = row
  if not weekly:
    raise RuntimeError(
      f"{mid}: no weekly genomes in schedule.json or live_weeks.json — cannot export"
    )
  payload = {
    "meta": {
      **meta,
      "model_id": mid,
      "source": meta.get("source") or "merged_export",
      "n_weeks": len(weekly),
    },
    "weekly": [weekly[k] for k in sorted(weekly)],
  }
  _write(sched_path, payload)
  return payload


def _restore_desk(desk: str) -> list[str]:
  cfg = _bind_desk(desk)
  from gui.trade_model import load_models_store, save_active_model_id, save_models_store
  from mt5_bridge.background import MAX_BRIDGE_MODELS, load_config, save_config, sync_bridge_roster

  suffixes = DESK_SUFFIXES[desk]
  store = load_models_store()
  models = list(store.get("models") or [])
  ids = _ids_by_suffix(models, suffixes)
  keep = set(ids)
  stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  for row in models:
    mid = str(row.get("id") or "")
    if mid in keep:
      row["archived"] = False
      row.pop("archived_at", None)
    elif not row.get("archived"):
      row["archived"] = True
      row["archived_at"] = stamp
  store["models"] = models
  save_models_store(store)
  save_active_model_id(ids[0])

  if len(ids) > MAX_BRIDGE_MODELS:
    raise SystemExit(f"{desk}: {len(ids)} > max {MAX_BRIDGE_MODELS}")
  cfg_b = load_config()
  save_config(
    model_id=ids[0],
    model_ids=ids,
    enabled=bool(cfg_b.get("enabled")),
    last_error=None,
  )
  sync_bridge_roster(model_ids=ids, risk_pct=float(cfg_b.get("risk_pct") or 1.0))

  magic_by_suf = DESK_MAGICS.get(desk) or {}
  roster_path = Path(cfg_b.get("bridge_dir") or cfg["runtime_root"]) / "models.json"
  # bridge_dir already includes the folder; models.json lives there.
  bdir = Path(cfg_b.get("bridge_dir") or "")
  if bdir.is_dir():
    roster_path = bdir / "models.json"
  roster = _read(roster_path) or {}
  changed = False
  for row in roster.get("models") or []:
    mid = str(row.get("id") or "")
    suf = mid[-8:]
    if suf in magic_by_suf and int(row.get("magic") or 0) != int(magic_by_suf[suf]):
      row["magic"] = int(magic_by_suf[suf])
      changed = True
  if changed:
    _write(roster_path, roster)
  print(f"=== restore {desk} ===")
  for mid in ids:
    print(f"  {mid}")
  return ids


def _export_desk(desk: str) -> list[Path]:
  cfg = _bind_desk(desk)
  from gui.export_live_package import export_model_tmpkg
  from gui.trade_model import load_models_store

  suffixes = DESK_SUFFIXES[desk]
  models = list((load_models_store().get("models") or []))
  ids = _ids_by_suffix(models, suffixes)
  by_id = {str(m.get("id")): m for m in models}
  models_dir = Path(cfg["runtime_root"]) / "results" / "trade_models"
  OUT_DIR.mkdir(parents=True, exist_ok=True)
  print(f"=== export {desk} ===")
  paths: list[Path] = []
  for mid in ids:
    n = _ensure_schedule(models_dir, mid)
    weeks = len(n.get("weekly") or [])
    info = export_model_tmpkg(by_id[mid], out_dir=OUT_DIR)
    path = Path(info["path"])
    print(f"  {mid} weeks={weeks} -> {path.name}")
    paths.append(path)
  return paths


def _import_trade(exported: list[Path]) -> None:
  live = TRADE / "live"
  for p in (str(TRADE), str(live)):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  from import_trade_package import import_one
  from live_config import INSTALLED_DIR, RESULTS_DIR
  from magic_allocator import assign_magics
  from materialize_models import materialize_enabled
  from package_store import default_roster_from_installed, save_roster

  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
  for d in list(INSTALLED_DIR.iterdir()):
    if d.is_dir() and not d.name.startswith("_") and d.name.upper().startswith("M15_"):
      shutil.rmtree(d)

  print(f"=== import Trade ({len(exported)} packages) ===")
  for pkg in exported:
    dest = import_one(pkg)
    print(f"  installed {dest.name}")

  rows = assign_magics(default_roster_from_installed())
  save_roster(rows)
  mat = materialize_enabled()
  print(f"  roster on={sum(1 for r in rows if r.get('enabled'))} materialized={mat.get('n')}")

  # Copy TrainApp2 live_weeks so Trade uses the same current-week genome.
  tm_dst = RESULTS_DIR / "trade_models"
  tm_dst.mkdir(parents=True, exist_ok=True)
  for desk, suffixes in DESK_SUFFIXES.items():
    src_dir = ROOT / "runtime" / desk / "results" / "trade_models"
    store = _read(ROOT / "runtime" / desk / "results" / "trade_models.json") or {}
    ids = _ids_by_suffix(list(store.get("models") or []), suffixes)
    for mid in ids:
      src = src_dir / f"{mid}_live_weeks.json"
      if src.is_file():
        shutil.copy2(src, tm_dst / f"{mid}_live_weeks.json")


def main() -> int:
  arg = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
  if arg in ("e21", "g23"):
    cmd = sys.argv[2] if len(sys.argv) > 2 else "all"
    if cmd in ("restore", "all"):
      _restore_desk(arg)
    if cmd in ("export", "all"):
      _export_desk(arg)
    return 0
  if arg and arg not in ("restore", "export", "import", "all"):
    raise SystemExit(f"Usage: {Path(__file__).name} [restore|export|import|all|e21|g23]")

  step = arg or "all"
  if step in ("restore", "all"):
    for desk in ("e21", "g23"):
      subprocess.check_call([sys.executable, str(Path(__file__).resolve()), desk, "restore"])
  exported: list[Path] = []
  if step in ("export", "all"):
    if OUT_DIR.exists() and step == "all":
      shutil.rmtree(OUT_DIR)
    for desk in ("e21", "g23"):
      subprocess.check_call([sys.executable, str(Path(__file__).resolve()), desk, "export"])
    exported = sorted(OUT_DIR.glob("*.tmpkg"))
    if len(exported) != 10:
      raise SystemExit(f"Expected 10 .tmpkg, found {len(exported)} in {OUT_DIR}")
  if step in ("import", "all"):
    if not exported:
      exported = sorted(OUT_DIR.glob("*.tmpkg"))
    _import_trade(exported)
  print("\nDone. TrainApp2 Bridge is restored to original M15 models.")
  print("Trade Live now has those same 10 packages. Restart Trade Live workers.")
  print("Do not run both apps Live on the same MT5 account — magics differ.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
