#!/usr/bin/env python3
"""Restore the last 10 M15 Live models from packages_out/m15_top5 after a data reset."""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

LIVE = Path(__file__).resolve().parents[1]
TRADE = LIVE.parent
sys.path.insert(0, str(TRADE))
sys.path.insert(0, str(LIVE))

from import_trade_package import import_one  # noqa: E402
from live_config import INSTALLED_DIR  # noqa: E402
from magic_allocator import assign_magics  # noqa: E402
from package_store import default_roster_from_installed, save_roster  # noqa: E402

SRC = TRADE / "packages_out" / "m15_top5"
TMP = TRADE / "packages_out" / "_restore_tmpkg"


def _pack(src: Path, dest: Path) -> Path:
  dest.parent.mkdir(parents=True, exist_ok=True)
  if dest.exists():
    dest.unlink()
  with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(src.iterdir()):
      if p.is_file():
        zf.write(p, arcname=p.name)
  return dest


def main() -> int:
  dirs = sorted(d for d in SRC.iterdir() if d.is_dir() and not d.name.startswith("_"))
  if len(dirs) != 10:
    print(f"Expected 10 package folders in {SRC}, found {len(dirs)}", flush=True)
    return 1

  INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
  for p in list(INSTALLED_DIR.iterdir()):
    if p.name.startswith("_"):
      continue
    if p.is_dir():
      shutil.rmtree(p)

  if TMP.exists():
    shutil.rmtree(TMP)
  TMP.mkdir(parents=True)

  print(f"Importing {len(dirs)} packages…", flush=True)
  for d in dirs:
    pkg = _pack(d, TMP / f"{d.name}.tmpkg")
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
  shutil.rmtree(TMP, ignore_errors=True)
  return 0 if len(enabled) == 10 else 1


if __name__ == "__main__":
  raise SystemExit(main())
