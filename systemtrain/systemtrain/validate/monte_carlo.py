from __future__ import annotations

import numpy as np

from systemtrain.backtest.engine import Trade


def run_monte_carlo(
    trades: list[Trade],
    initial_equity: float,
    simulations: int = 500,
    seed: int = 42,
) -> dict:
    if not trades:
        return {"positive_pct": 0.0, "median_return": 0.0, "passed": False}

    pnls = np.array([t.pnl for t in trades if t.is_closed])
    if len(pnls) == 0:
        return {"positive_pct": 0.0, "median_return": 0.0, "passed": False}

    rng = np.random.default_rng(seed)
    final_returns = []

    for _ in range(simulations):
        shuffled = rng.permutation(pnls)
        equity = initial_equity
        for pnl in shuffled:
            equity += pnl
        final_returns.append(equity / initial_equity - 1)

    final_returns = np.array(final_returns)
    positive_pct = (final_returns > 0).mean()

    return {
        "positive_pct": float(positive_pct),
        "median_return": float(np.median(final_returns)),
        "p5_return": float(np.percentile(final_returns, 5)),
        "p95_return": float(np.percentile(final_returns, 95)),
        "simulations": simulations,
        "passed": bool(positive_pct >= 0.70),
    }
