"""Constants for split_app Live magic / ports."""
from __future__ import annotations

# LiveCheck2 identity — offset from LiveCheck Trade (8601 / 20263001 / LIVE1).
LIVE_MAGIC_BASE = 20283001
LIVE_SIM_MAGIC_BASE = 20284001
LIVE_MAX_MODELS = 15          # global Live magic slots
LIVE_MAX_MODELS_PER_CHART = 5  # ForgeBridgeLive MAX_MODELS per EA/chart

LIVE_APP_PORT = 8801
LIVE_BRIDGE_PORT = 9801
LIVE_SIM_PORT = 9901

LIVE_BRIDGE_SUBDIR = "bridge_live"
LIVE_BRIDGE_SIM_SUBDIR = "bridge_sim_live"
LIVE_INSTANCE_ID = "LIVE2"
