"""Global defaults for ForexForge."""
from dataclasses import dataclass

DEFAULT_START_DATE = "2023-01-01"
DEFAULT_PAIR = "GBP/USD"
DEFAULT_TF = "M5"
BAR_MINUTES = 5
BARS_PER_WEEK = 7 * 24 * (60 // BAR_MINUTES)
TRAIN_WEEKS = 3
TARGET_TRADES_PER_WEEK = 24.0
MAX_TRADES_PER_DAY = 5
MIN_TRAIN_BARS = 1500
DEFAULT_FEATURE_PROFILE = "m5_parity"

# Compatibility for old imports. New artifacts must use train_weeks.
TRAIN_MONTHS = TRAIN_WEEKS

# Execution realism (pips, GBP/USD standard pip = 0.0001)
DEFAULT_SPREAD_PIPS = 1.5
DEFAULT_SLIPPAGE_PIPS = 0.3

# Risk dashboard
DEFAULT_RISK_PCT_PER_TRADE = 1.0
DEFAULT_MAX_WEEKLY_LOSS_R = 4.0

# Hold-out forward test
DEFAULT_HOLDOUT_MONTHS = 0
