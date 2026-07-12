from __future__ import annotations

from typing import Any

from backend.core.config import STRATEGY_PATH, load_json


def load_strategy_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_json(STRATEGY_PATH)
    if overrides:
        for key, val in overrides.items():
            if isinstance(cfg.get(key), dict) and isinstance(val, dict):
                cfg[key] = {**cfg[key], **val}
            else:
                cfg[key] = val
    return cfg


def band(cfg: dict[str, Any], name: str) -> tuple[float, float]:
    raw = cfg["bands"][name]
    return float(raw[0]), float(raw[1])


def in_band(value: float, b: tuple[float, float]) -> bool:
    return b[0] <= value <= b[1]


def above_band(value: float, b: tuple[float, float]) -> bool:
    return value > b[1]


def below_band(value: float, b: tuple[float, float]) -> bool:
    return value < b[0]
