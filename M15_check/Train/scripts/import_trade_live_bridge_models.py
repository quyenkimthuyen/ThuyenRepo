#!/usr/bin/env python3
"""Import Trade Live MT5 Bridge models into TrainApp2 desks e21 / g23.

Copies the same ids + frozen weekly schedule + KB pin Trade is running, then
points each desk Bridge roster at those 5 models so Live can be compared.

Each desk runs in its own process so MODELS_PATH / BRIDGE_DIR bind correctly.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRADE = ROOT.parent / "Trade"
PACKAGES = TRADE / "packages_out" / "m15_top5"
PREFLIGHT = TRADE / "live" / "results" / "live_preflight.json"

DESK_BY_SYMBOL = {"EURUSD": "e21", "GBPUSD": "g23"}
SYMBOL_BY_DESK = {v: k for k, v in DESK_BY_SYMBOL.items()}


def _read(path: Path):
  if not path.is_file():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _sha16(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
      h.update(chunk)
  return h.hexdigest()[:16]


def _index_packages() -> dict[str, Path]:
  out: dict[str, Path] = {}
  if not PACKAGES.is_dir():
    raise SystemExit(f"Missing Trade packages: {PACKAGES}")
  for folder in PACKAGES.iterdir():
    if not folder.is_dir():
      continue
    model = _read(folder / "model.json") or {}
    mid = str(model.get("id") or "")
    if mid:
      out[mid] = folder
  return out


def _live_ids_by_symbol() -> dict[str, list[str]]:
  pf = _read(PREFLIGHT) or {}
  by: dict[str, list[str]] = {}
  for book in pf.get("books") or []:
    if not isinstance(book, dict):
      continue
    sym = str(book.get("symbol") or "").upper()
    tf = str(book.get("timeframe") or "").upper()
    if tf != "M15" or sym not in DESK_BY_SYMBOL:
      continue
    ids = [
      str(row["model_id"])
      for row in (book.get("models") or [])
      if isinstance(row, dict) and row.get("model_id") and row.get("ok")
    ]
    if ids:
      by[sym] = ids
  if not by:
    raise SystemExit(f"No M15 live models in {PREFLIGHT}")
  return by


def _space(model: dict) -> dict | None:
  space = model.get("mining_search_space") or model.get("miner_search_space")
  return space if isinstance(space, dict) and space else None


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


def _copy_frozen(pkg: Path, models_dir: Path, mid: str) -> None:
  """Copy schedule last so KPI/report writes cannot replace Trade genomes."""
  sched_src = pkg / "schedule.json"
  if not sched_src.is_file():
    raise RuntimeError(f"{pkg}: missing schedule.json")
  shutil.copy2(sched_src, models_dir / f"{mid}_schedule.json")
  live_src = pkg / "live_weeks.json"
  if not live_src.is_file():
    live_src = TRADE / "live" / "results" / "trade_models" / f"{mid}_live_weeks.json"
  if live_src.is_file():
    shutil.copy2(live_src, models_dir / f"{mid}_live_weeks.json")


def _import_one(desk: str, pkg: Path, *, now: str) -> str:
  cfg = _bind_desk(desk)
  from gui.trade_model import (
    _write_json,
    load_models_store,
    model_report_path,
    save_models_store,
  )

  model = _read(pkg / "model.json") or {}
  metrics = _read(pkg / "metrics.json") or {}
  manifest = _read(pkg / "manifest.json") or {}
  mid = str(model.get("id") or "")
  if not mid:
    raise RuntimeError(f"{pkg}: model.json missing id")

  models_dir = Path(cfg["runtime_root"]) / "results" / "trade_models"
  models_dir.mkdir(parents=True, exist_ok=True)

  pin_src = pkg / "kb_pin.json"
  kb_rel = None
  kb_fp = manifest.get("kb_fingerprint") or manifest.get("kb_fingerprint")
  if pin_src.is_file():
    pin_dst = models_dir / f"{mid}_kb_pin.json"
    shutil.copy2(pin_src, pin_dst)
    kb_rel = f"trade_models/{mid}_kb_pin.json"
    kb_fp = kb_fp or _sha16(pin_dst)

  wr = metrics.get("win_rate_pct", model.get("win_rate_pct"))
  total_r = metrics.get("total_r", model.get("total_r"))
  dd = metrics.get("max_drawdown_r", model.get("max_drawdown_r"))
  pf = metrics.get("profit_factor", model.get("profit_factor"))
  n_tr = metrics.get("n_trades", model.get("n_trades"))
  label = str(
    model.get("label")
    or f"{model.get('symbol') or desk.upper()} M15 · Trade live {mid[-8:]}"
  )

  rec = {
    "id": mid,
    "label": label,
    "label_custom": True,
    "source": "trade_live_import",
    "archived": False,
    "train_weeks": int(model.get("train_weeks") or 6),
    "max_trades_per_day": int(model.get("max_trades_per_day") or 2),
    "use_kb": bool(model.get("use_kb", True)),
    "kb_profile": model.get("kb_profile"),
    "kb_snapshot": model.get("kb_snapshot"),
    "oos_from": model.get("oos_from") or metrics.get("oos_from"),
    "oos_to": model.get("oos_to") or metrics.get("oos_to"),
    "spread_pips": model.get("spread_pips"),
    "slippage_pips": model.get("slippage_pips"),
    "total_r": total_r,
    "win_rate_pct": wr,
    "max_drawdown_r": dd,
    "profit_factor": pf,
    "n_trades": n_tr,
    "feature_profile": model.get("feature_profile") or "current",
    "feature_schema": int(model.get("feature_schema") or 3),
    "mining_search_space": _space(model),
    "data_source": "mt5_ea",
    "data_symbol": model.get("symbol"),
    "data_timeframe": model.get("timeframe") or "M15",
    "created_at": now,
    "imported_from": "Trade/packages_out/m15_top5",
  }
  if kb_rel:
    rec["kb_pin_path"] = kb_rel
    rec["kb_fingerprint"] = kb_fp

  store = load_models_store()
  models = list(store.get("models") or [])
  found = False
  for i, existing in enumerate(models):
    if existing.get("id") == mid:
      merged = dict(existing)
      merged.update(rec)
      merged["archived"] = False
      merged.pop("archived_at", None)
      models[i] = merged
      found = True
      break
  if not found:
    models.append(rec)
  store["models"] = models
  save_models_store(store)

  # Do not call save_model_report — it rebuilds schedule.json from walk-forward.
  _write_json(model_report_path(mid), {
    "overall_oos": {
      "total_r": total_r,
      "win_rate_pct": wr,
      "max_drawdown_r": dd,
      "profit_factor": pf,
      "n_trades": n_tr,
      "trades_per_week": metrics.get("trades_per_week"),
    },
    "config": {
      "trade_model_id": mid,
      "source": "trade_live_import",
      "mining_search_space": _space(model),
      "oos_from": rec["oos_from"],
      "oos_to": rec["oos_to"],
    },
  })
  _copy_frozen(pkg, models_dir, mid)
  return mid


def _set_bridge(desk: str, ids: list[str], *, keep_live: set[str]) -> None:
  _bind_desk(desk)
  from gui.trade_model import (
    load_models_store,
    save_active_model_id,
    save_models_store,
  )
  from mt5_bridge.background import MAX_BRIDGE_MODELS, load_config, save_config, sync_bridge_roster

  store = load_models_store()
  stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  for row in store.get("models") or []:
    mid = str(row.get("id") or "")
    if not mid:
      continue
    if mid in keep_live:
      row["archived"] = False
      row.pop("archived_at", None)
    elif not row.get("archived"):
      row["archived"] = True
      row["archived_at"] = stamp
  save_models_store(store)
  save_active_model_id(ids[0])

  if len(ids) > MAX_BRIDGE_MODELS:
    raise SystemExit(f"{desk}: {len(ids)} models > max {MAX_BRIDGE_MODELS}")
  cfg = load_config()
  save_config(
    model_id=ids[0],
    model_ids=ids,
    enabled=bool(cfg.get("enabled")),
    last_error=None,
  )
  sync_bridge_roster(model_ids=ids, risk_pct=float(cfg.get("risk_pct") or 1.0))


def _import_desk(desk: str) -> int:
  pkgs = _index_packages()
  by_sym = _live_ids_by_symbol()
  sym = SYMBOL_BY_DESK[desk]
  ids = by_sym.get(sym) or []
  if not ids:
    raise SystemExit(f"{desk}: no live M15 models for {sym} in preflight")
  missing = [i for i in ids if i not in pkgs]
  if missing:
    raise SystemExit(f"{sym}: packages missing for {missing}")
  now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  print(f"=== {desk} {sym} ({len(ids)}) ===")
  imported = []
  for mid in ids:
    got = _import_one(desk, pkgs[mid], now=now)
    print(f"  imported {got}")
    imported.append(got)
  _set_bridge(desk, imported, keep_live=set(imported))
  print(f"  bridge roster = {len(imported)}")
  return 0


def main() -> int:
  arg = (sys.argv[1] if len(sys.argv) > 1 else "").strip().lower()
  if arg in SYMBOL_BY_DESK:
    return _import_desk(arg)
  if arg:
    raise SystemExit(f"Usage: {Path(__file__).name} [e21|g23]")
  for desk in ("e21", "g23"):
    subprocess.check_call([sys.executable, str(Path(__file__).resolve()), desk])
  print("\nDone. Stop/Start Live Bridge on e21 and g23 so workers reload genomes.")
  print("Do not run both apps Live on the same MT5 account — magics differ, orders would double.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
