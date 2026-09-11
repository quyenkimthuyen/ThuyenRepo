#!/usr/bin/env python3
"""One-shot: extra KB eras + 12 epochs, then OOS 2026-h1 grids. Not part of the app."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/thuyenng/work/ThuyenRepo/M15_clone2_1/Train")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_std_recipe import _bind  # noqa: E402

EXTRA = [
  {
    "key": "2024-full",
    "label": "2024 (cả năm)",
    "learn_from": "2024-01-01",
    "learn_until": "2024-12-31",
    "kb_profile": "era_2024_full",
  },
  {
    "key": "2025-full",
    "label": "2025 (cả năm)",
    "learn_from": "2025-01-01",
    "learn_until": "2025-12-31",
    "kb_profile": "era_2025_full",
  },
]

PY = sys.executable
RECIPE = str(ROOT / "scripts" / "run_std_recipe.py")
WORKERS = "4"
EUR = "eur_fill_wk5_mid,eur_fill_wk5,eur_fill_elite_or"
GBP = "gbp_fill_wk5,gbp_fill_r50_clip,gbp_fill_elite_or"


def recipe(args: list[str]) -> int:
  cmd = [
    PY, "-u", RECIPE,
    "--keep-settings", "--no-reset-kb",
    "--loops", "12", "--oos-keys", "2026-h1",
    "--workers", WORKERS, *args,
  ]
  print(f"\n=== {' '.join(cmd)} ===", flush=True)
  rc = subprocess.call(cmd)
  if rc != 0:
    print(f"WARN wave rc={rc}", flush=True)
  return rc


def setup(desk: str) -> None:
  _bind(desk)
  from gui.app_settings import get_settings, merge_learning_eras_into_catalog, save_settings

  merge_learning_eras_into_catalog(EXTRA)
  s = dict(get_settings())
  s["learning_loops"] = 12
  save_settings(s)
  keys = [e["key"] for e in (s.get("learning_eras") or [])]
  print(
    f"setup {desk} loops=12 active={s.get('learning_era_keys')} catalog={keys}",
    flush=True,
  )


def main() -> int:
  print("OPT3 start extra KB eras + 12 epochs", flush=True)
  for desk in ("e21", "g23"):
    setup(desk)

  recipe(["--desks", "e21", "--era-keys", "2024-h1,2025-h1", "--learn-only", "--persist-loops"])
  recipe(["--desks", "g23", "--era-keys", "2025-h2,2025-h1", "--learn-only", "--persist-loops"])

  waves = [
    ["--desks", "e21", "--era-keys", "2024-h2", "--presets", EUR, "--weeks", "8"],
    ["--desks", "g23", "--era-keys", "2024-h2", "--presets", GBP, "--weeks", "6"],
    ["--desks", "e21", "--era-keys", "2025-h2", "--presets", EUR, "--weeks", "8"],
    ["--desks", "g23", "--era-keys", "2024-h1", "--presets", GBP, "--weeks", "6"],
    ["--desks", "e21", "--era-keys", "2024-full", "--presets", EUR, "--weeks", "8"],
    ["--desks", "g23", "--era-keys", "2024-full", "--presets", GBP, "--weeks", "6"],
    ["--desks", "e21", "--era-keys", "2025-full", "--presets", EUR, "--weeks", "8"],
    ["--desks", "g23", "--era-keys", "2025-full", "--presets", GBP, "--weeks", "6"],
    ["--desks", "e21", "--era-keys", "2024-h1,2025-h1", "--presets", EUR, "--weeks", "8", "--epochs", "11,12"],
    ["--desks", "g23", "--era-keys", "2025-h2,2025-h1", "--presets", GBP, "--weeks", "6", "--epochs", "11,12"],
  ]
  rc = 0
  for wave in waves:
    if recipe(wave) != 0:
      rc = 1
  print("OPT3 DONE", flush=True)
  return rc


if __name__ == "__main__":
  raise SystemExit(main())
