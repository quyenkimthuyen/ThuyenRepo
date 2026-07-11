"""Registry chiến lược — dispatch analyze / backtest / label theo strategy_id."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from .config import ROOT

CATALOG_PATH = ROOT / "config" / "strategies.json"


class StrategyModule(Protocol):
    def detect_entry_at_bar(
        self, df: pd.DataFrame, i: int, strategy: dict[str, Any]
    ) -> tuple[str | None, str | None, dict[str, Any] | None]: ...

    def infer_setup_tags_for_label(
        self, df: pd.DataFrame, i: int, direction: str, strategy: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...

    def build_strategy(self, train_period: str, *, train_stats: dict[str, Any] | None = None) -> dict[str, Any]: ...

    def strategy_description(self) -> list[dict[str, str]]: ...


def load_catalog() -> dict[str, Any]:
    if CATALOG_PATH.exists():
        return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return {"strategies": [], "default_strategy_id": "rsi_h4_zone"}


def list_strategy_types() -> list[dict[str, Any]]:
    return load_catalog().get("strategies") or []


def default_strategy_id() -> str:
    return load_catalog().get("default_strategy_id") or "rsi_h4_zone"


def resolve_strategy_id(strategy_or_id: dict[str, Any] | str | None) -> str:
    if isinstance(strategy_or_id, dict):
        return (
            strategy_or_id.get("strategy_id")
            or strategy_or_id.get("name")
            or strategy_or_id.get("rule_mode")
            or default_strategy_id()
        )
    if isinstance(strategy_or_id, str) and strategy_or_id:
        return strategy_or_id
    return default_strategy_id()


def get_module(strategy_id: str | None = None):
    sid = resolve_strategy_id(strategy_id)
    if sid in ("rsi_h4", "rsi_h4_band"):
        from . import rsi_h4_strategy as mod

        return mod
    if sid == "ema_cross":
        from . import ema_cross_strategy as mod

        return mod
    if sid == "rsi_h4_zone":
        from . import rsi_h4_zone_strategy as mod

        return mod

    from . import rsi_h4_zone_strategy as mod

    return mod


def detect_entry(
    df: pd.DataFrame, i: int, strategy: dict[str, Any]
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    return get_module(strategy).detect_entry_at_bar(df, i, strategy)


def infer_setup_tags(
    df: pd.DataFrame, i: int, direction: str, strategy: dict[str, Any] | None = None
) -> dict[str, Any]:
    mod = get_module(strategy)
    return mod.infer_setup_tags_for_label(df, i, direction, strategy)


def build_strategy(
    strategy_id: str, train_period: str, *, train_stats: dict[str, Any] | None = None
) -> dict[str, Any]:
    strat = get_module(strategy_id).build_strategy(train_period, train_stats=train_stats)
    strat["strategy_id"] = resolve_strategy_id(strategy_id)
    return strat


def strategy_description(strategy_id: str | None = None) -> list[dict[str, str]]:
    return get_module(strategy_id).strategy_description()


def dist_ema_pips(row: pd.Series, strategy: dict[str, Any] | None = None):
    return get_module(strategy).dist_ema_pips(row)


def simulate_trade(
    df: pd.DataFrame,
    i: int,
    direction: str,
    strategy: dict[str, Any],
    cost: float,
    *,
    match_meta: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    mode = strategy.get("rule_mode")
    if mode == "ema_cross":
        from . import ema_cross_strategy as mod

        return mod.simulate_trade(df, i, direction, strategy, cost)
    if mode in ("rsi_h4_zone", "rsi_h4"):
        if mode == "rsi_h4_zone":
            from . import rsi_h4_zone_strategy as mod

            return mod.simulate_trade(df, i, direction, strategy, cost)
        from .backtest import _simulate_trade_rsi_h4

        return _simulate_trade_rsi_h4(
            df, i, direction, strategy, cost, setup_type=(match_meta or {}).get("setup_type")
        )
    return None


def rule_mode_for(strategy_id: str) -> str:
    for item in list_strategy_types():
        if item.get("id") == strategy_id:
            return item.get("rule_mode") or strategy_id
    return strategy_id
