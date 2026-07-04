"""Services cho UI — backtest, optimize, load config."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from systemtrain.config import Config
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.optimize.rolling_year import metrics_in_window, slice_year
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.orchestrator.rolling_production import (
    ACTIVE_PATH,
    backtest_trade_year,
    build_engines_from_state,
    current_trade_year,
    ensure_active_state,
    fill_missing_strategies,
    load_active_state,
    optimize_for_trade_year,
    save_active_state,
    state_from_fixed,
    train_year_for,
)
from systemtrain.ui.meta import STRATEGIES


def load_price_data() -> pd.DataFrame:
    config = Config.load()
    return to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")


def get_rolling_state(trade_year: int | None = None) -> dict[str, Any]:
    trade_year = trade_year or current_trade_year()
    state = load_active_state()
    if state and state.get("trade_year") == trade_year:
        return fill_missing_strategies(state)
    return ensure_active_state(trade_year)


def merge_params(state: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Ghi đè param từ UI vào bản copy state."""
    import copy
    out = copy.deepcopy(state)
    for sname, params in overrides.items():
        if sname in out.get("strategies", {}):
            out["strategies"][sname]["params"] = {**out["strategies"][sname]["params"], **params}
    return out


def run_strategy_backtest(
    strategy: str,
    state: dict[str, Any],
    year: int,
    equity: float = 1000.0,
) -> tuple[dict[str, Any], list, pd.DataFrame]:
    config = Config.load()
    df_1h = load_price_data()
    period_df, ts, te = slice_year(df_1h, year)
    engines = dict(build_engines_from_state(state, config, equity))
    engine = engines[strategy]
    result = engine.run(period_df)
    closed = [t for t in result.trades if t.is_closed and ts <= t.entry_time <= te]
    metrics = metrics_in_window(result, ts, te, equity)
    return metrics, closed, period_df


def run_all_backtest(state: dict[str, Any], year: int, equity: float = 1000.0) -> dict[str, Any]:
    config = Config.load()
    df_1h = load_price_data()
    fake = {**state, "trade_year": year}
    period_df, ts, te = slice_year(df_1h, year)
    out: dict[str, Any] = {"year": year, "strategies": {}, "combined": 0.0}
    for sname, engine in build_engines_from_state(fake, config, equity):
        m = metrics_in_window(engine.run(period_df), ts, te, equity)
        out["strategies"][sname] = m
        out["combined"] += m.get("total_return", 0)
    return out


def run_all_strategies_backtest(
    state: dict[str, Any],
    year: int,
    equity: float = 1000.0,
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame]:
    """Backtest tất cả chiến lược — trả về metrics + trades từng CL."""
    config = Config.load()
    df_1h = load_price_data()
    fake = {**state, "trade_year": year}
    period_df, ts, te = slice_year(df_1h, year)
    out: dict[str, dict[str, Any]] = {}
    for sname, engine in build_engines_from_state(fake, config, equity):
        result = engine.run(period_df)
        closed = [t for t in result.trades if t.is_closed and ts <= t.entry_time <= te]
        metrics = metrics_in_window(result, ts, te, equity)
        out[sname] = {"metrics": metrics, "trades": closed}
    return out, period_df


def optimize_trade_year(trade_year: int, equity: float = 1000.0) -> dict[str, Any]:
    state = optimize_for_trade_year(trade_year, equity=equity)
    save_active_state(state)
    return state


def load_base_yaml(strategy: str) -> dict[str, Any]:
    path = STRATEGIES[strategy]["base_config"]
    raw = yaml.safe_load(Path(path).read_text()) or {}
    key = list(raw.keys())[0] if len(raw) == 1 else strategy
    return raw.get(key, raw)


def load_history_years() -> list[int]:
    hist = Path("config/rolling/history")
    if not hist.exists():
        return []
    years = []
    for p in hist.glob("*.yaml"):
        try:
            years.append(int(p.stem))
        except ValueError:
            pass
    return sorted(years)


def load_history_year(year: int) -> dict[str, Any] | None:
    p = Path(f"config/rolling/history/{year}.yaml")
    if not p.exists():
        return None
    state = yaml.safe_load(p.read_text())
    return fill_missing_strategies(state) if state else None


def save_params_to_active(state: dict[str, Any]) -> None:
    save_active_state(state)
