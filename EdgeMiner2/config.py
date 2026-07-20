"""Global defaults for ForexForge."""
from dataclasses import dataclass

DEFAULT_START_DATE = "2022-01-01"
DEFAULT_PAIR = "EUR/USD"
DEFAULT_TF = "H1"
TRAIN_MONTHS = 3
TARGET_TRADES_PER_WEEK = 2.0
MIN_TRAIN_BARS = 500

# Execution realism (pips, EUR/USD standard pip = 0.0001)
DEFAULT_SPREAD_PIPS = 1.0
DEFAULT_SLIPPAGE_PIPS = 0.3

# Risk dashboard
DEFAULT_RISK_PCT_PER_TRADE = 1.0
DEFAULT_MAX_WEEKLY_LOSS_R = 4.0

# Hold-out forward test
DEFAULT_HOLDOUT_MONTHS = 0
