from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from systemtrain.backtest.engine import BacktestResult, Trade


def compute_metrics(result: BacktestResult, pip_size: float = 0.0001) -> dict[str, Any]:
    trades = result.trades
    if not trades:
        return _empty_metrics()

    closed = [t for t in trades if t.is_closed]
    if not closed:
        return _empty_metrics()

    pnls = np.array([t.pnl for t in closed])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]

    win_rate = len(wins) / len(closed)
    gross_profit = wins.sum() if len(wins) else 0.0
    gross_loss = abs(losses.sum()) if len(losses) else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Realized RR from average win / average loss
    avg_win = wins.mean() if len(wins) else 0.0
    avg_loss = abs(losses.mean()) if len(losses) else 0.0
    realized_rr = avg_win / avg_loss if avg_loss > 0 else 0.0

    equity = result.equity_curve
    max_dd = _max_drawdown(equity) if len(equity) > 1 else 0.0

    monthly_returns = _monthly_returns(equity)
    monthly_stability = (monthly_returns > 0).mean() if len(monthly_returns) else 0.0

    expectancy = pnls.mean()
    total_return = (equity.iloc[-1] / equity.iloc[0] - 1) if len(equity) > 1 else 0.0

    return {
        "trade_count": len(closed),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor) if np.isfinite(profit_factor) else 999.0,
        "realized_rr": float(realized_rr),
        "max_drawdown": float(max_dd),
        "monthly_stability": float(monthly_stability),
        "expectancy": float(expectancy),
        "total_return": float(total_return),
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "halted": result.halted,
        "halt_reason": result.halt_reason,
    }


def _empty_metrics() -> dict[str, Any]:
    return {
        "trade_count": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "realized_rr": 0.0,
        "max_drawdown": 0.0,
        "monthly_stability": 0.0,
        "expectancy": 0.0,
        "total_return": 0.0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "halted": False,
        "halt_reason": "",
    }


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (peak - equity) / peak.replace(0, np.nan)
    return float(dd.max())


def _monthly_returns(equity: pd.Series) -> pd.Series:
    if equity.empty:
        return pd.Series(dtype=float)
    monthly = equity.resample("ME").last().dropna()
    if len(monthly) < 2:
        return pd.Series(dtype=float)
    return monthly.pct_change().dropna()


def trades_to_dataframe(trades: list[Trade]) -> pd.DataFrame:
    rows = []
    for t in trades:
        rows.append(
            {
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "direction": "long" if t.direction == 1 else "short",
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "sl_price": t.sl_price,
                "tp_price": t.tp_price,
                "pnl": t.pnl,
                "result": t.result,
            }
        )
    return pd.DataFrame(rows)
