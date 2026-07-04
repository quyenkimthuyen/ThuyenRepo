from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class WalkForwardConfig:
    train_months: int = 6
    test_months: int = 2
    step_months: int = 2


@dataclass
class Config:
    symbol: str = "EURUSD"
    timeframe: str = "1h"
    entry_timeframe: str = "1h"
    htf_timeframe: str = "4h"
    pip_size: float = 0.0001
    data: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    backtest: dict[str, Any] = field(default_factory=dict)
    optimize: dict[str, Any] = field(default_factory=dict)
    fitness: dict[str, Any] = field(default_factory=dict)
    oos_gate: dict[str, Any] = field(default_factory=dict)
    monte_carlo: dict[str, Any] = field(default_factory=dict)

    @property
    def walk_forward(self) -> WalkForwardConfig:
        wf = self.optimize.get("walk_forward", {})
        return WalkForwardConfig(
            train_months=wf.get("train_months", 6),
            test_months=wf.get("test_months", 2),
            step_months=wf.get("step_months", 2),
        )

    @classmethod
    def load(cls, path: str | Path | None = None) -> Config:
        if path is None:
            path = Path(__file__).resolve().parent.parent / "config" / "default.yaml"
        path = Path(path)
        with path.open() as f:
            raw = yaml.safe_load(f)
        return cls(**raw)
