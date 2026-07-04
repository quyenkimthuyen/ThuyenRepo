from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_synthetic_eurusd(
    years: int = 3,
    bars_per_day: int = 96,
    seed: int = 42,
    start_price: float = 1.1000,
) -> pd.DataFrame:
    """Generate realistic synthetic EURUSD 15m OHLCV for pipeline testing."""
    rng = np.random.default_rng(seed)
    trading_days = 252 * years
    n_bars = trading_days * bars_per_day

    bar_vol = 0.05 / np.sqrt(252 * bars_per_day)
    returns = rng.normal(0, bar_vol, n_bars)

    for i in range(1, n_bars):
        hour = (i % bars_per_day) // 4
        session_mult = 1.4 if 8 <= hour <= 16 else 0.8
        returns[i] += -0.05 * returns[i - 1]
        returns[i] *= session_mult

    closes = start_price * np.exp(np.cumsum(returns))
    noise = rng.uniform(0.00005, 0.0003, n_bars)
    highs = closes + noise
    lows = closes - noise
    opens = np.roll(closes, 1)
    opens[0] = start_price
    volumes = rng.integers(100, 5000, n_bars)

    start = pd.Timestamp("2021-01-04 00:00:00", tz="UTC")
    index = pd.date_range(start, periods=n_bars, freq=pd.Timedelta(minutes=15))

    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum.reduce([opens, highs, closes]),
            "low": np.minimum.reduce([opens, lows, closes]),
            "close": closes,
            "volume": volumes,
        },
        index=index,
    )
