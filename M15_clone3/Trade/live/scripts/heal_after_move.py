"""CLI wrapper — same as LiveCheck/scripts/heal_after_move.py."""
from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).resolve().parents[3] / "scripts" / "heal_after_move.py"
runpy.run_path(str(TARGET), run_name="__main__")
