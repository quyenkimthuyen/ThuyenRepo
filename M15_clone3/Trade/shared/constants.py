"""Constants for split_app Live magic / ports."""
from __future__ import annotations

# M15_clone3 — offset from clone2 (9201 / 20283201 / LIVECL2).
LIVE_MAGIC_BASE = 20283301
LIVE_SIM_MAGIC_BASE = 20284301
LIVE_MAX_MODELS = 15          # global Live magic slots
LIVE_MAX_MODELS_PER_CHART = 5  # ForgeBridgeLive MAX_MODELS per EA/chart

LIVE_APP_PORT = 9401
LIVE_BRIDGE_PORT = 10401
LIVE_SIM_PORT = 10501

LIVE_BRIDGE_SUBDIR = "bridge_live"
LIVE_BRIDGE_SIM_SUBDIR = "bridge_sim_live"
LIVE_INSTANCE_ID = "LIVECL3"
