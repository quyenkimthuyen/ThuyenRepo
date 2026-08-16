from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aiapp.strategy.robust_pullback import Params, generate_signals


PIP = 0.0001  # FX majors


@dataclass
class BacktestResult:
  trades: pd.DataFrame
  equity_r: pd.Series
  metrics: dict

  def to_dict(self) -> dict:
    return {
      "metrics": self.metrics,
      "n_trades": int(len(self.trades)),
      "trades_head": self.trades.head(20).to_dict(orient="records") if len(self.trades) else [],
    }


def _metrics(trades: pd.DataFrame) -> dict:
  if trades.empty:
    return {
      "n_trades": 0,
      "total_r": 0.0,
      "win_rate_pct": 0.0,
      "avg_rr": 0.0,
      "max_drawdown_r": 0.0,
      "profit_factor": 0.0,
      "robust_score": -1e9,
    }
  r = trades["r"].astype(float)
  wins = r[r > 0]
  losses = r[r <= 0]
  total_r = float(r.sum())
  wr = float((r > 0).mean() * 100)
  avg_win = float(wins.mean()) if len(wins) else 0.0
  avg_loss = float((-losses).mean()) if len(losses) else 0.0
  avg_rr = (avg_win / avg_loss) if avg_loss > 1e-9 else 0.0
  equity = r.cumsum()
  dd = float((equity - equity.cummax()).min())
  max_dd = abs(dd)
  gross_win = float(wins.sum()) if len(wins) else 0.0
  gross_loss = float((-losses).sum()) if len(losses) else 0.0
  pf = (gross_win / gross_loss) if gross_loss > 1e-9 else (999.0 if gross_win > 0 else 0.0)
  robust = (total_r / max(max_dd, 1.0)) - (0.05 * max(0.0, 55.0 - wr))
  return {
    "n_trades": int(len(trades)),
    "total_r": round(total_r, 3),
    "win_rate_pct": round(wr, 2),
    "avg_rr": round(avg_rr, 3),
    "max_drawdown_r": round(max_dd, 3),
    "profit_factor": round(pf, 3),
    "robust_score": round(robust, 3),
    "avg_win_r": round(avg_win, 3),
    "avg_loss_r": round(avg_loss, 3),
  }


def run_backtest(
  feat: pd.DataFrame,
  params: Params,
  *,
  spread_pips: float,
  slippage_pips: float = 0.3,
) -> BacktestResult:
  """Next-bar open entry; ATR stop; RR take-profit; one position; R accounting includes costs."""
  sig = generate_signals(feat, params)
  rows: list[dict] = []
  i = 1
  n = len(feat)
  idx = feat.index
  cost_price = (spread_pips + slippage_pips) * PIP

  trades_today = 0
  cur_day = None

  while i < n - 1:
    ts = idx[i]
    day = ts.date()
    if cur_day != day:
      cur_day = day
      trades_today = 0
    if trades_today >= params.max_trades_per_day:
      i += 1
      continue

    direction = int(sig.iloc[i - 1])  # signal from previous close
    if direction == 0:
      i += 1
      continue

    entry = float(feat["open"].iloc[i])
    atr = float(feat["atr"].iloc[i - 1])
    if "atr_daily" in feat.columns:
      atr_d = float(feat["atr_daily"].iloc[i - 1])
      if np.isfinite(atr_d) and atr_d > 0:
        # swing systems (lookback-based) use daily ATR
        if hasattr(params, "lookback") and int(getattr(params, "lookback") or 0) >= 8:
          atr = atr_d
    if not np.isfinite(atr) or atr <= 0:
      i += 1
      continue

    sl_dist = params.atr_sl_mult * atr
    if direction > 0:
      entry_eff = entry + cost_price  # pay ask
      sl = entry_eff - sl_dist
      tp = entry_eff + params.rr * sl_dist
    else:
      entry_eff = entry - cost_price  # hit bid
      sl = entry_eff + sl_dist
      tp = entry_eff - params.rr * sl_dist

    exit_px = None
    exit_i = None
    outcome = None
    for j in range(i + 1, n):
      hi = float(feat["high"].iloc[j])
      lo = float(feat["low"].iloc[j])
      if direction > 0:
        hit_sl = lo <= sl
        hit_tp = hi >= tp
        if hit_sl and hit_tp:
          # conservative: SL first
          exit_px, outcome, exit_i = sl, "sl", j
          break
        if hit_sl:
          exit_px, outcome, exit_i = sl, "sl", j
          break
        if hit_tp:
          exit_px, outcome, exit_i = tp, "tp", j
          break
      else:
        hit_sl = hi >= sl
        hit_tp = lo <= tp
        if hit_sl and hit_tp:
          exit_px, outcome, exit_i = sl, "sl", j
          break
        if hit_sl:
          exit_px, outcome, exit_i = sl, "sl", j
          break
        if hit_tp:
          exit_px, outcome, exit_i = tp, "tp", j
          break

    if exit_px is None:
      # force flat at last bar
      exit_i = n - 1
      exit_px = float(feat["close"].iloc[exit_i])
      outcome = "eod"

    # Round-trip cost already applied on entry via entry_eff; add exit half-spread approx
    if direction > 0:
      exit_eff = exit_px - cost_price * 0.5
      r_mult = (exit_eff - entry_eff) / sl_dist
    else:
      exit_eff = exit_px + cost_price * 0.5
      r_mult = (entry_eff - exit_eff) / sl_dist

    rows.append(
      {
        "entry_time": str(idx[i]),
        "exit_time": str(idx[exit_i]),
        "side": "LONG" if direction > 0 else "SHORT",
        "entry": round(entry_eff, 5),
        "exit": round(float(exit_eff), 5),
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "r": round(float(r_mult), 4),
        "outcome": outcome,
      }
    )
    trades_today += 1
    i = exit_i + 1

  trades = pd.DataFrame(rows)
  if trades.empty:
    equity = pd.Series(dtype=float)
  else:
    equity = trades["r"].cumsum()
    equity.index = pd.to_datetime(trades["exit_time"])
  return BacktestResult(trades=trades, equity_r=equity, metrics=_metrics(trades))
