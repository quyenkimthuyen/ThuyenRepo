"""Global defaults for ForexForge (H1)."""
from dataclasses import dataclass

DEFAULT_START_DATE = "2023-01-01"
DEFAULT_PAIR = "EUR/USD"
DEFAULT_TF = "H1"
BAR_MINUTES = 60
BARS_PER_WEEK = 7 * 24 * (60 // BAR_MINUTES)
# H1 strategy: ~3 months train (API uses weeks; 12w ≈ 3 months)
TRAIN_WEEKS = 12
TRAIN_MONTHS = 3  # compat alias (~TRAIN_WEEKS)
TARGET_TRADES_PER_WEEK = 2.0
MAX_TRADES_PER_DAY = 1
MIN_TRAIN_BARS = 500

# Execution realism (pips, EUR/USD standard pip = 0.0001)
DEFAULT_SPREAD_PIPS = 1.0
DEFAULT_SLIPPAGE_PIPS = 0.3

# Risk dashboard
DEFAULT_RISK_PCT_PER_TRADE = 1.0
DEFAULT_MAX_WEEKLY_LOSS_R = 4.0

# Hold-out forward test
DEFAULT_HOLDOUT_MONTHS = 0
