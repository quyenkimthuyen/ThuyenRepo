"""Generic trade signal for rule-based strategies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradeSignal:
    signal_bar: int
    entry_bar: int
    direction: int  # 1 long, -1 short
    sl_price: float
    tag: str = ""
