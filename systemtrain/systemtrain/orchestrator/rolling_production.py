"""Production rolling — tối ưu 1 năm trước, trade năm hiện tại."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from systemtrain.config import Config
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.optimize.rolling_year import (
    build_ema_engine,
    build_pin_engine,
    build_rsi_engine,
    build_wyckoff_engine,
    fixed_params,
    metrics_in_window,
    optimize_ema_year,
    optimize_pin_year,
    optimize_rsi_year,
    optimize_wyckoff_year,
    slice_year,
    year_bounds,
)
from systemtrain.orchestrator.pipeline import TrainingPipeline

ROLLING_DIR = Path("config/rolling")
ACTIVE_PATH = ROLLING_DIR / "active.yaml"
HISTORY_DIR = ROLLING_DIR / "history"

STRATEGY_OPTIMIZERS = [
    ("Wyckoff", optimize_wyckoff_year, build_wyckoff_engine),
    ("RSI Divergence", optimize_rsi_year, build_rsi_engine),
    ("EMA 50/200", optimize_ema_year, build_ema_engine),
    ("Pin Bar Elite", optimize_pin_year, build_pin_engine),
]


def fill_missing_strategies(state: dict[str, Any]) -> dict[str, Any]:
    """Bổ sung chiến lược mới vào state cũ (vd. Pin Bar thêm sau)."""
    fp = fixed_params()
    strategies = state.setdefault("strategies", {})
    for name, params in fp.items():
        if name not in strategies:
            strategies[name] = {"params": params, "train": {}}
    return state


def current_trade_year(as_of: datetime | None = None) -> int:
    """Năm calendar đang trade (dùng năm hiện tại)."""
    dt = as_of or datetime.now(timezone.utc)
    return dt.year


def train_year_for(trade_year: int) -> int:
    return trade_year - 1


def load_active_state() -> dict[str, Any] | None:
    if not ACTIVE_PATH.exists():
        return None
    state = yaml.safe_load(ACTIVE_PATH.read_text()) or None
    return fill_missing_strategies(state) if state else None


def _native(obj: Any) -> Any:
    """Chuyển numpy scalar → Python native cho YAML/JSON."""
    if isinstance(obj, dict):
        return {k: _native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_native(v) for v in obj]
    if hasattr(obj, "item"):
        return obj.item()
    return obj


def save_active_state(state: dict[str, Any]) -> Path:
    ROLLING_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    clean = _native(state)
    trade_year = clean["trade_year"]
    ACTIVE_PATH.write_text(yaml.dump(clean, default_flow_style=False, allow_unicode=True, sort_keys=False))
    hist = HISTORY_DIR / f"{trade_year}.yaml"
    hist.write_text(yaml.dump(clean, default_flow_style=False, allow_unicode=True, sort_keys=False))
    json_path = Path("output/rolling_active.json")
    json_path.parent.mkdir(exist_ok=True)
    json_path.write_text(json.dumps(clean, indent=2, default=str))
    return ACTIVE_PATH


def optimize_for_trade_year(
    trade_year: int,
    config: Config | None = None,
    equity: float = 1000.0,
    df_1h: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Grid-search trên năm train_year → lưu param cho trade_year."""
    config = config or Config.load()
    if df_1h is None:
        df_1h = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")

    ty = train_year_for(trade_year)
    train_df, train_s, train_e = slice_year(df_1h, ty)

    state: dict[str, Any] = {
        "trade_year": trade_year,
        "train_year": ty,
        "optimized_at": datetime.now(timezone.utc).isoformat(),
        "equity": equity,
        "strategies": {},
    }

    for sname, opt_fn, _ in STRATEGY_OPTIMIZERS:
        params, train_m = opt_fn(train_df, train_s, train_e, config, equity)
        state["strategies"][sname] = {
            "params": params,
            "train": train_m,
        }

    return state


def state_from_fixed(trade_year: int, equity: float = 1000.0) -> dict[str, Any]:
    """Fallback: config yaml cố định (không optimize)."""
    fp = fixed_params()
    return {
        "trade_year": trade_year,
        "train_year": train_year - 1,
        "optimized_at": datetime.now(timezone.utc).isoformat(),
        "equity": equity,
        "mode": "fixed",
        "strategies": {name: {"params": p, "train": {}} for name, p in fp.items()},
    }


def build_engines_from_state(state: dict[str, Any], config: Config, equity: float) -> list[tuple[str, Any]]:
    state = fill_missing_strategies(state)
    builders = {
        "Wyckoff": build_wyckoff_engine,
        "RSI Divergence": build_rsi_engine,
        "EMA 50/200": build_ema_engine,
        "Pin Bar Elite": build_pin_engine,
    }
    engines = []
    for sname, builder in builders.items():
        params = state["strategies"][sname]["params"]
        engines.append((sname, builder(params, config, equity)))
    return engines


def backtest_trade_year(
    state: dict[str, Any],
    config: Config,
    equity: float,
    df_1h: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Backtest năm trade với param đã optimize."""
    trade_year = state["trade_year"]
    if df_1h is None:
        df_1h = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")

    trade_df, trade_s, trade_e = slice_year(df_1h, trade_year)
    results: dict[str, Any] = {
        "trade_year": trade_year,
        "period": year_bounds(trade_year),
        "strategies": {},
    }
    total_ret = 0.0

    for sname, engine in build_engines_from_state(state, config, equity):
        m = metrics_in_window(engine.run(trade_df), trade_s, trade_e, equity)
        results["strategies"][sname] = m
        total_ret += m.get("total_return", 0)

    results["combined_return"] = total_ret
    return results


def ensure_active_state(
    trade_year: int | None = None,
    force_remine: bool = False,
    equity: float = 1000.0,
) -> dict[str, Any]:
    """Load active state; re-mine nếu thiếu hoặc trade_year đổi hoặc --remine."""
    trade_year = trade_year or current_trade_year()
    existing = load_active_state()

    if not force_remine and existing and existing.get("trade_year") == trade_year:
        return existing

    state = optimize_for_trade_year(trade_year, equity=equity)
    save_active_state(state)
    return state
