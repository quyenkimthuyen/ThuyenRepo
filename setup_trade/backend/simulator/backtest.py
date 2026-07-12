from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.core.config import PERIODS_PATH, load_json
from backend.simulator.trade import simulate_trade
from backend.strategy.rsi_ema_v1.engine import RsiEmaV1Strategy
from backend.reports.metrics import compute_metrics, monte_carlo_pf


def run_backtest(
    df: pd.DataFrame,
    period: str,
    *,
    strategy_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    strategy = RsiEmaV1Strategy(strategy_config)
    signals = strategy.scan_period(df)
    trades: list[dict[str, Any]] = []
    for sig in signals:
        i = sig["bar_index"]
        result = simulate_trade(
            df,
            i,
            sig["direction"],
            strategy_config=strategy.config,
            setup_id=sig["setup_id"],
        )
        if result:
            trades.append({**sig, **result})

    metrics = compute_metrics(trades)
    pass_cfg = load_json(PERIODS_PATH).get("pass_criteria") or {}
    mc = monte_carlo_pf(trades, iterations=int(pass_cfg.get("monte_carlo_iterations", 1000)))

    passed = (
        metrics["trades"] >= int(pass_cfg.get("min_trades", 30))
        and metrics["profit_factor"] >= float(pass_cfg.get("min_profit_factor", 1.3))
        and metrics["max_drawdown_pips"] <= float(pass_cfg.get("max_drawdown_pips", 250))
        and metrics["expectancy_pips"] > float(pass_cfg.get("min_expectancy_pips", 0))
        and mc["pf_p5"] >= float(pass_cfg.get("monte_carlo_pf_p5_min", 1.0))
    )

    return {
        "period": period,
        "strategy_id": strategy.strategy_id,
        "trades": trades,
        "metrics": metrics,
        "monte_carlo": mc,
        "pass": passed,
    }
