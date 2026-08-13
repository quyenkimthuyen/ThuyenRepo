#!/usr/bin/env python3
"""Import a .tmpkg into live/installed_models/."""
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

from shared.package_format import extract_package  # noqa: E402
from live_config import INSTALLED_DIR  # noqa: E402
from package_store import delete_installed, list_installed  # noqa: E402


def import_one(tmpkg: Path) -> Path:
  tmpkg = Path(tmpkg)
  if not tmpkg.exists():
    raise FileNotFoundError(tmpkg)
  staging = INSTALLED_DIR / "_staging"
  if staging.exists():
    shutil.rmtree(staging)
  extract_package(tmpkg, staging)
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
  model["label"] = label
  (staging / "manifest.json").write_text(
    json.dumps(man, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
  )
  if model_path.exists():
    model_path.write_text(
      json.dumps(model, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
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
  }
  (dest / "install_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
  return dest


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("package", nargs="?", help="Path to .tmpkg")
  ap.add_argument("--list", action="store_true")
  ap.add_argument(
    "--delete",
    metavar="INSTALL_ID",
    help="Delete an installed package (install_id from --list)",
  )
  args = ap.parse_args()
  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)

  if args.list:
    for row in list_installed():
      print(
        f"{row['install_id']} | {row['label']} | {row['symbol']} {row['timeframe']} | "
        f"id={row['model_id']}"
      )
    return 0

  if args.delete:
    out = delete_installed(args.delete)
    print(
      f"Deleted {out['install_id']} ({out.get('label') or out.get('model_id')}) "
      f"· roster -{out.get('removed_from_roster')}"
    )
    return 0

  if not args.package:
    ap.error("package path required (or --list / --delete)")
  dest = import_one(Path(args.package))
  print(f"Installed → {dest}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
