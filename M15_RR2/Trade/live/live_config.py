"""Live app paths & settings."""
from __future__ import annotations

from pathlib import Path

LIVE_ROOT = Path(__file__).resolve().parent
SPLIT_ROOT = LIVE_ROOT.parent
MT5_ROOT = SPLIT_ROOT / "mt5"
INSTALLED_DIR = LIVE_ROOT / "installed_models"
RESULTS_DIR = LIVE_ROOT / "results"
ROSTER_PATH = RESULTS_DIR / "live_roster.json"
INBOX_DIR = LIVE_ROOT / "packages_inbox"

BRIDGE_DIR = MT5_ROOT / "bridge_live"
BRIDGE_SIM_DIR = MT5_ROOT / "bridge_sim_live"
