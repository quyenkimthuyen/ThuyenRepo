"""Run a TrainApp desk (Streamlit) with shared GUI + TF core + per-desk runtime."""
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
  parser.add_argument("desk", nargs="?", help="Desk id: e21 g23")
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
  app = ROOT / "gui" / "app.py"
  if not app.exists():
    raise SystemExit(f"Missing shared GUI app: {app}")
  runtime.mkdir(parents=True, exist_ok=True)
  for name in ("data", "results", "learning", "mt5"):
    (runtime / name).mkdir(parents=True, exist_ok=True)

  port = int(args.port or cfg.get("port") or 8711)
  print(
    f"TrainApp desk={cfg['id']} label={cfg.get('label')} "
    f"pair={cfg.get('pair')} {cfg.get('tf')} port={port}"
  )
  print(f"  gui     = {app}")
  print(f"  core    = {core}")
  print(f"  runtime = {runtime}")
  print(f"  bridge  = {cfg.get('bridge_subdir')} magic={cfg.get('magic')}")

  # Shared GUI first on path, then desk core (config / mt5_bridge / data_loader).
  path_prefix = [str(ROOT), str(core)]
  for p in reversed(path_prefix):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)

  if args.check:
    import config  # noqa: F401
    from mt5_bridge import protocol
    from gui.desk_ui import desk_caption
    print("  DEFAULT_PAIR", config.DEFAULT_PAIR, "TF", config.DEFAULT_TF)
    print("  FEATURE", getattr(config, "DEFAULT_FEATURE_PROFILE", "?"))
    print("  INSTANCE", protocol.INSTANCE_ID, "BRIDGE", protocol.BRIDGE_DIR)
    print("  UI", desk_caption())
    print("OK")
    return 0

  env = os.environ.copy()
  env["PYTHONPATH"] = os.pathsep.join(
    path_prefix + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
  )
  cmd = [
    sys.executable, "-m", "streamlit", "run", str(app),
    "--server.port", str(port),
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false",
  ]
  return subprocess.call(cmd, cwd=str(runtime), env=env)


if __name__ == "__main__":
  raise SystemExit(main())
