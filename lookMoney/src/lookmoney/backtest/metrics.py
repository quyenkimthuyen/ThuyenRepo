"""Backtest performance metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestMetrics:
    total_trades: int
    win_rate: float
    profit_factor: float
    total_pnl: float
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    avg_r_multiple: float
    expectancy: float
    final_balance: float

    def passes_gates(self) -> bool:
        return (
            self.total_trades >= 30
            and self.profit_factor >= 1.2
            and self.max_drawdown_pct <= 20.0
            and self.sharpe_ratio >= 0.5
        )

    def summary(self) -> str:
        gate = "PASS" if self.passes_gates() else "FAIL (review before live)"
        lines = [
            f"Trades:           {self.total_trades}",
            f"Win rate:         {self.win_rate:.1%}",
            f"Profit factor:    {self.profit_factor:.2f}",
            f"Total PnL:        ${self.total_pnl:,.2f}",
            f"Return:           {self.total_return_pct:.2%}",
            f"Max drawdown:     {self.max_drawdown_pct:.2%}",
            f"Sharpe (daily):   {self.sharpe_ratio:.2f}",
            f"Avg R-multiple:   {self.avg_r_multiple:.2f}",
            f"Expectancy:       ${self.expectancy:.2f}/trade",
            f"Final balance:    ${self.final_balance:,.2f}",
            f"Quality gate:     {gate}",
        ]
        return "\n".join(lines)


def compute_metrics(
    trades: pd.DataFrame,
    equity: pd.Series,
    initial_balance: float,
) -> BacktestMetrics:
    if trades.empty:
        return BacktestMetrics(
            total_trades=0,
            win_rate=0.0,
            profit_factor=0.0,
            total_pnl=0.0,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            avg_r_multiple=0.0,
            expectancy=0.0,
            final_balance=initial_balance,
        )

    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] < 0]
    gross_profit = wins["pnl"].sum() if not wins.empty else 0.0
    gross_loss = abs(losses["pnl"].sum()) if not losses.empty else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    peak = equity.cummax()
    dd = (peak - equity) / peak.replace(0, np.nan)
    max_dd = float(dd.max()) if not dd.empty else 0.0

    daily = equity.resample("D").last().dropna().pct_change().dropna()
    sharpe = 0.0
    if len(daily) > 1 and daily.std() > 0:
        sharpe = float((daily.mean() / daily.std()) * np.sqrt(252))

    r_vals = trades["r_multiple"].replace([np.inf, -np.inf], np.nan).dropna()
    avg_r = float(r_vals.mean()) if not r_vals.empty else 0.0

    final = float(equity.iloc[-1]) if not equity.empty else initial_balance
    total_pnl = final - initial_balance

    return BacktestMetrics(
        total_trades=len(trades),
        win_rate=float((trades["pnl"] > 0).mean()),
        profit_factor=float(pf),
        total_pnl=total_pnl,
        total_return_pct=total_pnl / initial_balance,
        max_drawdown_pct=max_dd,
        sharpe_ratio=sharpe,
        avg_r_multiple=avg_r,
        expectancy=float(trades["pnl"].mean()),
        final_balance=final,
    )
