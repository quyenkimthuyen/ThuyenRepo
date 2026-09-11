"""Constants for split_app Live magic / ports."""
from __future__ import annotations

from pathlib import Path

# Folder name M15_RR2 → RR2. Off clone2 (9201/9311/8801) and RR1 (9501/9511).
_CLONE_DIR = Path(__file__).resolve().parents[2].name
CLONE_TAG = _CLONE_DIR.replace("M15_", "")

LIVE_MAGIC_BASE = 20285201
LIVE_SIM_MAGIC_BASE = 20286201
LIVE_MAX_MODELS = 15          # global Live magic slots
LIVE_MAX_MODELS_PER_CHART = 5  # ForgeBridgeLive MAX_MODELS per EA/chart

LIVE_APP_PORT = 9601
LIVE_BRIDGE_PORT = 10601
LIVE_SIM_PORT = 10701

LIVE_BRIDGE_SUBDIR = f"bridge_{CLONE_TAG.lower()}"
LIVE_BRIDGE_SIM_SUBDIR = f"bridge_sim_{CLONE_TAG.lower()}"
LIVE_INSTANCE_ID = f"LIVE{CLONE_TAG}"
LIVE_EA_STEM = f"ForgeBridgeLive{CLONE_TAG}"
LIVE_EA_SIM_STEM = f"ForgeBridgeLiveSim{CLONE_TAG}"
LIVE_EA_FOLDER = f"EdgeMiner{CLONE_TAG}"
