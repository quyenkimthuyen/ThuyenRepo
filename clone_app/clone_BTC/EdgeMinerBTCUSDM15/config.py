"""Global defaults for ForexForge."""
from dataclasses import dataclass

DEFAULT_START_DATE = "2025-01-01"
DEFAULT_PAIR = "BTC/USD"
DEFAULT_TF = "M15"
BAR_MINUTES = 15
BARS_PER_WEEK = 7 * 24 * (60 // BAR_MINUTES)
TRAIN_WEEKS = 3
TARGET_TRADES_PER_WEEK = 10.0
MAX_TRADES_PER_DAY = 2
MIN_TRAIN_BARS = 500

# Compatibility for old imports. New artifacts must use train_weeks.
TRAIN_MONTHS = TRAIN_WEEKS

# Execution realism (pips, BTC/USD pip ≈ 1.0 (1 USD))
DEFAULT_SPREAD_PIPS = 25.0
DEFAULT_SLIPPAGE_PIPS = 5.0

# Risk dashboard
DEFAULT_RISK_PCT_PER_TRADE = 1.0
DEFAULT_MAX_WEEKLY_LOSS_R = 4.0

# Hold-out forward test
DEFAULT_HOLDOUT_MONTHS = 0
