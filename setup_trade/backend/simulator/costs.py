from __future__ import annotations

from backend.core.config import COSTS_PATH, PIP, load_json


def load_costs() -> dict:
    return load_json(COSTS_PATH)


def round_trip_cost_pips() -> float:
    c = load_costs()
    return float(c.get("spread_pips", 1.0)) + float(c.get("slippage_pips", 0.2))


def round_trip_cost_price() -> float:
    return round_trip_cost_pips() * PIP
