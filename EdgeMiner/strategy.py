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


def compute_metrics(trades: list[Trade]) -> dict:
  if not trades:
    return {"n_trades": 0, "win_rate": 0.0, "avg_rr": 0.0, "profit_factor": 0.0,
            "total_pips": 0.0, "total_r": 0.0, "avg_win_r": 0.0, "avg_loss_r": 0.0}
  r_vals = np.array([t.r_multiple for t in trades])
  pips = np.array([t.pnl_pips for t in trades])
  wins = r_vals > 0
  avg_win = r_vals[wins].mean() if wins.any() else 0.0
  avg_loss = abs(r_vals[~wins].mean()) if (~wins).any() else 1.0
  gp = pips[wins].sum() if wins.any() else 0.0
  gl = abs(pips[~wins].sum()) if (~wins).any() else 0.0
  return {
    "n_trades": len(trades),
    "win_rate": float(wins.mean()),
    "avg_rr": float(avg_win / avg_loss) if avg_loss > 0 else 0.0,
    "profit_factor": float(gp / gl) if gl > 0 else float("inf"),
    "total_pips": float(pips.sum()),
    "total_r": float(r_vals.sum()),
    "avg_win_r": float(avg_win),
    "avg_loss_r": float(avg_loss),
  }
