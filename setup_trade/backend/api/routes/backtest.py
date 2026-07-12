from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.core.config import STRATEGY_PATH, load_json
from backend.data.loader import load_candles, slice_period
from backend.indicators import add_indicators
from backend.simulator.backtest import run_backtest
from backend.core.folds import require_final_test_period, require_optimize_period

router = APIRouter()


@router.get("/strategy")
def get_strategy() -> dict:
    return load_json(STRATEGY_PATH)


@router.post("/backtest/explore")
def backtest_explore(period: str = Query(...)) -> dict:
    """Backtest trên optimize_period — dùng khi tune, không phải final test."""
    require_optimize_period(period)
    df = add_indicators(slice_period(load_candles(), period))
    return run_backtest(df, period)


@router.post("/backtest")
def backtest(period: str = Query(...)) -> dict:
    require_final_test_period(period)
    df = add_indicators(slice_period(load_candles(), period))
    return run_backtest(df, period)
