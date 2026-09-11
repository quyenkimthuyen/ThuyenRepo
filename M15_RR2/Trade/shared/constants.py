"""Constants for split_app Live magic / ports."""
from __future__ import annotations

# LiveCheck2 identity — offset from LiveCheck Trade (8601 / 20263001 / LIVE1).
LIVE_MAGIC_BASE = 20283201
LIVE_SIM_MAGIC_BASE = 20284201
LIVE_MAX_MODELS = 15          # global Live magic slots
LIVE_MAX_MODELS_PER_CHART = 5  # ForgeBridgeLive MAX_MODELS per EA/chart

LIVE_APP_PORT = 9201
LIVE_BRIDGE_PORT = 10201
LIVE_SIM_PORT = 10301

LIVE_BRIDGE_SUBDIR = "bridge_live"
LIVE_BRIDGE_SIM_SUBDIR = "bridge_sim_live"
LIVE_INSTANCE_ID = "LIVECL2"
