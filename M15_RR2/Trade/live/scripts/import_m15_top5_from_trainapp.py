#!/usr/bin/env python3
"""Promote top 5 M15 TrainApp models per desk, export .tmpkg, import into Live.

TrainApp e21/g23 currently have grid-search results but empty trade_models.
This script:

1. Picks the 5 best *quality* combos from each desk's latest grid search
   (positive R, PF>=1.2, n>=40, then WR/R/DD composite).
2. Creates Trade Models named ``WR<winrate>R<totalR>DD<maxDD>``.
3. Runs walk-forward to freeze ``schedule.json`` (required for Live).
4. Exports ``.tmpkg`` and installs them on the Trade Live roster.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
TRADE = LIVE.parent
TRAINAPP = TRADE.parent / "TrainApp"

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


def unique_metric_label(model: dict, seen: set[str]) -> str:
  label = metric_label(model)
  if label not in seen:
    return label
  return (
    f"WR{compact(model.get('win_rate_pct') or 0, 2)}"
    f"R{compact(model.get('total_r') or 0, 2)}"
    f"DD{compact(model.get('max_drawdown_r') or 0, 2)}"
  )


def quality_score(row: dict) -> float:
  """M15 quality score — same formula as TrainApp grid_search_engine._score."""
  total_r = float(row.get("total_r") or 0)
  dd = float(row.get("max_drawdown_r") or 1)
  pf = float(row.get("profit_factor") or 0)
  wr = float(row.get("win_rate_pct") or 0)
  n = int(row.get("n_trades") or 0)
  if total_r <= 0 or pf < 1.2 or n < 40:
    return -1e12
  return (total_r / max(dd, 0.5)) * 2.0 + pf * 25.0 + wr * 0.8 + total_r * 0.04


def latest_grid_path(desk_id: str) -> Path:
  return TRAINAPP / "runtime" / desk_id / "results" / "grid_search" / "latest.json"


def ranked_grid_rows(desk_id: str) -> list[dict]:
  data = _read_json(latest_grid_path(desk_id)) or {}
  rows: list[dict] = []
  for raw in data.get("rows") or []:
    if not isinstance(raw, dict) or raw.get("error"):
      continue
    if not (isinstance(raw.get("mining_search_space"), dict) and raw["mining_search_space"]):
      continue
    if raw.get("total_r") is None:
      continue
    rows.append(raw)
  rows.sort(key=lambda r: (-quality_score(r), -float(r.get("total_r") or 0)))
  return rows[:TOP_N]


def _bind_desk(desk_id: str) -> dict:
  if str(TRAINAPP) not in sys.path:
    sys.path.insert(0, str(TRAINAPP))
  from desk_context import apply_desk_env

  cfg = apply_desk_env(desk_id)
  for p in (str(TRAINAPP), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  os.environ["PYTHONUNBUFFERED"] = "1"
  return cfg


def promote_desk(desk_id: str, out_dir: Path, *, skip_wf: bool = False) -> list[Path]:
  """Create top-5 TMs for one desk, freeze schedules, export .tmpkg files."""
  cfg = _bind_desk(desk_id)
  from gui.export_live_package import export_model_tmpkg
  from gui.trade_model import create_trade_model, rename_trade_model, save_model_report
  from data_loader import load_eurusd_m15
  from run_backtest import run_walk_forward
  from strategy_miner import mining_search_space_from_dict

  picks = ranked_grid_rows(desk_id)
  print(
    f"=== {desk_id} {cfg.get('symbol')} {cfg.get('tf')} "
    f"top {len(picks)} quality ===",
    flush=True,
  )
  if len(picks) < TOP_N:
    print(f"WARNING: only {len(picks)} exportable grid rows", flush=True)

  out_dir.mkdir(parents=True, exist_ok=True)
  exported: list[Path] = []
  seen: set[str] = set()

  df = None
  if not skip_wf:
    print(f"[{desk_id}] loading MT5 cache…", flush=True)
    df = load_eurusd_m15()
    print(f"[{desk_id}] {len(df)} bars {df.index[0]} → {df.index[-1]}", flush=True)

  for i, row in enumerate(picks, 1):
    label = unique_metric_label(row, seen)
    seen.add(label)
    print(
      f"[{desk_id}] {i}/{len(picks)} {label}  "
      f"R={row.get('total_r')} WR={row.get('win_rate_pct')} "
      f"DD={row.get('max_drawdown_r')} n={row.get('n_trades')} "
      f"preset={row.get('mining_preset')} tw={row.get('train_weeks')} "
      f"kb={row.get('kb_profile')}@{row.get('kb_snapshot')}",
      flush=True,
    )
    model = create_trade_model(
      row,
      run_id=str((_read_json(latest_grid_path(desk_id)) or {}).get("run_id") or ""),
      label=label,
      set_active=False,
      build_report=False,
    )
    mid = str(model.get("id") or "")
    if not skip_wf:
      space = mining_search_space_from_dict(model.get("mining_search_space"))
      kb_snap = model.get("kb_snapshot")
      try:
        kb_snap = None if kb_snap in (None, "latest", "") else int(kb_snap)
      except (TypeError, ValueError):
        kb_snap = None
      print(f"[{desk_id}] walk-forward {mid} …", flush=True)
      result = run_walk_forward(
        df,
        use_learning=bool(model.get("use_kb", True)),
        train_weeks=int(model.get("train_weeks") or cfg.get("train_weeks") or 3),
        verbose=True,
        spread_pips=float(model.get("spread_pips") or cfg.get("spread_pips") or 1.9),
        slippage_pips=float(model.get("slippage_pips") or cfg.get("slippage_pips") or 0.3),
        holdout_months=0,
        kb_profile=model.get("kb_profile") if model.get("use_kb", True) else None,
        kb_snapshot=kb_snap if model.get("use_kb", True) else None,
        oos_from=model.get("oos_from"),
        oos_to=model.get("oos_to"),
        feature_profile=model.get("feature_profile") or "current",
        search_space=space,
      )
      result.setdefault("config", {})["trade_model_id"] = mid
      save_model_report(mid, result)
      overall = result.get("overall_oos") or {}
      for key in (
        "total_r", "win_rate_pct", "max_drawdown_r", "profit_factor",
        "n_trades", "trades_per_week",
      ):
        if overall.get(key) is not None:
          model[key] = overall[key]
      from gui.trade_model import load_models_store, save_models_store
      store = load_models_store()
      for m in store.get("models") or []:
        if m.get("id") == mid:
          m.update({k: model[k] for k in (
            "total_r", "win_rate_pct", "max_drawdown_r", "profit_factor",
            "n_trades", "trades_per_week",
          ) if k in model})
          break
      save_models_store(store)
      wf_label = unique_metric_label(model, seen - {label})
      if wf_label != label:
        rename_trade_model(mid, wf_label)
        label = wf_label
        seen.add(label)
      print(
        f"[{desk_id}] WF done {label} R={model.get('total_r')} "
        f"WR={model.get('win_rate_pct')} DD={model.get('max_drawdown_r')}",
        flush=True,
      )

    if skip_wf:
      print(f"[{desk_id}] created {mid} as {label} (schedule skipped)", flush=True)
      continue
    info = export_model_tmpkg(model, out_dir=out_dir, label_override=label)
    exported.append(Path(info["path"]))
    print(f"[{desk_id}] exported {Path(info['path']).name} weeks={info.get('weeks')}", flush=True)

  return exported


def wipe_m15_installed() -> None:
  sys.path.insert(0, str(TRADE))
  sys.path.insert(0, str(LIVE))
  from live_config import INSTALLED_DIR

  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
  for p in list(INSTALLED_DIR.iterdir()):
    if p.name.startswith("_"):
      continue
    if (
      p.is_dir()
      and ("_EURUSD_" in p.name.upper() or "_GBPUSD_" in p.name.upper())
      and p.name.upper().startswith("M15_")
    ):
      shutil.rmtree(p)


def import_packages(exported: list[Path]) -> int:
  sys.path.insert(0, str(TRADE))
  sys.path.insert(0, str(LIVE))
  from import_trade_package import import_one
  from magic_allocator import assign_magics
  from package_store import default_roster_from_installed, save_roster

  print(f"\nImporting {len(exported)} packages…", flush=True)
  for pkg in exported:
    dest = import_one(pkg)
    print(f"  installed {dest.name}", flush=True)

  rows = assign_magics(default_roster_from_installed())
  save_roster(rows)
  enabled = [r for r in rows if r.get("enabled")]
  print(f"\nRoster: {len(enabled)} On / {len(rows)} total", flush=True)
  for r in sorted(enabled, key=lambda x: (str(x.get("symbol")), str(x.get("label")))):
    print(
      f"  {r.get('label')} magic={r.get('magic')} ready={r.get('ready')}",
      flush=True,
    )
  return 0 if len(exported) == TOP_N * len(DESKS) and len(enabled) == len(exported) else 1


def run_workers(out_dir: Path, *, skip_wf: bool = False) -> list[Path]:
  env = os.environ.copy()
  env["PYTHONUNBUFFERED"] = "1"
  procs: list[tuple[str, subprocess.Popen]] = []
  for desk_id in DESKS:
    cmd = [
      sys.executable, "-u", str(Path(__file__).resolve()),
      "--desk", desk_id,
      "--out", str(out_dir),
    ]
    if skip_wf:
      cmd.append("--skip-wf")
    print(f"spawn {desk_id}: {' '.join(cmd)}", flush=True)
    procs.append((
      desk_id,
      subprocess.Popen(cmd, cwd=str(TRADE), env=env),
    ))
  failed = False
  for desk_id, proc in procs:
    rc = proc.wait()
    print(f"worker {desk_id} exit={rc}", flush=True)
    if rc != 0:
      failed = True
  if failed:
    raise SystemExit("A desk worker failed — see logs above")
  return sorted(out_dir.glob("*.tmpkg"))


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass

  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", choices=list(DESKS), help="Worker: promote one M15 desk")
  ap.add_argument("--out", type=Path, help="Export directory for .tmpkg")
  ap.add_argument("--skip-wf", action="store_true", help="Create/export without walk-forward")
  ap.add_argument("--preview", action="store_true", help="Print top-5 picks and exit")
  args = ap.parse_args()

  if args.preview:
    for desk_id in DESKS:
      picks = ranked_grid_rows(desk_id)
      print(f"=== {desk_id} top {len(picks)} quality ===")
      for i, row in enumerate(picks, 1):
        print(
          f"  {i} {metric_label(row)}  R={row.get('total_r')} "
          f"WR={row.get('win_rate_pct')} DD={row.get('max_drawdown_r')} "
          f"n={row.get('n_trades')} preset={row.get('mining_preset')}"
        )
    return 0

  out_dir = args.out or (TRADE / "packages_out" / "m15_top5")

  if args.desk:
    exported = promote_desk(args.desk, out_dir, skip_wf=args.skip_wf)
    if args.skip_wf:
      return 0
    return 0 if len(exported) == TOP_N else 1

  if out_dir.exists():
    shutil.rmtree(out_dir)
  out_dir.mkdir(parents=True, exist_ok=True)
  wipe_m15_installed()
  exported = run_workers(out_dir, skip_wf=args.skip_wf)
  return import_packages(exported)


if __name__ == "__main__":
  raise SystemExit(main())
