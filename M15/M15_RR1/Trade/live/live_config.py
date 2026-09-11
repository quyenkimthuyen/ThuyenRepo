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

try:
  from shared.constants import LIVE_BRIDGE_SUBDIR, LIVE_BRIDGE_SIM_SUBDIR
except ImportError:
  _tag = SPLIT_ROOT.parent.name.replace("M15_", "").lower() or "live"
  LIVE_BRIDGE_SUBDIR = f"bridge_{_tag}"
  LIVE_BRIDGE_SIM_SUBDIR = f"bridge_sim_{_tag}"

BRIDGE_DIR = MT5_ROOT / LIVE_BRIDGE_SUBDIR
BRIDGE_SIM_DIR = MT5_ROOT / LIVE_BRIDGE_SIM_SUBDIR
