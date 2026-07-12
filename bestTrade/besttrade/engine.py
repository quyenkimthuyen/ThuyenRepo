"""Backtest engine — wraps SystemTrain Pin Bar Elite pipeline."""

from __future__ import annotations

import copy
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import yaml

from besttrade.paths import BESTTRADE_ROOT, SYSTEMTRAIN_ROOT, ensure_systemtrain_on_path

ensure_systemtrain_on_path()

from systemtrain.config import Config  # noqa: E402
from systemtrain.data.timeframes import to_entry_timeframe  # noqa: E402
from systemtrain.optimize.rolling_year import (  # noqa: E402
    build_pin_engine,
    metrics_in_window,
    slice_year,
)
from systemtrain.orchestrator.pipeline import TrainingPipeline  # noqa: E402


STRATEGY_NAME = "Pin Bar Elite"


@contextmanager
def _systemtrain_cwd() -> Iterator[None]:
    """SystemTrain uses relative paths for config/data — run from its root."""
    prev = os.getcwd()
    os.chdir(SYSTEMTRAIN_ROOT)
    try:
        yield
    finally:
        os.chdir(prev)


@dataclass
class BacktestResult:
    year: int | None
    metrics: dict[str, Any]
    trades: list
    period_df: pd.DataFrame
    period_start: pd.Timestamp | None = None
    period_end: pd.Timestamp | None = None


def load_strategy_config() -> dict[str, Any]:
    path = BESTTRADE_ROOT / "config" / "strategy.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def systemtrain_config(
    sl_pct: float | None = None,
    min_rr: float | None = None,
    spread_pips: float | None = None,
    slippage_pips: float | None = None,
) -> Config:
    """Load SystemTrain config with data paths pointing to sibling project."""
    config_path = SYSTEMTRAIN_ROOT / "config" / "default.yaml"
    config = Config.load(config_path)
    config = copy.deepcopy(config)
    config.data["data_dir"] = str(SYSTEMTRAIN_ROOT / "data" / "store")
    if sl_pct is not None:
        config.risk["sl_pct"] = float(sl_pct)
    if min_rr is not None:
        config.risk["min_rr"] = float(min_rr)
    if spread_pips is not None:
        config.backtest["spread_pips"] = float(spread_pips)
    if slippage_pips is not None:
        config.backtest["slippage_pips"] = float(slippage_pips)
    return config


def load_price_data() -> pd.DataFrame:
    with _systemtrain_cwd():
        config = systemtrain_config()
        return to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")


def run_year_backtest(
    year: int,
    params: dict[str, Any] | None = None,
    equity: float = 1000.0,
    sl_pct: float = 0.02,
    min_rr: float = 2.0,
    spread_pips: float | None = None,
    slippage_pips: float | None = None,
) -> BacktestResult:
    cfg_doc = load_strategy_config()
    merged = {**cfg_doc["params"], **(params or {})}
    config = systemtrain_config(sl_pct, min_rr, spread_pips, slippage_pips)
    with _systemtrain_cwd():
        df = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
        period_df, ts, te = slice_year(df, year)
        engine = build_pin_engine(merged, config, equity)
        result = engine.run(period_df)
    closed = [t for t in result.trades if t.is_closed and ts <= t.entry_time <= te]
    metrics = metrics_in_window(result, ts, te, equity)
    return BacktestResult(
        year=year, metrics=metrics, trades=closed, period_df=period_df,
        period_start=ts, period_end=te,
    )


def run_period_backtest(
    start: pd.Timestamp,
    end: pd.Timestamp,
    params: dict[str, Any] | None = None,
    equity: float = 1000.0,
    sl_pct: float = 0.02,
    min_rr: float = 2.0,
    spread_pips: float | None = None,
) -> BacktestResult:
    """Backtest arbitrary date range (for forward test comparison)."""
    cfg_doc = load_strategy_config()
    merged = {**cfg_doc["params"], **(params or {})}
    config = systemtrain_config(sl_pct, min_rr, spread_pips)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts.tzinfo is None:
        start_ts = start_ts.tz_localize("UTC")
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")

    with _systemtrain_cwd():
        df = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
        mask = (df.index >= start_ts) & (df.index <= end_ts)
        period_df = df.loc[mask].copy()
        if period_df.empty:
            return BacktestResult(
                year=None, metrics={"trade_count": 0, "win_rate": 0, "profit_factor": 0, "total_return": 0},
                trades=[], period_df=period_df, period_start=start_ts, period_end=end_ts,
            )
        engine = build_pin_engine(merged, config, equity)
        result = engine.run(period_df)
    closed = [t for t in result.trades if t.is_closed and start_ts <= t.entry_time <= end_ts]
    metrics = metrics_in_window(result, start_ts, end_ts, equity)
    return BacktestResult(
        year=None, metrics=metrics, trades=closed, period_df=period_df,
        period_start=start_ts, period_end=end_ts,
    )


def run_multi_year(
    years: list[int],
    params: dict[str, Any] | None = None,
    equity: float = 1000.0,
    sl_pct: float = 0.02,
    min_rr: float = 2.0,
) -> list[BacktestResult]:
    return [run_year_backtest(y, params, equity, sl_pct, min_rr) for y in years]


def equity_curve(trades: list, equity: float) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame({"time": [], "equity": []})
    rows = []
    bal = equity
    for t in sorted(trades, key=lambda x: x.exit_time or x.entry_time):
        bal += t.pnl
        rows.append({"time": t.exit_time or t.entry_time, "equity": bal})
    return pd.DataFrame(rows)
