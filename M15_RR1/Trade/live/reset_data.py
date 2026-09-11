"""Reset Live runtime data — journal, sim/parity, bridge state, OHLC cache, optional packages."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import (
  BRIDGE_DIR,
  BRIDGE_SIM_DIR,
  INSTALLED_DIR,
  INBOX_DIR,
  LIVE_ROOT,
  MT5_ROOT,
  RESULTS_DIR,
  ROSTER_PATH,
)

# Bridge runtime files (keep directory; wipe state)
BRIDGE_WIPE_FILES = (
  "fills.jsonl",
  "ea_fills.jsonl",
  "trades.json",
  "fill.json",
  "bar.json",
  "bars.json",
  "decision.json",
  "status.json",
  "connection.json",
  "sim_control.json",
  "command.json",
  "comm_log.jsonl",
  "history_status.json",
  "history_request.json",
  "models.json",
)
BRIDGE_WIPE_DIRS = ("decisions",)

# results/ files to remove (never touch Streamlit process files)
RESULTS_WIPE_GLOBS = (
  "parity_*.json",
  "parity_oos_batch.json",
  "replay_*.json",
  "replay_*.log",
  "replay_*.pid",
  "kill_switch.json",
  "live_workers.json",
  "mt5_bridge_config.json",
  "mt5_bridge_sim_config.json",
  "mt5_bridge_service.pid",
  "mt5_bridge_sim_service.pid",
  "active_trade_model.json",
  "trade_models.json",
)
RESULTS_KEEP = {
  "streamlit_app.pid",
  "streamlit_app.log",
  "live_roster.json",  # cleared separately when include_packages
}


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _rm(path: Path) -> bool:
  if not path.exists():
    return False
  try:
    if path.is_dir():
      shutil.rmtree(path)
    else:
      path.unlink()
    return True
  except OSError:
    return False


def _wipe_bridge_dir(bdir: Path) -> dict[str, int]:
  removed_files = 0
  removed_dirs = 0
  if not bdir.is_dir():
    return {"files": 0, "dirs": 0}
  for name in BRIDGE_WIPE_FILES:
    if _rm(bdir / name):
      removed_files += 1
  for name in BRIDGE_WIPE_DIRS:
    p = bdir / name
    if p.is_dir():
      for child in list(p.iterdir()):
        if _rm(child):
          removed_files += 1
      removed_dirs += 1
  return {"files": removed_files, "dirs": removed_dirs}


def list_bridge_dirs() -> list[Path]:
  out: list[Path] = []
  if not MT5_ROOT.exists():
    return out
  for p in sorted(MT5_ROOT.iterdir()):
    if not p.is_dir():
      continue
    name = p.name
    if name.startswith("bridge_live") or name.startswith("bridge_sim_live"):
      out.append(p)
  # ensure canonical dirs counted even if empty/missing
  for p in (BRIDGE_DIR, BRIDGE_SIM_DIR):
    if p not in out and p.exists():
      out.append(p)
  return out


def reset_live_data(
  *,
  stop_services: bool = True,
  journal: bool = True,
  sim_parity: bool = True,
  runtime: bool = True,
  ohlc_cache: bool = True,
  include_packages: bool = True,
  reseed_ohlc: bool = True,
  disarm_kill: bool = True,
  keep_live_weeks: bool = True,
) -> dict[str, Any]:
  """Full Live data reset. Returns a summary payload.

  ``keep_live_weeks`` (default True) preserves ``*_live_weeks.json`` — the
  frozen Monday remine Replay must reuse to match Live.
  """
  summary: dict[str, Any] = {
    "updated_at": _now(),
    "stopped": {},
    "bridges": {},
    "results_removed": [],
    "cache_removed": False,
    "packages_removed": 0,
    "roster_cleared": False,
    "reseed": [],
    "live_weeks_kept": [],
    "errors": [],
  }

  if stop_services:
    try:
      from bridge_control import stop_bridge
      summary["stopped"]["bridge"] = stop_bridge(flatten=False)
    except Exception as exc:
      summary["errors"].append(f"stop_bridge: {exc}")
    try:
      from replay_control import stop_replay
      summary["stopped"]["replay"] = stop_replay()
    except Exception as exc:
      summary["errors"].append(f"stop_replay: {exc}")

  if disarm_kill:
    try:
      from safety import disarm_kill_switch
      disarm_kill_switch()
      summary["kill_disarmed"] = True
    except Exception as exc:
      summary["errors"].append(f"disarm_kill: {exc}")

  if journal or runtime:
    for bdir in list_bridge_dirs():
      summary["bridges"][bdir.name] = _wipe_bridge_dir(bdir)

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)

  if sim_parity or runtime:
    for pattern in RESULTS_WIPE_GLOBS:
      for p in RESULTS_DIR.glob(pattern):
        if p.name in RESULTS_KEEP:
          continue
        if _rm(p):
          summary["results_removed"].append(p.name)

  if runtime:
    # materialized schedules / pins — keep frozen live remine by default
    tm = RESULTS_DIR / "trade_models"
    if tm.exists():
      n = 0
      kept: list[str] = []
      for p in list(tm.iterdir()):
        if keep_live_weeks and p.name.endswith("_live_weeks.json"):
          kept.append(p.name)
          continue
        if _rm(p):
          n += 1
      summary["trade_models_files_removed"] = n
      summary["live_weeks_kept"] = kept
    workers = RESULTS_DIR / "workers"
    if workers.exists():
      n = 0
      for p in list(workers.iterdir()):
        if _rm(p):
          n += 1
      summary["worker_logs_removed"] = n

  if ohlc_cache:
    data_dir = RESULTS_DIR / "data"
    if data_dir.exists():
      n = 0
      for p in list(data_dir.iterdir()):
        if _rm(p):
          n += 1
      summary["cache_removed"] = True
      summary["cache_files_removed"] = n

  if include_packages:
    if INSTALLED_DIR.exists():
      n = 0
      for p in list(INSTALLED_DIR.iterdir()):
        if _rm(p):
          n += 1
      summary["packages_removed"] = n
    if INBOX_DIR.exists():
      for p in list(INBOX_DIR.iterdir()):
        _rm(p)
    # empty roster
    payload = {"updated_at": _now(), "models": [], "active_book": None}
    ROSTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ROSTER_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary["roster_cleared"] = True
  elif not ROSTER_PATH.exists():
    # keep existing roster when not wiping packages
    pass

  if reseed_ohlc and ohlc_cache and not include_packages:
    # Only reseed when packages/roster still define books
    try:
      import importlib.util
      from package_store import load_roster
      from books import group_models_by_book

      spec = importlib.util.spec_from_file_location(
        "seed_mt5_cache", LIVE_ROOT / "scripts" / "seed_mt5_cache.py",
      )
      mod = importlib.util.module_from_spec(spec)
      assert spec.loader is not None
      spec.loader.exec_module(mod)
      roster = load_roster()
      enabled = [r for r in (roster.get("models") or []) if r.get("enabled")]
      groups = group_models_by_book(enabled) if enabled else {}
      if not groups:
        # seed common books from any roster rows
        rows = roster.get("models") or []
        groups = group_models_by_book(rows)
      for (sym, tf), _ in groups.items():
        try:
          info = mod.seed(sym, tf, allow_lab=True, force=True)
          summary["reseed"].append({
            "symbol": sym, "timeframe": tf, "bars": info.get("bars"), "sha256": info.get("sha256"),
          })
        except Exception as exc:
          summary["errors"].append(f"reseed {sym} {tf}: {exc}")
    except Exception as exc:
      summary["errors"].append(f"reseed: {exc}")

  summary["ok"] = len(summary["errors"]) == 0
  # audit trail
  try:
    (RESULTS_DIR / "last_reset.json").write_text(
      json.dumps(summary, indent=2, ensure_ascii=False, default=str) + "\n",
      encoding="utf-8",
    )
  except OSError:
    pass
  return summary
