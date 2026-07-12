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
    year: int
    metrics: dict[str, Any]
    trades: list
    period_df: pd.DataFrame


def load_strategy_config() -> dict[str, Any]:
    path = BESTTRADE_ROOT / "config" / "strategy.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def systemtrain_config(sl_pct: float | None = None, min_rr: float | None = None) -> Config:
    """Load SystemTrain config with data paths pointing to sibling project."""
    config_path = SYSTEMTRAIN_ROOT / "config" / "default.yaml"
    config = Config.load(config_path)
    config = copy.deepcopy(config)
    config.data["data_dir"] = str(SYSTEMTRAIN_ROOT / "data" / "store")
    if sl_pct is not None:
        config.risk["sl_pct"] = float(sl_pct)
    if min_rr is not None:
        config.risk["min_rr"] = float(min_rr)
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
) -> BacktestResult:
    cfg_doc = load_strategy_config()
    merged = {**cfg_doc["params"], **(params or {})}
    config = systemtrain_config(sl_pct, min_rr)
    with _systemtrain_cwd():
        df = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
        period_df, ts, te = slice_year(df, year)
        engine = build_pin_engine(merged, config, equity)
        result = engine.run(period_df)
    closed = [t for t in result.trades if t.is_closed and ts <= t.entry_time <= te]
    metrics = metrics_in_window(result, ts, te, equity)
    return BacktestResult(year=year, metrics=metrics, trades=closed, period_df=period_df)


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
