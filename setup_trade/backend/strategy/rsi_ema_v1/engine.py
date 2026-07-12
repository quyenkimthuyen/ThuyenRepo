from __future__ import annotations

from typing import Any

import pandas as pd

from backend.strategy.rsi_ema_v1.config import load_strategy_config
from backend.strategy.rsi_ema_v1.detector import classify_for_direction, detect_at_bar


class RsiEmaV1Strategy:
    strategy_id = "rsi_ema_v1"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = load_strategy_config(config)

    def detect_at(self, df: pd.DataFrame, i: int) -> dict[str, Any] | None:
        return detect_at_bar(df, i, self.config)

    def detect_at_time(self, df: pd.DataFrame, entry_time: pd.Timestamp) -> dict[str, Any] | None:
        if entry_time.tz is None:
            entry_time = entry_time.tz_localize("UTC")
        else:
            entry_time = entry_time.tz_convert("UTC")
        if entry_time not in df.index:
            loc = df.index.get_indexer([entry_time], method="nearest")
            if loc[0] < 0:
                return None
            i = int(loc[0])
        else:
            i = int(df.index.get_loc(entry_time))
        return self.detect_at(df, i)

    def validate_label(
        self,
        df: pd.DataFrame,
        entry_time: pd.Timestamp,
        direction: str,
        setup_id: str | None = None,
    ) -> dict[str, Any]:
        detected = self.detect_at_time(df, entry_time)
        if not detected:
            return {
                "valid": False,
                "reason": "State machine không khớp tại thời điểm entry",
                "detected": None,
            }
        if detected["direction"] != direction:
            return {
                "valid": False,
                "reason": f"Hướng lệch: rule={detected['direction']}, label={direction}",
                "detected": detected,
            }
        if setup_id and detected["setup_id"] != setup_id:
            return {
                "valid": False,
                "reason": f"Setup lệch: rule={detected['setup_id']}, label={setup_id}",
                "detected": detected,
            }
        return {"valid": True, "reason": "OK", "detected": detected}

    def scan_period(
        self,
        df: pd.DataFrame,
        *,
        cooldown_bars: int | None = None,
    ) -> list[dict[str, Any]]:
        cooldown = cooldown_bars if cooldown_bars is not None else int(self.config.get("entry_cooldown_bars", 24))
        signals: list[dict[str, Any]] = []
        last_i = -cooldown - 1
        for i in range(2, len(df)):
            if i - last_i <= cooldown:
                continue
            hit = self.detect_at(df, i)
            if hit:
                signals.append(hit)
                last_i = i
        return signals
