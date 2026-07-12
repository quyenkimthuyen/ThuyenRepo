"""Analytics — Monte Carlo, monthly breakdown, stress spread."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from besttrade.engine import run_multi_year, run_year_backtest
from besttrade.params import locked_params


def _trade_pnls(trades: list) -> np.ndarray:
    pnls = []
    for t in trades:
        pnl = t.pnl if hasattr(t, "pnl") else t.get("pnl", 0)
        if pnl is not None:
            pnls.append(float(pnl))
    return np.array(pnls, dtype=float)


def bootstrap_monte_carlo(
    trades: list,
    initial_equity: float,
    simulations: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    pnls = _trade_pnls(trades)
    if len(pnls) == 0:
        return {
            "simulations": simulations,
            "trade_count": 0,
            "positive_pct": 0.0,
            "median_return": 0.0,
            "p5_return": 0.0,
            "p95_return": 0.0,
            "worst_drawdown_p95": 0.0,
            "passed": False,
            "verdict": "Không đủ lệnh để mô phỏng",
        }

    rng = np.random.default_rng(seed)
    final_returns = []
    max_drawdowns = []

    for _ in range(simulations):
        shuffled = rng.permutation(pnls)
        equity = initial_equity
        peak = equity
        max_dd = 0.0
        for pnl in shuffled:
            equity += pnl
            peak = max(peak, equity)
            if peak > 0:
                max_dd = max(max_dd, (peak - equity) / peak)
        final_returns.append(equity / initial_equity - 1)
        max_drawdowns.append(max_dd)

    final_returns = np.array(final_returns)
    max_drawdowns = np.array(max_drawdowns)
    positive_pct = float((final_returns > 0).mean())

    return {
        "simulations": simulations,
        "trade_count": int(len(pnls)),
        "positive_pct": positive_pct,
        "median_return": float(np.median(final_returns)),
        "p5_return": float(np.percentile(final_returns, 5)),
        "p95_return": float(np.percentile(final_returns, 95)),
        "worst_drawdown_p95": float(np.percentile(max_drawdowns, 95)),
        "passed": bool(positive_pct >= 0.65 and len(pnls) >= 10),
        "verdict": _mc_verdict(positive_pct, len(pnls)),
    }


def _mc_verdict(positive_pct: float, n: int) -> str:
    if n < 10:
        return "Mẫu quá nhỏ — cần ≥10 lệnh để tin Monte Carlo"
    if positive_pct >= 0.75:
        return "Phân phối return ổn định (≥75% mô phỏng dương)"
    if positive_pct >= 0.55:
        return "Trung bình — edge có nhưng không chắc chắn"
    return "Yếu — nhiều mô phỏng âm, cẩn trọng khi live"


def monthly_breakdown(trades: list, equity: float) -> list[dict[str, Any]]:
    if not trades:
        return []

    by_month: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        entry = t.entry_time if hasattr(t, "entry_time") else t.get("entry_time")
        pnl = t.pnl if hasattr(t, "pnl") else t.get("pnl", 0)
        if not entry:
            continue
        month = str(pd.Timestamp(entry).to_period("M"))
        by_month[month].append(float(pnl))

    rows = []
    for month in sorted(by_month.keys()):
        pnls = by_month[month]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        gp = sum(wins)
        gl = abs(sum(losses))
        rows.append({
            "Tháng": month,
            "Lệnh": len(pnls),
            "WR": f"{len(wins) / len(pnls):.0%}" if pnls else "—",
            "PnL": round(sum(pnls), 2),
            "Return": f"{sum(pnls) / equity:+.1%}",
            "PF": round(gp / gl, 2) if gl else "—",
            "Âm": "✓" if sum(pnls) < 0 else "",
        })
    return rows


def quarterly_breakdown(trades: list, equity: float) -> list[dict[str, Any]]:
    if not trades:
        return []

    by_q: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        entry = t.entry_time if hasattr(t, "entry_time") else t.get("entry_time")
        pnl = t.pnl if hasattr(t, "pnl") else t.get("pnl", 0)
        if not entry:
            continue
        q = str(pd.Timestamp(entry).to_period("Q"))
        by_q[q].append(float(pnl))

    rows = []
    for q in sorted(by_q.keys()):
        pnls = by_q[q]
        wins = [p for p in pnls if p > 0]
        rows.append({
            "Quý": q,
            "Lệnh": len(pnls),
            "WR": f"{len(wins) / len(pnls):.0%}" if pnls else "—",
            "PnL": round(sum(pnls), 2),
            "Return": f"{sum(pnls) / equity:+.1%}",
        })
    return rows


def monthly_stability_score(trades: list) -> float:
    """Tỷ lệ tháng có PnL dương."""
    months = monthly_breakdown(trades, 1000.0)
    if not months:
        return 0.0
    positive = sum(1 for m in months if float(m["PnL"]) > 0)
    return positive / len(months)


def stress_spread_comparison(
    years: list[int],
    equity: float = 1000.0,
    sl_pct: float = 0.02,
    min_rr: float = 2.0,
    spreads: list[float] | None = None,
) -> list[dict[str, Any]]:
    spreads = spreads or [0.5, 1.0, 1.5]
    params = locked_params()
    rows = []
    for spread in spreads:
        total_ret = 0.0
        total_trades = 0
        for year in years:
            r = run_year_backtest(
                year, params, equity, sl_pct, min_rr,
                spread_pips=spread,
            )
            total_ret += r.metrics.get("total_return", 0)
            total_trades += r.metrics.get("trade_count", 0)
        rows.append({
            "Spread (pip)": spread,
            "Tổng lệnh": total_trades,
            "Tổng return": f"{total_ret:+.1%}",
            "Avg/năm": f"{total_ret / len(years):+.1%}" if years else "—",
        })
    return rows


def collect_oos_trades(years: list[int] | None = None, equity: float = 1000.0) -> list:
    years = years or [2023, 2024, 2025]
    params = locked_params()
    trades = []
    for year in years:
        r = run_year_backtest(year, params, equity)
        trades.extend(r.trades)
    return trades
