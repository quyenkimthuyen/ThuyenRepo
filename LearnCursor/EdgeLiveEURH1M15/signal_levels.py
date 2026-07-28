"""Shared signal level helpers used by the MT5 bridge engine."""
from __future__ import annotations

import pandas as pd

from execution import adjust_entry_price


def week_bounds_for_ts(ts: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
  """ISO week containing ``ts`` (broker/series time) — used by live + HistoryFeed."""
  now = pd.Timestamp(ts)
  week_start = now - pd.Timedelta(days=int(now.weekday()))
  week_start = week_start.normalize()
  if week_start.hour > 0:
    week_start = pd.Timestamp(week_start.date())
  week_end = week_start + pd.Timedelta(days=7)
  return week_start, week_end


# Back-compat aliases
_week_bounds_for_ts = week_bounds_for_ts


def project_signal_levels(
  fm,
  strat,
  bar_idx: int,
  direction: int,
  spread_pips: float,
  slippage_pips: float,
  *,
  bar_minutes: int = 15,
) -> dict | None:
  """Compute entry / SL / TP for a signal at bar_idx.

  Live bridge: signal bar may be the last bar (no next bar yet). Then
  estimate entry ≈ close of signal bar; EA still fills at next open.
  """
  entry_idx = bar_idx + 1
  av = fm.atr[bar_idx]
  if pd.isna(av) or av <= 0:
    return None
  if entry_idx >= fm.n:
    raw_entry = float(fm.close[bar_idx])
    entry_time = str(fm.index[bar_idx] + pd.Timedelta(minutes=int(bar_minutes)))
  else:
    raw_entry = float(fm.open[entry_idx])
    entry_time = str(fm.index[entry_idx])
  entry_price = adjust_entry_price(raw_entry, direction, spread_pips, slippage_pips)
  sl_d = strat.atr_mult_sl * av
  if direction == 1:
    sl, tp = entry_price - sl_d, entry_price + sl_d * strat.rr_ratio
  else:
    sl, tp = entry_price + sl_d, entry_price - sl_d * strat.rr_ratio
  risk_pips = sl_d * 10000
  return {
    "signal_time": str(fm.index[bar_idx]),
    "entry_time": entry_time,
    "direction": "LONG" if direction == 1 else "SHORT",
    "entry_px": round(entry_price, 5),
    "sl": round(sl, 5),
    "tp": round(tp, 5),
    "risk_pips": round(risk_pips, 1),
    "rr": strat.rr_ratio,
    "hour": int(fm.hours[bar_idx]),
  }


_project_signal_levels = project_signal_levels
