from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from backend.core.folds import list_folds
from backend.reports.html_report import render_backtest_html
from backend.research.analyze import analyze_period
from backend.research.fold import run_fold_step
from backend.research.optimize import optimize_period
from backend.core.folds import require_final_test_period, require_optimize_period
from backend.data.loader import load_candles, slice_period
from backend.indicators import add_indicators
from backend.simulator.backtest import run_backtest

router = APIRouter()


@router.get("/folds")
def get_folds() -> dict:
    return {"folds": list_folds()}


@router.post("/fold/{fold_id}/{step}")
def fold_step(
    fold_id: str,
    step: str,
    max_add: int = Query(50, ge=1, le=100),
    apply_disable: bool = Query(False),
    method: str = Query("greedy"),
    save_best: bool = Query(True),
) -> dict:
    try:
        return run_fold_step(
            fold_id,
            step,
            max_add=max_add,
            apply_disable=apply_disable,
            method=method,
            save_best=save_best,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/analyze/full")
def analyze_full(
    period: str = Query(...),
    apply_disable: bool = Query(False),
) -> dict:
    try:
        return analyze_period(period, apply_disable=apply_disable)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/optimize")
def run_optimize(
    period: str = Query(...),
    method: str = Query("greedy"),
    save_best: bool = Query(True),
) -> dict:
    require_optimize_period(period)
    return optimize_period(period, method=method, save_best=save_best)


@router.get("/backtest/report")
def backtest_report(period: str = Query(...)) -> HTMLResponse:
    require_final_test_period(period)
    df = add_indicators(slice_period(load_candles(), period))
    result = run_backtest(df, period)
    html = render_backtest_html(result, title=f"Backtest — {period}")
    return HTMLResponse(html)
