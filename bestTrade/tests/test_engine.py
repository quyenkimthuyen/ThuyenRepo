"""Engine parity and module smoke tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_locked_params_match_config():
    from besttrade.params import locked_params, load_strategy_config

    cfg = load_strategy_config()
    assert locked_params() == cfg["params"]


def test_year_backtest_returns_trades():
    from besttrade.engine import run_year_backtest
    from besttrade.params import locked_params

    r = run_year_backtest(2024, locked_params(), equity=1000.0)
    assert "trade_count" in r.metrics
    assert r.year == 2024


def test_monte_carlo_on_oos():
    from besttrade.analytics import bootstrap_monte_carlo, collect_oos_trades

    trades = collect_oos_trades([2024], equity=1000.0)
    mc = bootstrap_monte_carlo(trades, 1000.0, simulations=100)
    assert "positive_pct" in mc
    assert "verdict" in mc


def test_paper_run_once():
    from besttrade.paper import run_paper_once

    result = run_paper_once(equity=1000.0, refresh_data=False)
    assert "state" in result
    assert "latest_bar" in result


if __name__ == "__main__":
    test_locked_params_match_config()
    test_year_backtest_returns_trades()
    test_monte_carlo_on_oos()
    test_paper_run_once()
    print("All tests passed.")
