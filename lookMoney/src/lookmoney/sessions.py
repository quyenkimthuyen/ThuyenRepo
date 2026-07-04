"""Trading session filters for London and New York (UTC)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd


@dataclass(frozen=True)
class SessionWindow:
    name: str
    start_utc: int
    end_utc: int

    def contains_hour(self, hour: int) -> bool:
        if self.start_utc <= self.end_utc:
            return self.start_utc <= hour < self.end_utc
        return hour >= self.start_utc or hour < self.end_utc


def load_sessions(config: dict) -> list[SessionWindow]:
    raw = config.get("sessions", {})
    return [
        SessionWindow(name=name, start_utc=s["start_utc"], end_utc=s["end_utc"])
        for name, s in raw.items()
    ]


def in_trading_session(
    ts: pd.Timestamp,
    sessions: Sequence[SessionWindow],
    *,
    weekdays_only: bool = True,
) -> bool:
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")

    if weekdays_only and ts.weekday() >= 5:
        return False

    hour = ts.hour
    return any(s.contains_hour(hour) for s in sessions)


def filter_session_bars(df: pd.DataFrame, sessions: Sequence[SessionWindow]) -> pd.DataFrame:
    if df.empty:
        return df
    mask = df.index.to_series().apply(lambda ts: in_trading_session(ts, sessions))
    return df.loc[mask]
