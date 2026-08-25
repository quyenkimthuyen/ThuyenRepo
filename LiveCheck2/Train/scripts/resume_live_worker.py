"""Resume the Live Bridge worker after Windows logon (called by live_windows_boot.ps1)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description="Resume Live Bridge worker for a desk")
  parser.add_argument("--desk", required=True, help="Desk id: e21 or g23")
  args = parser.parse_args(argv)

  if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
  os.environ.setdefault("TRAINAPP_ROOT", str(ROOT))

  from desk_context import apply_desk_env

  cfg = apply_desk_env(args.desk.strip().lower())
  core = str(Path(cfg["core_root"]).resolve())
  if core not in sys.path:
    sys.path.insert(0, core)

  from mt5_bridge.background import is_running, load_config, start_worker

  conf = load_config()
  if not conf.get("enabled"):
    print("skip worker: enabled=false")
    return 0
  if is_running():
    print("worker already running")
    return 0
  ok = start_worker(detached=True)
  print("worker start", "ok" if ok else "fail")
  return 0 if ok else 1


if __name__ == "__main__":
  raise SystemExit(main())
