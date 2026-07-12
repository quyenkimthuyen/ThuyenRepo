"""RSI Zone Analyzer — EURUSD H1 + RSI H4."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_service import build_chart_payload, data_info, filter_range, load_candles
from .zone_stats import ZoneConfig, analyze_zone_touches

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="RSI Zone Analyzer", version="1.0.0")


@app.get("/api/info")
def api_info():
    return data_info()


@app.get("/api/chart")
def api_chart(
    start: str | None = Query(None, description="YYYY-MM-DD"),
    end: str | None = Query(None, description="YYYY-MM-DD"),
):
    df = filter_range(load_candles(), start, end)
    return build_chart_payload(df)


@app.get("/api/zone-stats")
def api_zone_stats(
    start: str | None = Query(None),
    end: str | None = Query(None),
    horizon_bars: int = Query(24, ge=4, le=168),
    min_reversal_pips: float = Query(20.0, ge=5, le=100),
    cooldown_bars: int = Query(12, ge=1, le=72),
):
    df = filter_range(load_candles(), start, end)
    cfg = ZoneConfig(horizon_bars=horizon_bars, min_reversal_pips=min_reversal_pips, cooldown_bars=cooldown_bars)
    return analyze_zone_touches(df, cfg)


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
