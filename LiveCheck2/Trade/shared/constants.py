"""Constants for split_app Live magic / ports."""
from __future__ import annotations

# Live magic block — isolated from Final_app lab (202615xx) and backtest desks.
LIVE_MAGIC_BASE = 20263001
LIVE_SIM_MAGIC_BASE = 20264001
LIVE_MAX_MODELS = 15          # global Live magic slots
LIVE_MAX_MODELS_PER_CHART = 5  # ForgeBridgeLive MAX_MODELS per EA/chart

LIVE_APP_PORT = 8601
LIVE_BRIDGE_PORT = 9601
LIVE_SIM_PORT = 9701

LIVE_BRIDGE_SUBDIR = "bridge_live"
LIVE_BRIDGE_SIM_SUBDIR = "bridge_sim_live"
LIVE_INSTANCE_ID = "LIVE1"
