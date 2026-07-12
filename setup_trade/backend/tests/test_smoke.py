from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.data.loader import load_candles, slice_period
from backend.indicators import add_indicators
from backend.indicators.rsi import rsi
from backend.indicators.rsi_h4 import add_h4_rsi_closed_only, h4_ohlc
from backend.strategy.rsi_ema_v1.detector import setup1_long
from backend.simulator.trade import simulate_trade


@pytest.fixture(scope="session")
def candles_df() -> pd.DataFrame:
    return add_indicators(load_candles())


@pytest.fixture
def sample_h4_rsi() -> pd.Series:
  """10 H4 closes → RSI reference."""
  closes = pd.Series(
      [1.10, 1.101, 1.099, 1.102, 1.103, 1.101, 1.104, 1.105, 1.103, 1.106,
       1.107, 1.108, 1.106, 1.109, 1.11],
      index=pd.date_range("2022-01-03 00:00", periods=15, freq="4h", tz="UTC"),
  )
  return rsi(closes, 14)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["walk_forward_valid"] is True


def test_load_candles(candles_df):
    assert len(candles_df) > 1000
    assert "close" in candles_df.columns


def test_h4_rsi_sanity(candles_df):
    raw = candles_df.dropna(subset=["rsi14_h4"])
    assert len(raw) > 100
    assert raw["rsi14_h4"].between(0, 100).all()


def test_h4_rsi_manual_sample(sample_h4_rsi):
    assert len(sample_h4_rsi.dropna()) >= 1
    last = float(sample_h4_rsi.dropna().iloc[-1])
    assert 0 <= last <= 100


def test_periods_no_overlap():
    from backend.core.periods import validate_all_folds

    errors = validate_all_folds()
    assert all(not v for v in errors.values())


def test_candles_api(client):
    r = client.get("/api/candles", params={"period": "bt_2023", "limit": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 50
    assert "rsi14_h4" in body["candles"][-1]


def test_setup1_long_fixture():
    """Given RSI path: break above 52 → retest 48-52 → bounce up."""
    mid = (48.0, 52.0)
    rsi_vals = np.array([
        50.0, 50.5, 51.0, 53.0, 54.0, 53.5, 52.0, 51.0, 50.0, 49.5,
        49.0, 49.5, 50.0, 50.5, 51.0,
    ])
    i = len(rsi_vals) - 1
    assert setup1_long(rsi_vals, i, mid, lookback=20, bounce_min=0.1)


def test_simulator_long_tp():
    """Synthetic bars: long should hit RSI TP band."""
    idx = pd.date_range("2022-06-01", periods=30, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": 1.05,
            "high": 1.052,
            "low": 1.0485,
            "close": 1.05,
            "volume": 0,
            "ema50": 1.049,
            "ema200": 1.048,
            "atr14": 0.001,
            "rsi14_h4": 55.0,
        },
        index=idx,
    )
    df.loc[idx[6:], "rsi14_h4"] = 69.0
    trade = simulate_trade(df, 5, "long", setup_id="s1_break_retest")
    assert trade is not None
    assert trade["exit_reason"] == "rsi_tp"
    assert trade["pnl_pips"] != 0


def test_backtest_runs(candles_df):
    from backend.simulator.backtest import run_backtest

    df = slice_period(candles_df, "bt_2023")
    result = run_backtest(df, "bt_2023")
    assert "metrics" in result
    assert "trades" in result["metrics"]
