"""Run a TrainApp desk (Streamlit) with shared TF core + per-desk runtime."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env, list_desks  # noqa: E402


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(description="Start TrainApp desk UI")
  parser.add_argument("desk", nargs="?", help="Desk id: e21 g23 e31 g33")
  parser.add_argument("--list", action="store_true", help="List desks")
  parser.add_argument("--port", type=int, default=0, help="Override port")
  parser.add_argument("--check", action="store_true", help="Validate desk then exit")
  args = parser.parse_args(argv)

  if args.list or not args.desk:
    print("Desks:", ", ".join(list_desks()))
    if not args.desk:
      return 0 if args.list else 2

  cfg = apply_desk_env(args.desk)
  core = Path(cfg["core_root"])
  runtime = Path(cfg["runtime_root"])
  app = core / "gui" / "app.py"
  if not app.exists():
    raise SystemExit(f"Missing app: {app}")
  runtime.mkdir(parents=True, exist_ok=True)
  for name in ("data", "results", "learning", "mt5"):
    (runtime / name).mkdir(parents=True, exist_ok=True)

  port = int(args.port or cfg.get("port") or 8711)
  print(
    f"TrainApp desk={cfg['id']} label={cfg.get('label')} "
    f"pair={cfg.get('pair')} {cfg.get('tf')} port={port}"
  )
  print(f"  core    = {core}")
  print(f"  runtime = {runtime}")
  print(f"  bridge  = {cfg.get('bridge_subdir')} magic={cfg.get('magic')}")

  if args.check:
    # Import smoke
    sys.path.insert(0, str(core))
    import config  # noqa: F401
    from mt5_bridge import protocol
    print("  DEFAULT_PAIR", config.DEFAULT_PAIR, "TF", config.DEFAULT_TF)
    print("  INSTANCE", protocol.INSTANCE_ID, "BRIDGE", protocol.BRIDGE_DIR)
    print("OK")
    return 0

  env = os.environ.copy()
  # Core first on PYTHONPATH so gui/config/mt5_bridge resolve to shared code.
  env["PYTHONPATH"] = os.pathsep.join(
    [str(core), str(ROOT)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
  )
  cmd = [
    sys.executable, "-m", "streamlit", "run", str(app),
    "--server.port", str(port),
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false",
  ]
  # cwd=runtime so relative writes land in desk workspace when any code still uses cwd.
  return subprocess.call(cmd, cwd=str(runtime), env=env)


if __name__ == "__main__":
  raise SystemExit(main())
