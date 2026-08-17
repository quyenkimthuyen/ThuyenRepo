#!/usr/bin/env python3
"""Export top 5 exportable M15 TrainApp models per desk and import into Live."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
TRADE = LIVE.parent
TRAINAPP = TRADE.parent / "TrainApp"
sys.path.insert(0, str(TRAINAPP))
sys.path.insert(0, str(TRADE))
sys.path.insert(0, str(LIVE))

from desk_context import apply_desk_env  # noqa: E402
from gui.export_live_package import export_model_tmpkg  # noqa: E402
from import_trade_package import import_one  # noqa: E402
from live_config import INSTALLED_DIR  # noqa: E402
from magic_allocator import assign_magics  # noqa: E402
from package_store import default_roster_from_installed, save_roster  # noqa: E402

DESKS = ("e21", "g23")
TOP_N = 5


def _read_json(path: Path) -> dict | list | None:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def compact(x, digits: int = 1) -> str:
  s = f"{float(x):.{digits}f}".rstrip("0").rstrip(".")
  return s or "0"


def metric_label(model: dict) -> str:
  return (
    f"WR{compact(model.get('win_rate_pct') or 0)}"
    f"R{compact(model.get('total_r') or 0)}"
    f"DD{compact(model.get('max_drawdown_r') or 0)}"
  )


def attach_search_space(model: dict, tm_dir: Path) -> dict:
  mid = str(model.get("id") or "")
  space = model.get("mining_search_space")
  if isinstance(space, dict) and space:
    return model
  report = _read_json(tm_dir / f"{mid}.json")
  if isinstance(report, dict):
    space = report.get("mining_search_space") or (report.get("config") or {}).get(
      "mining_search_space"
    )
    if isinstance(space, dict) and space:
      model = dict(model)
      model["mining_search_space"] = space
      return model
  sched = _read_json(tm_dir / f"{mid}_schedule.json")
  weeks = (sched or {}).get("weeks") if isinstance(sched, dict) else None
  if isinstance(weeks, list) and weeks:
    space = (weeks[0] or {}).get("mining_search_space")
    if isinstance(space, dict) and space:
      model = dict(model)
      model["mining_search_space"] = space
  return model


def ranked_exportable(desk_id: str) -> list[dict]:
  apply_desk_env(desk_id)
  results = Path(TRAINAPP) / "runtime" / desk_id / "results"
  store = _read_json(results / "trade_models.json") or {}
  models = store.get("models") if isinstance(store, dict) else store
  tm_dir = results / "trade_models"
  rows: list[dict] = []
  for raw in models or []:
    if not isinstance(raw, dict):
      continue
    mid = str(raw.get("id") or "")
    if not (tm_dir / f"{mid}_schedule.json").exists():
      continue
    if raw.get("use_kb", True) and not (tm_dir / f"{mid}_kb_pin.json").exists():
      continue
    model = attach_search_space(raw, tm_dir)
    if not (isinstance(model.get("mining_search_space"), dict) and model["mining_search_space"]):
      continue
    rows.append(model)
  rows.sort(
    key=lambda m: (-float(m.get("total_r") or -1e9), -float(m.get("win_rate_pct") or 0))
  )
  return rows[:TOP_N]


def wipe_m15_installed() -> None:
  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
  for p in list(INSTALLED_DIR.iterdir()):
    if p.name.startswith("_"):
      continue
    if p.is_dir() and ("_EURUSD_" in p.name.upper() or "_GBPUSD_" in p.name.upper()) and p.name.upper().startswith("M15_"):
      shutil.rmtree(p)


def main() -> int:
  out_dir = TRADE / "packages_out" / "m15_top5"
  if out_dir.exists():
    shutil.rmtree(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)

  wipe_m15_installed()

  exported: list[Path] = []
  for desk_id in DESKS:
    picks = ranked_exportable(desk_id)
    print(f"=== {desk_id} top {len(picks)} ===", flush=True)
    seen: set[str] = set()
    for model in picks:
      label = metric_label(model)
      if label in seen:
        label = (
          f"WR{compact(model.get('win_rate_pct') or 0, 2)}"
          f"R{compact(model.get('total_r') or 0, 2)}"
          f"DD{compact(model.get('max_drawdown_r') or 0, 2)}"
        )
      seen.add(label)
      print(
        f"  {label}  R={model.get('total_r')} WR={model.get('win_rate_pct')} "
        f"DD={model.get('max_drawdown_r')} n={model.get('n_trades')} {model.get('id')}",
        flush=True,
      )
      info = export_model_tmpkg(model, out_dir=out_dir, label_override=label)
      exported.append(Path(info["path"]))
      print(f"    -> {Path(info['path']).name}", flush=True)

  print(f"\nImporting {len(exported)} packages…", flush=True)
  for pkg in exported:
    dest = import_one(pkg)
    print(f"  installed {dest.name}", flush=True)

  rows = assign_magics(default_roster_from_installed())
  save_roster(rows)
  enabled = [r for r in rows if r.get("enabled")]
  print(f"\nRoster: {len(enabled)} On / {len(rows)} total", flush=True)
  for r in sorted(enabled, key=lambda x: (x.get("symbol"), x.get("timeframe"), x.get("label"))):
    print(
      f"  {r.get('label')} magic={r.get('magic')} ready={r.get('ready')}",
      flush=True,
    )
  return 0 if len(exported) == TOP_N * len(DESKS) else 1


if __name__ == "__main__":
  raise SystemExit(main())
