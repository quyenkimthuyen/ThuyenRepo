from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.core.periods import period_bounds
from backend.data.loader import candles_to_records, load_candles, slice_period
from backend.indicators import add_indicators

router = APIRouter()


@router.get("/candles")
def get_candles(
    period: str = Query("bt_2023"),
    limit: int | None = Query(None, ge=1, le=50000),
) -> dict:
    try:
        df = add_indicators(slice_period(load_candles(), period))
    except KeyError as exc:
        raise HTTPException(404, f"Unknown period: {period}") from exc
    if limit:
        df = df.iloc[-limit:]
    start, end = period_bounds(period)
    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "count": len(df),
        "candles": candles_to_records(df),
    }
