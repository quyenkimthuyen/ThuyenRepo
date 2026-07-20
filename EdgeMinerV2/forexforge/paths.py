"""Project paths — root is EdgeMinerV2/, not the package dir."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LEARNING_DIR = ROOT / "learning"
RESULTS_DIR = ROOT / "results"
DB_PATH = ROOT / "forexforge.db"


def ensure_dirs() -> None:
  for d in (DATA_DIR, LEARNING_DIR, RESULTS_DIR, LEARNING_DIR / "kb_profiles"):
    d.mkdir(parents=True, exist_ok=True)
