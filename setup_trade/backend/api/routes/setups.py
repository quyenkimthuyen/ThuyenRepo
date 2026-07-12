from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.data.labels import create_setup, delete_setup, list_setups
from backend.indicators import add_indicators
from backend.data.loader import load_candles, slice_period
from backend.research.analyze import analyze_alignment, analyze_period
from backend.strategy.rsi_ema_v1.engine import RsiEmaV1Strategy

router = APIRouter()


class SetupIn(BaseModel):
    direction: str
    entry_time: str
    label_period: str
    setup_id: str | None = None
    note: str = ""
    discretionary_override: bool = False


class ValidateIn(BaseModel):
    direction: str
    entry_time: str
    label_period: str
    setup_id: str | None = None


@router.get("/setups")
def get_setups(period: str | None = None) -> dict:
    return {"setups": list_setups(period=period)}


@router.post("/setups/validate")
def validate_setup(body: ValidateIn) -> dict:
    df = add_indicators(slice_period(load_candles(), body.label_period))
    strategy = RsiEmaV1Strategy()
    import pandas as pd

    gate = strategy.validate_label(
        df,
        pd.Timestamp(body.entry_time),
        body.direction,
        body.setup_id,
    )
    return gate


@router.post("/setups")
def post_setup(body: SetupIn) -> dict:
    try:
        setup = create_setup(
            direction=body.direction,
            entry_time=body.entry_time,
            label_period=body.label_period,
            setup_id=body.setup_id,
            note=body.note,
            discretionary_override=body.discretionary_override,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return setup


@router.delete("/setups/{setup_id}")
def remove_setup(setup_id: str) -> dict:
    if not delete_setup(setup_id):
        raise HTTPException(404, "Setup not found")
    return {"deleted": setup_id}


@router.get("/analyze")
def analyze(period: str, full: bool = False, apply_disable: bool = False) -> dict:
    if full:
        return analyze_period(period, apply_disable=apply_disable)
    return analyze_alignment(period)
