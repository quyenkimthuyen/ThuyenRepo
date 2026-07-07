from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analyzer import analyze_patterns, load_strategy
from .backtest import run_backtest
from .data_service import candles_to_records, load_candles, load_splits, slice_period
from .indicators import add_indicators
from .labels import create_setup, delete_setup, enrich_setup, load_setups, update_setup

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

app = FastAPI(title="AI Trade Lab", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetupIn(BaseModel):
    direction: str
    entry_time: str
    entry_price: float
    stop_loss: float
    take_profit: float
    tags: list[str] = Field(default_factory=list)
    note: str = ""


class SetupPatch(BaseModel):
    tags: list[str] | None = None
    note: str | None = None


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def get_config():
    return load_splits()


@app.get("/api/candles")
def get_candles(period: str = "train", with_indicators: bool = True):
    try:
        df = slice_period(load_candles(), period)
    except KeyError:
        raise HTTPException(400, f"Unknown period: {period}")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    if with_indicators:
        df = add_indicators(df)

    records = candles_to_records(df)
    indicators = None
    if with_indicators:
        indicators = {
            "ema50": [
                {"time": int(ts.timestamp()), "value": round(float(v), 5)}
                for ts, v in df["ema50"].dropna().items()
            ],
            "ema200": [
                {"time": int(ts.timestamp()), "value": round(float(v), 5)}
                for ts, v in df["ema200"].dropna().items()
            ],
            "rsi14": [
                {"time": int(ts.timestamp()), "value": round(float(v), 2)}
                for ts, v in df["rsi14"].dropna().items()
            ],
        }
    return {"period": period, "count": len(records), "candles": records, "indicators": indicators}


@app.get("/api/setups")
def list_setups():
    return {"setups": load_setups()}


@app.post("/api/setups")
def add_setup(body: SetupIn):
    try:
        return create_setup(body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/setups/{setup_id}")
def patch_setup(setup_id: str, body: SetupPatch):
    try:
        return update_setup(setup_id, body.model_dump(exclude_none=True))
    except KeyError:
        raise HTTPException(404, "Setup not found")


@app.delete("/api/setups/{setup_id}")
def remove_setup(setup_id: str):
    delete_setup(setup_id)
    return {"deleted": setup_id}


@app.post("/api/setups/refresh")
def refresh_setups():
    df = add_indicators(load_candles())
    setups = [enrich_setup(s, df) for s in load_setups()]
    from .labels import save_setups

    save_setups(setups)
    return {"setups": setups}


@app.post("/api/analyze")
def analyze():
    return analyze_patterns()


@app.get("/api/strategy")
def strategy():
    s = load_strategy()
    if not s:
        raise HTTPException(404, "No strategy yet")
    return s


@app.post("/api/backtest")
def backtest(period: str = "validation"):
    if period not in load_splits()["periods"]:
        raise HTTPException(400, f"Unknown period: {period}")
    return run_backtest(period)


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
