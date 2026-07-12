from __future__ import annotations

from typing import Any, Protocol

import pandas as pd


class StrategyProtocol(Protocol):
  strategy_id: str

  def detect_at(self, df: pd.DataFrame, i: int) -> dict[str, Any] | None:
    ...

  def detect_at_time(self, df: pd.DataFrame, entry_time: pd.Timestamp) -> dict[str, Any] | None:
    ...
