"""Desk-aware UI helpers (pair / TF / bars)."""
from __future__ import annotations


def bars_per_day() -> int:
  try:
    from config import BAR_MINUTES
    return max(1, (24 * 60) // int(BAR_MINUTES or 15))
  except Exception:
    return 96


def chart_bars_presets() -> dict[str, int]:
  b = bars_per_day()
  return {
    "1 ngày": b,
    "1 tuần": b * 7,
    "1 tháng": b * 30,
  }


def pair_label() -> str:
  try:
    from config import DEFAULT_PAIR
    return str(DEFAULT_PAIR or "EUR/USD")
  except Exception:
    return "EUR/USD"


def tf_label() -> str:
  try:
    from config import DEFAULT_TF
    return str(DEFAULT_TF or "M15")
  except Exception:
    return "M15"


def symbol_label() -> str:
  p = pair_label().replace("/", "")
  return p or "EURUSD"


def desk_caption() -> str:
  return f"{pair_label()} {tf_label()}"


def feature_profile_default() -> str:
  try:
    from config import DEFAULT_FEATURE_PROFILE
    return str(DEFAULT_FEATURE_PROFILE or "current")
  except Exception:
    return "current"
