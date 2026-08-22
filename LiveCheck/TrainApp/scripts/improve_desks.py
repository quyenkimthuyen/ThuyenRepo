#!/usr/bin/env python3
"""Stretch-search unused weeks/presets on all 4 TrainApp desks, then promote TMs.

Existing 120-combo grids already covered weeks 3/6/9 × curated presets.
This run fills the gaps that usually lift WR/DD:

  M15: elite_60_3 / vwap / 60_35 + weeks 7/8/12
  M5:  elite_m5_balanced / wr60 / London-GBP presets + weeks 8/12
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Skip keys already in latest.json. Sizes stay ~30–45 walk-forwards / desk.
PLAN: dict[str, dict] = {
  "e21": {
    "weeks": [6, 7, 8, 9, 12],
    "presets": ["elite_60_3", "elite_60_3_vwap", "elite_60_35", "elite_or_quality", "elite_55_4"],
    "kb_profiles": ["era_2025_full"],
    "epochs": [1, 4],
    "workers": 2,
  },
  "g23": {
    "weeks": [3, 6, 8, 9, 12],
    "presets": ["elite_60_3", "elite_60_3_vwap", "elite_60_35", "elite_or_quality", "elite_55_4"],
    "kb_profiles": ["era_2025_h2"],
    "epochs": [3, 4],
    "workers": 2,
  },
  "e31": {
    "weeks": [6, 8, 9, 12],
    "presets": ["elite_m5_balanced", "elite_wr60", "elite_wr60_ldn", "elite_or_quality", "elite_55_4"],
    "kb_profiles": ["era_2025_h2"],
    "epochs": [2, 4],
    "workers": 2,
  },
  "g33": {
    "weeks": [3, 6, 8, 12],
    "presets": ["elite_gbp_ldn", "elite_gbp_rr4", "elite_m5_balanced", "elite_wr60", "elite_or_quality"],
    "kb_profiles": ["era_2025_full"],
    "epochs": [2, 4],
    "workers": 2,
  },
}


def _read_json(path: Path):
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def compact(x, digits: int = 1) -> str:
  s = f"{float(x):.{digits}f}".rstrip("0").rstrip(".")
  return s or "0"


def metric_label(row: dict) -> str:
  return (
    f"WR{compact(row.get('win_rate_pct') or 0)}"
    f"R{compact(row.get('total_r') or 0)}"
    f"DD{compact(row.get('max_drawdown_r') or 0)}"
  )


def _purge() -> None:
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer", "mining_presets",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)


def _bind(desk: str) -> dict:
  if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
  from desk_context import apply_desk_env

  cfg = apply_desk_env(desk)
  _purge()
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def _log(desk: str, msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [{desk}] {msg}"
  print(line, flush=True)
  log_dir = Path(os.environ.get("TRAINAPP_RUNTIME") or ROOT / "runtime" / desk) / "results"
  log_dir.mkdir(parents=True, exist_ok=True)
  with open(log_dir / "improve_desks.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def run_desk(desk: str, *, preview: bool = False, promote_only: bool = False) -> dict:
  plan = PLAN[desk]
  cfg = _bind(desk)
  from gui.grid_search_engine import (  # noqa: WPS433
    GridSpec,
    _score,
    load_latest_grid_run,
    run_grid,
    save_grid_run,
  )
  from gui.trade_model import create_trade_model
  from config import DEFAULT_TF

  prev = load_latest_grid_run() or {}
  prev_rows = [r for r in (prev.get("rows") or []) if isinstance(r, dict)]
  known = {str(r.get("key")) for r in prev_rows if r.get("key")}
  oos_from = str((prev.get("config") or {}).get("oos_from") or "2026-01-01")
  oos_to = str((prev.get("config") or {}).get("oos_to") or "2026-12-31")
  spread = float(cfg.get("spread_pips") or 1.9)
  slip = float(cfg.get("slippage_pips") or 0.3)

  specs: list[GridSpec] = []
  for week in plan["weeks"]:
    for preset in plan["presets"]:
      for kb in plan["kb_profiles"]:
        for ep in plan["epochs"]:
          spec = GridSpec(
            train_weeks=int(week),
            use_kb=True,
            kb_profile=str(kb),
            kb_snapshot=int(ep),
            oos_from=oos_from,
            oos_to=oos_to,
            spread_pips=spread,
            slippage_pips=slip,
            mining_preset=str(preset),
          )
          if spec.key() in known:
            continue
          specs.append(spec)

  _log(
    desk,
    f"{cfg.get('pair')} {cfg.get('tf')} stretch specs={len(specs)} "
    f"(skip existing {len(known)}) workers={plan['workers']}",
  )
  if preview:
    for spec in specs[:12]:
      _log(desk, f"  {spec.label()}")
    if len(specs) > 12:
      _log(desk, f"  … +{len(specs) - 12} more")
    return {"desk": desk, "specs": len(specs), "preview": True}

  new_rows: list[dict] = []
  if not promote_only and specs:
    def on_prog(done, total, label):
      if done == 1 or done == total or done % 4 == 0:
        _log(desk, f"Grid {done}/{total}: {label}")

    new_rows = run_grid(
      specs,
      objective="quality",
      on_progress=on_prog,
      workers=int(plan["workers"]),
    )
    ok = [r for r in new_rows if not r.get("error")]
    _log(desk, f"stretch done {len(ok)}/{len(new_rows)} OK")
  elif promote_only:
    _log(desk, "promote-only — reuse latest merged grid")

  by_key: dict[str, dict] = {}
  for row in prev_rows + new_rows:
    key = str(row.get("key") or "")
    if not key:
      continue
    by_key[key] = row
  merged = list(by_key.values())
  merged.sort(key=lambda r: _score(r, "quality"), reverse=True)
  rid = save_grid_run(
    merged,
    config={
      **(prev.get("config") or {}),
      "timeframe": DEFAULT_TF,
      "source": "improve_desks",
      "stretch_presets": plan["presets"],
      "stretch_weeks": plan["weeks"],
    },
    objective="quality",
  )
  _log(desk, f"merged latest={rid} n={len(merged)}")

  seen_labels: set[str] = set()
  created = []
  for i, row in enumerate(merged[:5]):
    if row.get("error") or row.get("total_r") is None:
      continue
    label = metric_label(row)
    if label in seen_labels:
      label = (
        f"WR{compact(row.get('win_rate_pct') or 0, 2)}"
        f"R{compact(row.get('total_r') or 0, 2)}"
        f"DD{compact(row.get('max_drawdown_r') or 0, 2)}"
      )
    seen_labels.add(label)
    model = create_trade_model(
      row,
      run_id=rid,
      label=label,
      set_active=False,
      build_report=False,
    )
    created.append({"id": model.get("id"), "label": label, "new": bool(new_rows)})
    _log(
      desk,
      f"TM {label}  R={row.get('total_r')} WR={row.get('win_rate_pct')} "
      f"DD={row.get('max_drawdown_r')} n={row.get('n_trades')} "
      f"{row.get('mining_preset')} tw={row.get('train_weeks')} id={model.get('id')}",
    )
  return {"desk": desk, "run_id": rid, "specs": len(specs), "promoted": created}


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", choices=list(PLAN))
  ap.add_argument("--desks", default=",".join(PLAN))
  ap.add_argument("--preview", action="store_true")
  ap.add_argument("--promote-only", action="store_true")
  args = ap.parse_args()

  if args.desk:
    out = run_desk(args.desk, preview=args.preview, promote_only=args.promote_only)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str), flush=True)
    return 0

  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip() in PLAN]
  if args.preview or args.promote_only:
    summary = []
    rc = 0
    for desk in desks:
      try:
        summary.append(run_desk(desk, preview=args.preview, promote_only=args.promote_only))
      except Exception as exc:
        rc = 1
        summary.append({"desk": desk, "error": str(exc)})
        print(f"FAILED {desk}: {exc}", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str), flush=True)
    return rc

  env = os.environ.copy()
  env["PYTHONUNBUFFERED"] = "1"
  procs = []
  for desk in desks:
    cmd = [sys.executable, "-u", str(Path(__file__).resolve()), "--desk", desk]
    print(f"spawn {desk}", flush=True)
    procs.append((desk, subprocess.Popen(cmd, cwd=str(ROOT), env=env)))
  summary = []
  rc = 0
  for desk, proc in procs:
    code = proc.wait()
    print(f"worker {desk} exit={code}", flush=True)
    if code != 0:
      rc = 1
    summary.append({"desk": desk, "exit": code})
  print(json.dumps(summary, indent=2), flush=True)
  return rc


if __name__ == "__main__":
  raise SystemExit(main())
