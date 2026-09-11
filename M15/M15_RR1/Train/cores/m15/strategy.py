"""Trade dataclass and metrics."""
from dataclasses import dataclass

import numpy as np


@dataclass
class Trade:
  entry_time: object
  exit_time: object
  direction: int
  entry_price: float
  exit_price: float
  sl: float
  tp: float
  pnl_pips: float
  r_multiple: float
  exit_reason: str


def max_drawdown_r(trades: list[Trade]) -> float:
  if not trades:
    return 0.0
  equity = np.cumsum([t.r_multiple for t in trades])
  peak = np.maximum.accumulate(equity)
  dd = peak - equity
  return float(dd.max()) if len(dd) else 0.0


def streak_stats(trades: list[Trade]) -> dict:
  if not trades:
    return {"max_win_streak": 0, "max_loss_streak": 0, "current_streak": 0, "current_streak_type": "none"}
  max_w = max_l = 0
  cur_w = cur_l = 0
  for t in trades:
    if t.r_multiple > 0:
      cur_w += 1
      cur_l = 0
      max_w = max(max_w, cur_w)
    else:
      cur_l += 1
      cur_w = 0
      max_l = max(max_l, cur_l)
  last = trades[-1].r_multiple
  return {
    "max_win_streak": max_w,
    "max_loss_streak": max_l,
    "current_streak": cur_w if last > 0 else cur_l,
    "current_streak_type": "win" if last > 0 else "loss",
  }


def risk_of_ruin_approx(
  win_rate: float, avg_win_r: float, avg_loss_r: float,
  risk_pct: float = 1.0, ruin_r: float = 20.0,
) -> float:
  """
  Ước lượng xác suất phá sản (0–1) với cố định % rủi ro mỗi lệnh.
  Dùng expectancy / edge — không phạt nhầm chiến lược WR < 50% nhưng RR cao.
  """
  if avg_loss_r <= 0 or win_rate <= 0 or win_rate >= 1:
    return 0.0
  p, q = win_rate, 1.0 - win_rate
  expectancy = p * avg_win_r - q * avg_loss_r
  if expectancy <= 0:
    return 0.95
  edge = min(expectancy / avg_loss_r, 0.99)
  base = (1.0 - edge) / (1.0 + edge)
  n = ruin_r / max(risk_pct / 100.0, 0.01)
  return float(np.clip(base ** min(n, 500), 0.0, 1.0))


def compute_metrics(trades: list[Trade], risk_pct_per_trade: float = 1.0) -> dict:
  if not trades:
    return {
      "n_trades": 0, "win_rate": 0.0, "avg_rr": 0.0, "profit_factor": 0.0,
      "total_pips": 0.0, "total_r": 0.0, "avg_win_r": 0.0, "avg_loss_r": 0.0,
      "max_drawdown_r": 0.0, "max_win_streak": 0, "max_loss_streak": 0,
      "risk_of_ruin_pct": 0.0,
    }
  r_vals = np.array([t.r_multiple for t in trades])
  pips = np.array([t.pnl_pips for t in trades])
  wins = r_vals > 0
  avg_win = r_vals[wins].mean() if wins.any() else 0.0
  avg_loss = abs(r_vals[~wins].mean()) if (~wins).any() else 1.0
  gp = pips[wins].sum() if wins.any() else 0.0
  gl = abs(pips[~wins].sum()) if (~wins).any() else 0.0
  st = streak_stats(trades)
  wr = float(wins.mean())
  ror = risk_of_ruin_approx(wr, avg_win, avg_loss, risk_pct_per_trade) * 100
  return {
    "n_trades": len(trades),
    "win_rate": wr,
    "avg_rr": float(avg_win / avg_loss) if avg_loss > 0 else 0.0,
    "profit_factor": float(gp / gl) if gl > 0 else float("inf"),
    "total_pips": float(pips.sum()),
    "total_r": float(r_vals.sum()),
    "avg_win_r": float(avg_win),
    "avg_loss_r": float(avg_loss),
    "max_drawdown_r": max_drawdown_r(trades),
    "max_win_streak": st["max_win_streak"],
    "max_loss_streak": st["max_loss_streak"],
    "current_streak": st["current_streak"],
    "current_streak_type": st["current_streak_type"],
    "risk_of_ruin_pct": round(ror, 1),
  }
