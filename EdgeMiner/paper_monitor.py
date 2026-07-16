"""Paper / live monitor — tín hiệu tuần hiện tại."""
from __future__ import annotations

import pandas as pd

from config import TRAIN_MONTHS, MIN_TRAIN_BARS, DEFAULT_SPREAD_PIPS, DEFAULT_SLIPPAGE_PIPS
from data_loader import get_train_window_indices, get_week_indices
from feature_engine import FeatureMatrix
from optimizer import optimize_on_window
from strategy import compute_metrics
from strategy_miner import generate_signals_mined, backtest_mined


def _current_week_bounds(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
  now = df.index[-1]
  week_start = now - pd.Timedelta(days=now.weekday())
  week_start = week_start.normalize()
  if week_start.hour > 0:
    week_start = pd.Timestamp(week_start.date())
  week_end = week_start + pd.Timedelta(days=7)
  return week_start, week_end


def get_monitor_state(
  df: pd.DataFrame,
  use_learning: bool = False,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
) -> dict:
  """Trạng thái paper monitor: strategy tuần này, tín hiệu, lệnh đã có."""
  fm = FeatureMatrix(df)
  week_start, week_end = _current_week_bounds(df)

  train_start_idx, train_end_idx = get_train_window_indices(df, week_start, TRAIN_MONTHS)
  if train_start_idx is None or (train_end_idx - train_start_idx) < MIN_TRAIN_BARS:
    return {"error": "Không đủ dữ liệu train cho tuần hiện tại."}

  strat = optimize_on_window(
    fm, train_start_idx, train_end_idx,
    use_learning=use_learning, as_of=week_start,
  )
  if strat is None:
    return {"error": "Không mine được strategy."}

  oos_start, oos_end = get_week_indices(df, week_start, week_end)
  if oos_start is None:
    return {"error": "Không có bar OOS tuần này."}

  signals = generate_signals_mined(fm, strat, oos_start, oos_end)
  week_trades = backtest_mined(
    fm, strat, signals, oos_start, oos_end,
    spread_pips=spread_pips, slippage_pips=slippage_pips,
  )
  week_m = compute_metrics(week_trades)

  # Pending signals: bars with signal not yet traded (simplified)
  signal_bars = []
  for i in range(oos_start, oos_end - 1):
    if signals[i] != 0:
      signal_bars.append({
        "time": str(fm.index[i]),
        "direction": "LONG" if signals[i] == 1 else "SHORT",
        "hour": int(fm.hours[i]),
      })

  last_bar = df.index[-1]
  in_session = 7 <= last_bar.hour <= 20

  return {
    "week_start": str(week_start.date()),
    "week_end": str(week_end.date()),
    "last_bar": str(last_bar),
    "in_session": in_session,
    "strategy": {
      "name": strat.name,
      "exit_mode": strat.exit_mode,
      "rr": strat.rr_ratio,
      "ml_prob_min": strat.ml_prob_min,
      "max_trades_per_week": strat.max_trades_per_week,
    },
    "week_trades_taken": week_m["n_trades"],
    "week_total_r": round(week_m["total_r"], 2),
    "week_wr": round(week_m["win_rate"] * 100, 1),
    "slots_remaining": max(strat.max_trades_per_week - week_m["n_trades"], 0),
    "signals_this_week": signal_bars,
    "recent_trades": [
      {
        "entry": str(t.entry_time),
        "dir": "LONG" if t.direction == 1 else "SHORT",
        "r": round(t.r_multiple, 2),
        "reason": t.exit_reason,
      }
      for t in week_trades
    ],
  }
