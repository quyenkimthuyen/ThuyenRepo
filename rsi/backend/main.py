"""RSI Zone Analyzer — EURUSD H1 + RSI H4."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_service import build_chart_payload, data_info, filter_range, load_candles
from .setup_optimizer import build_recommended_report
from .zone_stats import ZoneConfig, analyze_zone_touches

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

app = FastAPI(title="RSI Zone Analyzer", version="1.0.0", docs_url="/api/swagger", redoc_url=None)


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
    horizon_bars: int = Query(48, ge=4, le=168),
    min_reversal_pips: float = Query(20.0, ge=5, le=100),
    cooldown_bars: int = Query(12, ge=1, le=72),
    exit_lookahead_bars: int = Query(48, ge=4, le=168),
    sl_mode: str = Query("fixed"),
    stop_loss_pips: float = Query(25.0, ge=5, le=100),
    stop_loss_atr_mult: float = Query(1.0, ge=0.5, le=5.0),
    take_profit_r: float = Query(2.5, ge=0.5, le=5.0),
    spread_pips: float = Query(1.0, ge=0, le=10),
):
    df = filter_range(load_candles(), start, end)
    cfg = ZoneConfig(
        horizon_bars=horizon_bars,
        min_reversal_pips=min_reversal_pips,
        cooldown_bars=cooldown_bars,
        exit_lookahead_bars=exit_lookahead_bars,
        sl_mode="atr" if sl_mode == "atr" else "fixed",
        stop_loss_pips=stop_loss_pips,
        stop_loss_atr_mult=stop_loss_atr_mult,
        take_profit_r=take_profit_r,
        spread_pips=spread_pips,
    )
    return analyze_zone_touches(df, cfg)


@app.get("/api/recommended-setup")
def api_recommended_setup(
    start: str | None = Query(None),
    end: str | None = Query(None),
    split_date: str = Query("2025-01-01"),
):
    df = filter_range(load_candles(), start, end)
    cfg = ZoneConfig(horizon_bars=48, stop_loss_pips=25.0, take_profit_r=2.5)
    report = build_recommended_report(df, cfg, split_date=split_date)
    return report


@app.get("/huong-dan")
def huong_dan():
    return FileResponse(FRONTEND / "docs.html")


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
