"""Global defaults for ForexForge — dual TF (H1 + M15)."""
from __future__ import annotations

from runtime_profiles import TF_DEFAULTS, get_tf_defaults

DEFAULT_PAIR = "EUR/USD"
DEFAULT_TF = "M15"

# Execution realism (pips, EUR/USD standard pip = 0.0001)
DEFAULT_SPREAD_PIPS = 1.0
DEFAULT_SLIPPAGE_PIPS = 0.3

# Risk dashboard
DEFAULT_RISK_PCT_PER_TRADE = 1.0
DEFAULT_MAX_WEEKLY_LOSS_R = 4.0

# Hold-out forward test
DEFAULT_HOLDOUT_MONTHS = 0

MIN_TRAIN_BARS = 500

# Active TF for CLI / workers (GUI overrides via session). Env: FORGE_TF=H1|M15
_ACTIVE_TF = DEFAULT_TF


def get_active_tf() -> str:
  return _ACTIVE_TF


def set_active_tf(tf: str) -> str:
  global _ACTIVE_TF
  t = str(tf).upper()
  if t not in TF_DEFAULTS:
    raise ValueError(f"Unsupported TF: {tf}")
  _ACTIVE_TF = t
  _sync_legacy_aliases()
  return _ACTIVE_TF


def active_defaults():
  return get_tf_defaults(get_active_tf())


# Back-compat module-level names (resolve from active TF). Prefer get_tf_defaults().
def _sync_legacy_aliases() -> None:
  d = active_defaults()
  global DEFAULT_START_DATE, BAR_MINUTES, BARS_PER_WEEK
  global TRAIN_WEEKS, TRAIN_MONTHS, TARGET_TRADES_PER_WEEK, MAX_TRADES_PER_DAY
  global MAX_TRADES_PER_WEEK, TRAIN_UNIT
  DEFAULT_START_DATE = d.start_date
  BAR_MINUTES = d.bar_minutes
  BARS_PER_WEEK = d.bars_per_week
  TRAIN_UNIT = d.train_unit
  TRAIN_WEEKS = d.train_length if d.train_unit == "weeks" else d.train_length
  TRAIN_MONTHS = d.train_length
  TARGET_TRADES_PER_WEEK = d.target_trades_per_week
  MAX_TRADES_PER_DAY = d.max_trades_per_day if d.max_trades_per_day is not None else 0
  MAX_TRADES_PER_WEEK = d.max_trades_per_week if d.max_trades_per_week is not None else 0


_sync_legacy_aliases()

# Re-export TF map for callers that want explicit lookup
TF_CONFIG = TF_DEFAULTS
