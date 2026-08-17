#!/usr/bin/env python3
"""Import a .tmpkg into live/installed_models/.

Rejects incomplete packages (missing/empty schedule.json) — Live parity requires
frozen weekly genomes. Incomplete installs already on disk stay listed but cannot
be enabled (see package_store.package_ready).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

LIVE = Path(__file__).resolve().parent
SPLIT = LIVE.parent
sys.path.insert(0, str(SPLIT))
sys.path.insert(0, str(LIVE))

from shared.package_format import (  # noqa: E402
  _sha256_file,
  extract_package,
  package_has_usable_schedule,
  schedule_weekly_count,
  validate_package_dir,
)
from live_config import INSTALLED_DIR  # noqa: E402
from package_store import delete_installed, list_installed  # noqa: E402


def import_one(tmpkg: Path) -> Path:
  tmpkg = Path(tmpkg)
  if not tmpkg.exists():
    raise FileNotFoundError(tmpkg)
  if tmpkg.is_dir():
    raise IsADirectoryError(
      f"{tmpkg} is a folder, not a .tmpkg file.\n"
      f"Export from Lab first, then import a file like:\n"
      f"  python live/import_trade_package.py {tmpkg / 'YourModel.tmpkg'}\n"
      f"Or import every .tmpkg in that folder:\n"
      f"  python live/import_trade_package.py --dir {tmpkg}"
    )
  if tmpkg.suffix.lower() != ".tmpkg":
    raise ValueError(f"expected a .tmpkg package, got: {tmpkg.name}")
  staging = INSTALLED_DIR / "_staging"
  if staging.exists():
    shutil.rmtree(staging)
  try:
    extract_package(tmpkg, staging)
  except PermissionError as exc:
    raise PermissionError(
      f"Cannot read package file {tmpkg}: {exc}\n"
      "Close any program locking the file, or copy the .tmpkg elsewhere and retry."
    ) from exc
  except ValueError as exc:
    if staging.exists():
      shutil.rmtree(staging, ignore_errors=True)
    raise ValueError(
      f"{exc}\n"
      "Fix on Lab: export_model_schedule.py for this model, then re-export .tmpkg "
      "with schedule.json (lab/export_trade_package.py --ensure-schedule)."
    ) from exc
  man = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
  model_path = staging / "model.json"
  model = json.loads(model_path.read_text(encoding="utf-8")) if model_path.exists() else {}
  mid = man.get("model_id") or model.get("id") or "model"
  symbol = man.get("symbol") or model.get("symbol") or "?"
  timeframe = man.get("timeframe") or model.get("timeframe") or "?"
  raw_label = man.get("label") or model.get("label") or mid
  # Ensure unique display name across books
  prefix = f"{symbol} {timeframe} · "
  if str(raw_label).startswith(prefix) or str(raw_label).startswith(f"{symbol} {timeframe} "):
    label = str(raw_label)
  else:
    label = f"{prefix}{raw_label}"
  man["label"] = label
  man["has_schedule"] = package_has_usable_schedule(staging)
  try:
    sched = json.loads((staging / "schedule.json").read_text(encoding="utf-8"))
    man["schedule_weeks"] = schedule_weekly_count(sched)
  except Exception:
    man["schedule_weeks"] = 0
  model["label"] = label
  (staging / "manifest.json").write_text(
    json.dumps(man, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
  )
  if model_path.exists():
    model_path.write_text(
      json.dumps(model, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
  # Refresh checksums after label/manifest rewrite.
  sum_path = staging / "SHA256SUMS"
  if sum_path.exists():
    lines = []
    for name in (man.get("files") or ["manifest.json", "model.json"]):
      fp = staging / name
      if fp.exists():
        lines.append(f"{_sha256_file(fp)}  {name}")
    if lines:
      sum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
  errs = validate_package_dir(staging)
  if errs:
    shutil.rmtree(staging, ignore_errors=True)
    raise ValueError("package invalid after import prep: " + "; ".join(errs))

  install_id = f"{timeframe}_{symbol}_{mid}"
  install_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in install_id)[:80]
  dest = INSTALLED_DIR / install_id
  if dest.exists():
    shutil.rmtree(dest)
  staging.rename(dest)
  meta = {
    "installed_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "source_package": str(tmpkg.resolve()),
    "install_id": install_id,
    "label": label,
    "has_schedule": bool(man.get("has_schedule")),
    "schedule_weeks": int(man.get("schedule_weeks") or 0),
  }
  (dest / "install_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
  try:
    from weekend_preremine import drop_preremine_model
    drop_preremine_model(str(symbol), str(timeframe), str(mid))
  except Exception:
    pass
  return dest


def import_dir(folder: Path) -> list[Path]:
  folder = Path(folder)
  if not folder.is_dir():
    raise NotADirectoryError(folder)
  pkgs = sorted(folder.glob("*.tmpkg"))
  if not pkgs:
    raise FileNotFoundError(
      f"No .tmpkg files in {folder}.\n"
      "Export from Lab:\n"
      "  python lab/export_trade_package.py --ensure-schedule --out packages_out"
    )
  return [import_one(p) for p in pkgs]


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("package", nargs="?", help="Path to .tmpkg (file, not folder)")
  ap.add_argument(
    "--dir",
    type=Path,
    metavar="FOLDER",
    help="Import every .tmpkg in FOLDER (e.g. packages_out)",
  )
  ap.add_argument("--list", action="store_true")
  ap.add_argument(
    "--delete",
    metavar="INSTALL_ID",
    help="Delete an installed package (install_id from --list)",
  )
  ap.add_argument(
    "--audit",
    action="store_true",
    help="List installed packages and whether they are Live-ready (schedule OK)",
  )
  args = ap.parse_args()
  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)

  if args.list or args.audit:
    for row in list_installed():
      ready = "READY" if row.get("ready") else "INCOMPLETE"
      print(
        f"{ready:10} {row['install_id']} | {row['label']} | {row['symbol']} {row['timeframe']} | "
        f"id={row['model_id']} | schedule_weeks={row.get('schedule_weeks')} "
        f"| {row.get('ready_error') or 'ok'}"
      )
    return 0

  if args.delete:
    out = delete_installed(args.delete)
    print(
      f"Deleted {out['install_id']} ({out.get('label') or out.get('model_id')}) "
      f"- roster -{out.get('removed_from_roster')}"
    )
    return 0

  if args.dir:
    dests = import_dir(args.dir)
    for dest in dests:
      print(f"Installed -> {dest}")
    print(f"Done - {len(dests)} package(s)")
    return 0

  if not args.package:
    ap.error("package path required (or --dir / --list / --delete / --audit)")
  dest = import_one(Path(args.package))
  print(f"Installed -> {dest}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
