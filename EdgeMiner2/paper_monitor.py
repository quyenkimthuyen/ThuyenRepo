"""Paper / live monitor — tín hiệu tuần hiện tại."""
from __future__ import annotations

import pandas as pd

from analytics import trade_objects_to_rows
from config import (
  DEFAULT_RISK_PCT_PER_TRADE, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS,
  MIN_TRAIN_BARS, TRAIN_WEEKS,
)
from data_loader import get_train_window_indices, get_week_indices
from execution import adjust_entry_price
from feature_engine import FeatureMatrix
from mt5_bridge.history_sync import utc_to_broker_time
from optimizer import optimize_on_window
from strategy import compute_metrics
from strategy_miner import (
  generate_signals_mined, backtest_mined, mining_search_space_from_dict,
)


def _current_week_bounds(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
  now = df.index[-1]
  week_start = now - pd.Timedelta(days=now.weekday())
  week_start = week_start.normalize()
  if week_start.hour > 0:
    week_start = pd.Timestamp(week_start.date())
  week_end = week_start + pd.Timedelta(days=7)
  return week_start, week_end


def _project_signal_levels(
  fm, strat, bar_idx: int, direction: int,
  spread_pips: float, slippage_pips: float,
) -> dict | None:
  """Tính entry / SL / TP dự kiến cho tín hiệu tại bar_idx."""
  entry_idx = bar_idx + 1
  if entry_idx >= fm.n:
    return None
  av = fm.atr[bar_idx]
  if pd.isna(av) or av <= 0:
    return None
  entry_price = adjust_entry_price(fm.open[entry_idx], direction, spread_pips, slippage_pips)
  sl_d = strat.atr_mult_sl * av
  if direction == 1:
    sl, tp = entry_price - sl_d, entry_price + sl_d * strat.rr_ratio
  else:
    sl, tp = entry_price + sl_d, entry_price - sl_d * strat.rr_ratio
  risk_pips = sl_d * 10000
  return {
    "signal_time": str(fm.index[bar_idx]),
    "entry_time": str(fm.index[entry_idx]),
    "direction": "LONG" if direction == 1 else "SHORT",
    "entry_px": round(entry_price, 5),
    "sl": round(sl, 5),
    "tp": round(tp, 5),
    "risk_pips": round(risk_pips, 1),
    "rr": strat.rr_ratio,
    "hour": int(fm.hours[bar_idx]),
  }


def get_monitor_state(
  df: pd.DataFrame,
  use_learning: bool = False,
  train_weeks: int = TRAIN_WEEKS,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  risk_pct: float = DEFAULT_RISK_PCT_PER_TRADE,
  kb_profile: str | None = None,
  kb_snapshot: int | str | None = None,
  feature_profile: str = "current",
  mining_search_space: dict | None = None,
) -> dict:
  """Trạng thái paper monitor: strategy tuần này, tín hiệu, lệnh đã có."""
  from strategy_miner import ensure_label_cache_for_df

  ensure_label_cache_for_df(len(df))
  search_space = (
    mining_search_space_from_dict(mining_search_space)
    if mining_search_space else None
  )
  fm = FeatureMatrix(df, profile=feature_profile)
  week_start, week_end = _current_week_bounds(df)

  kb = None
  if use_learning:
    from optimizer import set_kb_profile, get_knowledge_base
    if kb_profile:
      set_kb_profile(kb_profile, kb_snapshot)
    kb = get_knowledge_base(kb_profile, kb_snapshot)

  train_start_idx, train_end_idx = get_train_window_indices(df, week_start, train_weeks)
  if train_start_idx is None or (train_end_idx - train_start_idx) < MIN_TRAIN_BARS:
    return {"error": "Không đủ dữ liệu train cho tuần hiện tại."}

  strat = optimize_on_window(
    fm, train_start_idx, train_end_idx,
    use_learning=use_learning, as_of=week_start, kb=kb,
    search_space=search_space,
  )
  if strat is None:
    return {"error": "Không mine được strategy."}

  oos_start, oos_end = get_week_indices(df, week_start, week_end)
  if oos_start is None:
    return {"error": "Không có bar OOS tuần này."}

  signals = generate_signals_mined(fm, strat, oos_start, oos_end)
  week_trades, open_position = backtest_mined(
    fm, strat, signals, oos_start, oos_end,
    spread_pips=spread_pips, slippage_pips=slippage_pips,
    return_open=True,
  )
  week_m = compute_metrics(week_trades, risk_pct)
  trade_rows = trade_objects_to_rows(week_trades)

  # Tín hiệu tuần này (kể cả chưa khớp lệnh)
  signal_bars = []
  traded_entries = {t["entry"] for t in trade_rows}
  for i in range(oos_start, oos_end - 1):
    if signals[i] == 0:
      continue
    proj = _project_signal_levels(
      fm, strat, i, int(signals[i]), spread_pips, slippage_pips,
    )
    if not proj:
      continue
    proj["status"] = "FILLED" if proj["entry_time"] in traded_entries else "SIGNAL"
    signal_bars.append(proj)

  # Chart window: tuần hiện tại + padding
  pad = pd.Timedelta(hours=24)
  chart_from = max(df.index[0], week_start - pad)
  chart_to = min(df.index[-1], week_end + pad)

  last_bar = df.index[-1]
  broker_last_bar = utc_to_broker_time(last_bar)
  in_session = 7 <= broker_last_bar.hour <= 20
  day_trades = [
    trade for trade in week_trades
    if utc_to_broker_time(trade.entry_time).date() == broker_last_bar.date()
  ]

  orders = []
  for t in trade_rows:
    orders.append({
      **t,
      "status": "CLOSED",
      "risk_pips": round(abs(t["entry_px"] - t["sl"]) * 10000, 1),
      "risk_pct": risk_pct,
      "pnl_pct": round(float(t.get("r") or 0) * risk_pct, 2),
    })
  if open_position:
    orders.append({
      **open_position,
      "exit": None, "exit_px": None, "r": None, "reason": None,
      "risk_pct": risk_pct,
    })
  for sig in signal_bars:
    if sig["status"] != "SIGNAL":
      continue
    orders.append({
      "status": "SIGNAL",
      "signal_time": sig["signal_time"],
      "entry": sig["entry_time"],
      "entry_time": sig["entry_time"],
      "dir": sig["direction"],
      "direction": sig["direction"],
      "entry_px": sig["entry_px"],
      "sl": sig["sl"],
      "tp": sig["tp"],
      "risk_pips": sig["risk_pips"],
      "rr": sig["rr"],
      "exit": None,
      "exit_px": None,
      "r": None,
      "reason": None,
      "risk_pct": risk_pct,
    })

  return {
    "week_start": str(week_start.date()),
    "week_end": str(week_end.date()),
    "chart_from": str(chart_from),
    "chart_to": str(chart_to),
    "last_bar": str(last_bar),
    "in_session": in_session,
    "strategy": {
      "name": strat.name,
      "exit_mode": strat.exit_mode,
      "rr": strat.rr_ratio,
      "atr_mult_sl": strat.atr_mult_sl,
      "ml_prob_min": strat.ml_prob_min,
      "max_trades_per_day": strat.max_trades_per_day,
      "max_hold_bars": strat.max_hold_bars,
    },
    "week_trades_taken": week_m["n_trades"],
    "day_trades_taken": len(day_trades),
    "week_total_r": round(week_m["total_r"], 2),
    "week_return_pct": round(week_m["total_r"] * risk_pct, 2),
    "risk_pct": risk_pct,
    "risk_of_ruin_pct": week_m.get("risk_of_ruin_pct", 0.0),
    "week_wr": round(week_m["win_rate"] * 100, 1),
    "slots_remaining": max(strat.max_trades_per_day - len(day_trades), 0),
    "kb_profile": kb_profile,
    "kb_snapshot": kb_snapshot if kb_snapshot not in (None, "latest") else "latest",
    "signals_this_week": signal_bars,
    "recent_trades": trade_rows,
    "orders": orders,
    "open_position": open_position,
  }
