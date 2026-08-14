#!/usr/bin/env python3
"""Export Trade Model(s) from Final_app lab desks → .tmpkg packages.

Requires a frozen ``*_schedule.json`` (OOS weekly genomes) so Live parity can
match lab metrics. Missing schedule → export fails (use --ensure-schedule to
run desk export_model_schedule.py first).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SPLIT = Path(__file__).resolve().parents[1]
FINAL = SPLIT.parent
sys.path.insert(0, str(SPLIT))

from shared.package_format import (  # noqa: E402
  build_manifest,
  schedule_weekly_count,
  validate_schedule_payload,
  write_package,
)

DESK_META = {
  "EdgeMinerEURUSDM15": {"instance": "M15F1", "symbol": "EURUSD", "timeframe": "M15"},
  "EdgeMinerGBPUSDM15": {"instance": "M15F2", "symbol": "GBPUSD", "timeframe": "M15"},
  "EdgeMinerEURUSDM5": {"instance": "M5F3", "symbol": "EURUSD", "timeframe": "M5"},
  "EdgeMinerGBPUSDM5": {"instance": "M5F4", "symbol": "GBPUSD", "timeframe": "M5"},
}

PY = Path("/home/thuyenng/work/ThuyenRepo/EdgeMinerM15B5/.venv/bin/python")


def _slug(s: str) -> str:
  return re.sub(r"[^a-zA-Z0-9_-]+", "_", (s or "model").strip())[:40]


def load_models(desk: Path) -> list[dict]:
  store = json.loads((desk / "results" / "trade_models.json").read_text(encoding="utf-8"))
  return [m for m in (store.get("models") or []) if not m.get("archived")]


def resolve_kb_pin(desk: Path, model: dict) -> Path | None:
  pin = model.get("kb_pin_path")
  if pin:
    p = Path(pin)
    if not p.is_absolute():
      p = desk / "results" / p
    if p.exists():
      return p
  mid = model.get("id")
  if mid:
    cand = desk / "results" / "trade_models" / f"{mid}_kb_pin.json"
    if cand.exists():
      return cand
  # try ensure pin via desk code
  try:
    sys.path.insert(0, str(desk))
    from trade_model_kb_pin import ensure_model_kb_pin, resolve_pin_absolute
    ensure_model_kb_pin(model)
    return resolve_pin_absolute(model.get("kb_pin_path"))
  except Exception:
    return None
  finally:
    if str(desk) in sys.path:
      try:
        sys.path.remove(str(desk))
      except ValueError:
        pass


def load_schedule(desk: Path, model_id: str) -> dict | None:
  p = desk / "results" / "trade_models" / f"{model_id}_schedule.json"
  if p.exists():
    return json.loads(p.read_text(encoding="utf-8"))
  return None


def ensure_schedule(desk: Path, model_id: str) -> dict | None:
  """Run desk export_model_schedule.py then reload schedule.json."""
  script = desk / "scripts" / "export_model_schedule.py"
  if not script.exists():
    raise RuntimeError(f"{desk.name}: missing scripts/export_model_schedule.py")
  py = str(PY if PY.exists() else sys.executable)
  print(f"==> ensure schedule {desk.name} {model_id}", flush=True)
  rc = subprocess.run(
    [py, str(script), "--model-id", model_id, "--quiet"],
    cwd=str(desk),
  ).returncode
  if rc != 0:
    raise RuntimeError(f"{desk.name}/{model_id}: export_model_schedule failed rc={rc}")
  return load_schedule(desk, model_id)


def metrics_from_model(m: dict) -> dict:
  keys = (
    "total_r", "profit_factor", "win_rate_pct", "max_drawdown_r",
    "n_trades", "trades_per_week", "oos_from", "oos_to",
  )
  return {k: m.get(k) for k in keys if m.get(k) is not None}


def export_one(
  desk_name: str,
  model: dict,
  out_dir: Path,
  *,
  ensure_sched: bool = False,
) -> Path:
  meta = DESK_META[desk_name]
  desk = FINAL / desk_name
  mid = model.get("id") or "unknown"
  raw_label = model.get("label") or mid
  # Disambiguate across desks: "EURUSD M5 · BestQuality"
  label = f"{meta['symbol']} {meta['timeframe']} · {raw_label}"
  if raw_label.startswith(f"{meta['symbol']} {meta['timeframe']}"):
    label = raw_label
  kb_pin = resolve_kb_pin(desk, model) if model.get("use_kb", True) else None
  if model.get("use_kb", True) and kb_pin is None:
    raise RuntimeError(
      f"{desk_name}/{label}: use_kb but kb_pin missing — run promote/ensure pin on lab desk first"
    )

  schedule = load_schedule(desk, mid)
  sched_errs = validate_schedule_payload(schedule)
  if sched_errs and ensure_sched:
    schedule = ensure_schedule(desk, mid)
    sched_errs = validate_schedule_payload(schedule)
  if sched_errs:
    hint = (
      f"Freeze schedule first:\n"
      f"  cd {desk} && {PY if PY.exists() else 'python'} "
      f"scripts/export_model_schedule.py --model-id {mid}\n"
      f"Or re-run export with --ensure-schedule"
    )
    raise RuntimeError(
      f"{desk_name}/{label}: incomplete package — {'; '.join(sched_errs)}\n{hint}"
    )

  payload = {
    "id": mid,
    "label": label,
    "mining_search_space": model.get("mining_search_space"),
    "train_weeks": model.get("train_weeks"),
    "use_kb": bool(model.get("use_kb", True)),
    "kb_profile": model.get("kb_profile"),
    "kb_snapshot": model.get("kb_snapshot"),
    "spread_pips": model.get("spread_pips"),
    "slippage_pips": model.get("slippage_pips"),
    "max_trades_per_day": model.get("max_trades_per_day"),
    "feature_profile": model.get("feature_profile") or (
      "m5_parity" if meta["timeframe"] == "M5" else "current"
    ),
    "feature_schema": int(model.get("feature_schema") or 3),
    "data_source": model.get("data_source") or "mt5_ea",
    "data_timeframe": meta["timeframe"],
    "oos_from": model.get("oos_from"),
    "oos_to": model.get("oos_to"),
    "total_r": model.get("total_r"),
    "profit_factor": model.get("profit_factor"),
    "win_rate_pct": model.get("win_rate_pct"),
    "max_drawdown_r": model.get("max_drawdown_r"),
    "n_trades": model.get("n_trades"),
    "symbol": meta["symbol"],
    "timeframe": meta["timeframe"],
  }
  lab = {
    "desk": desk_name,
    "instance": meta["instance"],
    "repo_relative": f"Final_app/{desk_name}",
  }
  files = ["manifest.json", "model.json"]
  manifest = build_manifest(
    model=payload,
    lab=lab,
    symbol=meta["symbol"],
    timeframe=meta["timeframe"],
    files=files,
  )
  out_name = f"{meta['instance']}_{_slug(label)}_{mid[-8:]}.tmpkg"
  out_path = out_dir / out_name
  path = write_package(
    out_path,
    manifest=manifest,
    model=payload,
    metrics=metrics_from_model(model),
    kb_pin_src=kb_pin,
    schedule=schedule,
  )
  print(
    f"  schedule_weeks={schedule_weekly_count(schedule)} → {path.name}",
    flush=True,
  )
  return path


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", choices=list(DESK_META), help="Single lab desk folder name")
  ap.add_argument("--all-desks", action="store_true")
  ap.add_argument("--list", action="store_true")
  ap.add_argument("--model-id")
  ap.add_argument("--label")
  ap.add_argument("--all", action="store_true", help="Export all live models on desk(s)")
  ap.add_argument("--best-only", action="store_true", help="Only labels starting with Best")
  ap.add_argument(
    "--ensure-schedule",
    action="store_true",
    help="If schedule missing, run desk export_model_schedule.py before packaging",
  )
  ap.add_argument("--out", type=Path, default=SPLIT / "packages_out")
  args = ap.parse_args()

  desks = list(DESK_META) if args.all_desks else ([args.desk] if args.desk else [])
  if not desks:
    ap.error("Pass --desk NAME or --all-desks")

  args.out.mkdir(parents=True, exist_ok=True)
  exported = []
  failed = 0

  for desk_name in desks:
    desk = FINAL / desk_name
    if not desk.exists():
      print(f"SKIP missing desk {desk}", flush=True)
      continue
    models = load_models(desk)
    if args.list:
      print(f"=== {desk_name} ({len(models)}) ===")
      for m in models:
        mid = m.get("id")
        sched = load_schedule(desk, str(mid))
        n_w = schedule_weekly_count(sched)
        ready = "OK" if n_w else "NO_SCHEDULE"
        print(
          f"  {ready:11} {m.get('id')} | {m.get('label')} | "
          f"R={m.get('total_r')} PF={m.get('profit_factor')} "
          f"oos={m.get('oos_from')}→{m.get('oos_to')} | weeks={n_w}"
        )
      continue

    chosen = []
    if args.model_id:
      chosen = [m for m in models if m.get("id") == args.model_id]
    elif args.label:
      chosen = [m for m in models if (m.get("label") or "") == args.label]
    elif args.all or args.best_only or args.all_desks:
      chosen = models
      if args.best_only:
        chosen = [m for m in chosen if str(m.get("label") or "").startswith("Best")]
    else:
      print(f"{desk_name}: pass --list / --label / --model-id / --all", flush=True)
      continue

    if not chosen:
      print(f"{desk_name}: no matching models", flush=True)
      continue

    for m in chosen:
      try:
        path = export_one(
          desk_name,
          m,
          args.out,
          ensure_sched=bool(args.ensure_schedule),
        )
        print(f"OK {desk_name} · {m.get('label')} → {path}", flush=True)
        exported.append(str(path))
      except Exception as exc:
        failed += 1
        print(f"FAIL {desk_name} · {m.get('label')}: {exc}", flush=True)

  if args.list:
    return 0
  print(f"Exported {len(exported)} package(s) · failed={failed} → {args.out}", flush=True)
  return 0 if exported and failed == 0 else 1


if __name__ == "__main__":
  raise SystemExit(main())
