"""Global defaults for ForexForge."""
from dataclasses import dataclass

DEFAULT_START_DATE = "2022-01-01"
DEFAULT_PAIR = "GBP/USD"
DEFAULT_TF = "H1"
TRAIN_MONTHS = 3
TARGET_TRADES_PER_WEEK = 2.0
MIN_TRAIN_BARS = 500

# Execution realism (pips, GBP/USD standard pip = 0.0001)
DEFAULT_SPREAD_PIPS = 1.0
DEFAULT_SLIPPAGE_PIPS = 0.3

# Risk dashboard
DEFAULT_RISK_PCT_PER_TRADE = 1.0
DEFAULT_MAX_WEEKLY_LOSS_R = 4.0

# Hold-out forward test
DEFAULT_HOLDOUT_MONTHS = 0

# Max bars to hold a trade (H1) — mined from MAX_HOLD_GRID
DEFAULT_MAX_HOLD_BARS = 24
MAX_HOLD_GRID = [24, 36, 48]

# Spacing between trades & hybrid trail
DEFAULT_MIN_BARS_BETWEEN = 4
MIN_BARS_BETWEEN_GRID = [2, 4, 6]

# Hybrid trail — locked stable default (A/B: WR 66.7%, DD 3.8R)
DEFAULT_TRAIL_ACTIVATE_R = 1.0
DEFAULT_TRAIL_DISTANCE_R = 0.5
HYBRID_TRAIL_GRID = [
  {"trail_activate_r": DEFAULT_TRAIL_ACTIVATE_R, "trail_distance_r": DEFAULT_TRAIL_DISTANCE_R},
]

# Full grid for scripts/compare_exec_params.py only
HYBRID_TRAIL_COMPARE_GRID = [
  {"trail_activate_r": 1.0, "trail_distance_r": 0.5},
  {"trail_activate_r": 1.5, "trail_distance_r": 0.5},
  {"trail_activate_r": 1.8, "trail_distance_r": 0.6},
]
