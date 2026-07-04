"""Strategy module resolution from config."""

from __future__ import annotations

from types import ModuleType


_H4_NAMES = frozenset({"h4_native", "eur_h4_pullback", "h4_pullback_native"})


def resolve_strategy(config: dict) -> ModuleType:
    name = config.get("strategy", {}).get("name", "h4_pullback")
    if name in _H4_NAMES or config.get("timeframe", "H1").upper() == "H4":
        from lookmoney.strategies import eur_usd_h4

        return eur_usd_h4
    from lookmoney.strategies import eur_usd_h1

    return eur_usd_h1
