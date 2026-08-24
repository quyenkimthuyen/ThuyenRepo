"""Global defaults for ForexForge — desk-aware when TrainApp is active."""
from __future__ import annotations

from dataclasses import dataclass
import os


def _desk_cfg() -> dict:
  if not os.environ.get("TRAINAPP_DESK"):
    return {}
  try:
    import sys
    from pathlib import Path
    root = Path(os.environ.get("TRAINAPP_ROOT") or "").resolve()
    if root and str(root) not in sys.path:
      sys.path.insert(0, str(root))
    from desk_context import load_desk
    return load_desk()
  except Exception:
    return {}


_CFG = _desk_cfg()

DEFAULT_START_DATE = str(_CFG.get("start_date") or "2025-01-01")
DEFAULT_PAIR = str(_CFG.get("pair") or "EUR/USD")
DEFAULT_TF = str(_CFG.get("tf") or "M15")
BAR_MINUTES = int(_CFG.get("bar_minutes") or (5 if DEFAULT_TF == "M5" else 15))
BARS_PER_WEEK = 7 * 24 * (60 // BAR_MINUTES)
TRAIN_WEEKS = int(_CFG.get("train_weeks") or 3)
TARGET_TRADES_PER_WEEK = float(_CFG.get("target_trades_per_week") or (24.0 if DEFAULT_TF == "M5" else 10.0))
MAX_TRADES_PER_DAY = int(_CFG.get("max_trades_per_day") or (5 if DEFAULT_TF == "M5" else 2))
MIN_TRAIN_BARS = int(_CFG.get("min_train_bars") or (1500 if DEFAULT_TF == "M5" else 500))

# Compatibility for old imports. New artifacts must use train_weeks.
TRAIN_MONTHS = TRAIN_WEEKS

DEFAULT_SPREAD_PIPS = float(_CFG.get("spread_pips") or 1.0)
DEFAULT_SLIPPAGE_PIPS = float(_CFG.get("slippage_pips") or 0.3)

DEFAULT_RISK_PCT_PER_TRADE = 1.0
DEFAULT_MAX_WEEKLY_LOSS_R = 4.0
DEFAULT_HOLDOUT_MONTHS = 0

DEFAULT_FEATURE_PROFILE = str(
  _CFG.get("feature_profile") or ("m5_parity" if DEFAULT_TF == "M5" else "current")
)
