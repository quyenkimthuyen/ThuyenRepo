#!/usr/bin/env python3
"""Seed a few synthetic train setups for pipeline smoke test."""

from backend.labels import create_setup

SAMPLES = [
    {
        "direction": "long",
        "entry_time": "2022-03-15T12:00:00+00:00",
        "entry_price": 1.0950,
        "stop_loss": 1.0920,
        "take_profit": 1.1010,
        "note": "pullback ema50",
    },
    {
        "direction": "long",
        "entry_time": "2022-06-10T08:00:00+00:00",
        "entry_price": 1.0600,
        "stop_loss": 1.0570,
        "take_profit": 1.0660,
        "note": "trend continuation",
    },
    {
        "direction": "short",
        "entry_time": "2022-09-20T14:00:00+00:00",
        "entry_price": 1.0100,
        "stop_loss": 1.0130,
        "take_profit": 1.0040,
        "note": "rejection",
    },
    {
        "direction": "long",
        "entry_time": "2022-11-05T10:00:00+00:00",
        "entry_price": 1.0200,
        "stop_loss": 1.0170,
        "take_profit": 1.0260,
        "note": "breakout retest",
    },
    {
        "direction": "short",
        "entry_time": "2022-04-12T16:00:00+00:00",
        "entry_price": 1.0900,
        "stop_loss": 1.0930,
        "take_profit": 1.0840,
        "note": "lower high",
    },
    {
        "direction": "long",
        "entry_time": "2022-07-22T11:00:00+00:00",
        "entry_price": 1.0250,
        "stop_loss": 1.0220,
        "take_profit": 1.0310,
        "note": "ema bounce",
    },
]

if __name__ == "__main__":
    for s in SAMPLES:
        out = create_setup(s)
        print(out["id"], out["direction"], out["result"], out.get("planned_rr"))
