"""Ôn Văn vào 10 — entry point."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import STATIC_DIR

app = FastAPI(
    title="Ôn Văn vào 10",
    description="Ôn luyện Ngữ văn tuyển sinh lớp 10 — chấm qua Cursor API",
    version="0.2.0",
)

app.include_router(router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    path = STATIC_DIR / "index.html"
    if path.exists():
        return FileResponse(path)
    return {"docs": "/docs", "health": "/api/health"}
