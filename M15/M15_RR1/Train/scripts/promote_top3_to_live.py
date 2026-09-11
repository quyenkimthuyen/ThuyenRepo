#!/usr/bin/env python3
"""Take the 3 best Train trade models per desk and install them on Trade Live.

Ranking (catalog WR/n/R, OOS ~26 weeks):
  1. win_rate_pct > 50
  2. trades/week > 5  (n_trades / 26)
  3. higher total_r

Missing schedule.json is built with weekly remine (same as grid scoring).
Existing schedules are left untouched unless --force-schedule.

  python scripts/promote_top3_to_live.py --desk e21 --out /tmp/m15_top3_pkg
  python scripts/promote_top3_to_live.py --import-only --out /tmp/m15_top3_pkg
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parents[1]
TRADE = TRAIN.parent / "Trade"
LIVE = TRADE / "live"
OOS_WEEKS = 26.0
TOP_N = 3
DESKS = ("e21", "g23")


def _bind(desk: str) -> dict:
  if str(TRAIN) not in sys.path:
    sys.path.insert(0, str(TRAIN))
  from desk_context import apply_desk_env

  cfg = apply_desk_env(desk)
  for p in (str(TRAIN), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  os.environ["PYTHONUNBUFFERED"] = "1"
  return cfg


def _rank_key(model: dict) -> tuple:
  wr = float(model.get("win_rate_pct") or 0)
  n = int(model.get("n_trades") or 0)
  total_r = float(model.get("total_r") or 0)
  tpw = n / OOS_WEEKS if n else float(model.get("trades_per_week") or 0)
  return (
    0 if wr > 50 else 1,
    0 if tpw > 5 else 1,
    -total_r,
    -wr,
    -n,
  )


def pick_top(models: list[dict], n: int = TOP_N) -> list[dict]:
  ranked = sorted(
    [m for m in models if m.get("id")],
    key=_rank_key,
  )
  return ranked[:n]


def _kb_snapshot(raw) -> int | None:
  if raw in (None, "latest", ""):
    return None
  try:
    return int(raw)
  except (TypeError, ValueError):
    return None


def freeze_schedule(model: dict, df) -> dict:
  from run_backtest import run_walk_forward
  from strategy_miner import mining_search_space_from_dict
  from trade_model_schedule import save_model_schedule, schedule_from_walk_forward_result

  mid = str(model["id"])
  space = mining_search_space_from_dict(model.get("mining_search_space"))
  print(f"  walk-forward weekly remine {mid} …", flush=True)
  result = run_walk_forward(
    df,
    use_learning=bool(model.get("use_kb", True)),
    train_weeks=int(model.get("train_weeks") or 6),
    verbose=True,
    spread_pips=float(model.get("spread_pips") or 1.9),
    slippage_pips=float(model.get("slippage_pips") or 0.0),
    holdout_months=0,
    kb_profile=model.get("kb_profile") if model.get("use_kb", True) else None,
    kb_snapshot=_kb_snapshot(model.get("kb_snapshot")) if model.get("use_kb", True) else None,
    kb_pin_path=model.get("kb_pin_path"),
    oos_from=model.get("oos_from"),
    oos_to=model.get("oos_to"),
    feature_profile=model.get("feature_profile") or "current",
    search_space=space,
    remine_each_week=True,
  )
  result.setdefault("config", {})["trade_model_id"] = mid
  payload = schedule_from_walk_forward_result(result, mid)
  if not payload:
    raise RuntimeError(f"{mid}: walk-forward produced no schedule_weekly")
  path = save_model_schedule(mid, payload)
  overall = result.get("overall_oos") or {}
  print(
    f"  wrote {path.name} weeks={payload['meta']['n_weeks']} "
    f"wf_n={overall.get('n_trades')} wf_wr={overall.get('win_rate_pct')} "
    f"wf_r={overall.get('total_r')}",
    flush=True,
  )
  return payload


def promote_desk(desk_id: str, out_dir: Path, *, force_schedule: bool = False) -> list[Path]:
  cfg = _bind(desk_id)
  from gui.export_live_package import export_model_tmpkg, load_schedule
  from gui.trade_model import list_trade_models
  from data_loader import load_eurusd_m15

  picks = pick_top(list_trade_models(), TOP_N)
  print(
    f"=== {desk_id} {cfg.get('symbol')} {cfg.get('tf')} top {len(picks)} ===",
    flush=True,
  )
  if len(picks) < TOP_N:
    raise SystemExit(f"{desk_id}: only {len(picks)} models in catalog")

  keep_existing = {
    "tm_wr60r40_d634912b",
    "tm_wr76r61_afd20fd7",
  }
  need_wf = []
  for m in picks:
    mid = str(m["id"])
    n = int(m.get("n_trades") or 0)
    tpw = n / OOS_WEEKS
    has = load_schedule(mid) is not None
    rebuild = (not has) or (force_schedule and mid not in keep_existing)
    print(
      f"  {'KEEP' if not rebuild else 'REMINE'} {mid} {m.get('label')} "
      f"WR={m.get('win_rate_pct')} R={m.get('total_r')} n={n} "
      f"tpw={tpw:.2f} kb={m.get('kb_profile')}@{m.get('kb_snapshot')}",
      flush=True,
    )
    if rebuild:
      need_wf.append(m)

  df = None
  if need_wf:
    print(f"[{desk_id}] loading MT5 cache…", flush=True)
    df = load_eurusd_m15()
    print(f"[{desk_id}] {len(df)} bars {df.index[0]} → {df.index[-1]}", flush=True)
    for m in need_wf:
      freeze_schedule(m, df)

  out_dir.mkdir(parents=True, exist_ok=True)
  exported: list[Path] = []
  for m in picks:
    info = export_model_tmpkg(m, out_dir=out_dir, label_override=m.get("label"))
    exported.append(Path(info["path"]))
    print(
      f"[{desk_id}] exported {Path(info['path']).name} weeks={info.get('weeks')}",
      flush=True,
    )
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
      print(f"  wiped {p.name}", flush=True)


def import_packages(exported: list[Path]) -> int:
  sys.path.insert(0, str(TRADE))
  sys.path.insert(0, str(LIVE))
  from import_trade_package import import_one
  from magic_allocator import assign_magics
  from materialize_models import materialize_enabled
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
      f"  {r.get('symbol')} {r.get('label')} magic={r.get('magic')} "
      f"ready={r.get('ready')} weeks={r.get('schedule_weeks')}",
      flush=True,
    )

  mat = materialize_enabled()
  print(f"Materialized {mat.get('model_ids')}", flush=True)

  sync = LIVE / "sync_bridge_roster.py"
  rc = subprocess.call([sys.executable, str(sync)], cwd=str(LIVE))
  if rc != 0:
    print(f"sync_bridge_roster exit={rc}", flush=True)
    return rc
  want = TOP_N * len(DESKS)
  if len(exported) != want or len(enabled) != want:
    print(f"WARNING: expected {want} enabled, got export={len(exported)} on={len(enabled)}")
    return 1
  return 0


def main(argv: list[str] | None = None) -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", choices=list(DESKS))
  ap.add_argument("--out", type=Path, default=Path("/tmp/m15_top3_pkg"))
  ap.add_argument("--import-only", action="store_true")
  ap.add_argument("--spawn", action="store_true", help="Run both desks then import")
  ap.add_argument(
    "--force-schedule",
    action="store_true",
    help="Rebuild weekly-remine schedule even if one already exists (keeps WR60/WR76)",
  )
  args = ap.parse_args(argv)

  if args.import_only:
    pkgs = sorted(args.out.glob("*.tmpkg"))
    if not pkgs:
      print(f"No .tmpkg in {args.out}", file=sys.stderr)
      return 1
    wipe_m15_installed()
    return import_packages(pkgs)

  if args.spawn:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if args.out.exists():
      shutil.rmtree(args.out)
    args.out.mkdir(parents=True, exist_ok=True)
    procs = []
    for desk_id in DESKS:
      cmd = [sys.executable, "-u", str(Path(__file__).resolve()), "--desk", desk_id, "--out", str(args.out)]
      if args.force_schedule:
        cmd.append("--force-schedule")
      print(f"spawn {desk_id}: {' '.join(cmd)}", flush=True)
      procs.append((desk_id, subprocess.Popen(cmd, cwd=str(TRAIN), env=env)))
    failed = False
    for desk_id, proc in procs:
      rc = proc.wait()
      print(f"worker {desk_id} exit={rc}", flush=True)
      if rc != 0:
        failed = True
    if failed:
      return 1
    wipe_m15_installed()
    return import_packages(sorted(args.out.glob("*.tmpkg")))

  if not args.desk:
    ap.error("Pass --desk e21|g23, or --spawn, or --import-only")
  promote_desk(args.desk, args.out, force_schedule=args.force_schedule)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
