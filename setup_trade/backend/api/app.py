from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import backtest, candles, health, research, setups, validation

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"

app = FastAPI(title="Setup Trade", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(candles.router, prefix="/api", tags=["candles"])
app.include_router(setups.router, prefix="/api", tags=["setups"])
app.include_router(backtest.router, prefix="/api", tags=["backtest"])
app.include_router(research.router, prefix="/api", tags=["research"])
app.include_router(validation.router, prefix="/api", tags=["validation"])


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
