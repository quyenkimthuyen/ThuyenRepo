#!/usr/bin/env python3
"""Export a TrainApp Trade Model to a Trade `.tmpkg` (packages_inbox).

Writes the same v1 package Live imports at http://127.0.0.1:8601/?nav=Models.

  python scripts/export_trade_package.py --desk e21 --list
  python scripts/export_trade_package.py --desk e21 --model-id tm_...
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env, list_desks  # noqa: E402


def _bind(desk: str) -> dict:
  cfg = apply_desk_env(desk)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def main(argv: list[str] | None = None) -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desk", choices=list_desks(), help="TrainApp desk: e21 g23")
  ap.add_argument("--list", action="store_true", help="List models + schedule readiness")
  ap.add_argument("--model-id")
  ap.add_argument("--label")
  ap.add_argument("--all", action="store_true", help="Export every live (non-archived) model")
  ap.add_argument("--include-archived", action="store_true")
  ap.add_argument("--out", type=Path, help="Override output dir (default Trade/live/packages_inbox)")
  args = ap.parse_args(argv)

  if not args.desk:
    ap.error("Pass --desk e21|g23")

  _bind(args.desk)
  from gui.export_live_package import (  # noqa: E402
    default_export_dir,
    export_model_tmpkg,
    export_readiness,
  )
  from gui.trade_model import get_model_by_id, list_trade_models  # noqa: E402

  models = list_trade_models(include_archived=bool(args.include_archived))
  if args.list:
    print(f"=== {args.desk} ({len(models)}) ===")
    for m in models:
      mid = str(m.get("id") or "")
      ready = export_readiness(m)
      flag = "OK" if ready["ok"] else "BLOCKED"
      print(
        f"  {flag:8} {mid} | {m.get('label')} | "
        f"R={m.get('total_r')} weeks={ready['weeks']} | {ready['error'] or 'ready'}"
      )
    return 0

  chosen: list[dict] = []
  if args.model_id:
    found = get_model_by_id(args.model_id)
    if found:
      chosen = [found]
  elif args.label:
    chosen = [m for m in models if (m.get("label") or "") == args.label]
  elif args.all:
    chosen = models
  else:
    ap.error("Pass --list / --model-id / --label / --all")

  if not chosen:
    print(f"{args.desk}: no matching models", flush=True)
    return 1

  dest = args.out or default_export_dir()
  exported = 0
  failed = 0
  for m in chosen:
    try:
      result = export_model_tmpkg(m, out_dir=dest)
      print(
        f"OK {args.desk} · {result['label']} · weeks={result['weeks']} → {result['path']}",
        flush=True,
      )
      exported += 1
    except Exception as exc:
      failed += 1
      print(f"FAIL {args.desk} · {m.get('label')}: {exc}", flush=True)
  print(f"Exported {exported} package(s) · failed={failed} → {dest}", flush=True)
  return 0 if exported and failed == 0 else 1


if __name__ == "__main__":
  raise SystemExit(main())
