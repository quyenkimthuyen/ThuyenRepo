from __future__ import annotations

from enum import Enum


class SetupId(str, Enum):
    S1_BREAK_RETEST = "s1_break_retest"
    S2_EXTREME_BOUNCE = "s2_extreme_bounce"


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


class SignalState(str, Enum):
    IDLE = "idle"
    WATCHING = "watching"
    BREAKOUT = "breakout"
    RETEST = "retest"
    ENTRY_READY = "entry_ready"
    TOUCHED_EXTREME = "touched_extreme"
    PULLBACK_MID = "pullback_mid"
