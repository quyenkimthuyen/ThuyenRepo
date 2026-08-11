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
from package_store import list_installed  # noqa: E402


def import_one(tmpkg: Path) -> Path:
  tmpkg = Path(tmpkg)
  if not tmpkg.exists():
    raise FileNotFoundError(tmpkg)
  staging = INSTALLED_DIR / "_staging"
  if staging.exists():
    shutil.rmtree(staging)
  extract_package(tmpkg, staging)
  man = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
  mid = man.get("model_id") or "model"
  label = man.get("label") or mid
  install_id = f"{man.get('timeframe','TF')}_{man.get('symbol','SYM')}_{mid}"
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
  args = ap.parse_args()
  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)

  if args.list:
    for row in list_installed():
      print(
        f"{row['install_id']} | {row['label']} | {row['symbol']} {row['timeframe']} | "
        f"id={row['model_id']}"
      )
    return 0

  if not args.package:
    ap.error("package path required (or --list)")
  dest = import_one(Path(args.package))
  print(f"Installed → {dest}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
