"""PronounceLab Personal — FastAPI local service."""

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception as e:
    print(f"Warning: Failed to load static-ffmpeg: {e}")

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.evaluate import router as evaluate_router
from config import CORS_ORIGINS, UPLOAD_DIR

app = FastAPI(
    title="PronounceLab Personal",
    description="Local pronunciation evaluation service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evaluate_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    from config import ALIGNMENT_METHOD, SCORING_METHOD
    return {
        "status": "ok",
        "alignment_method": ALIGNMENT_METHOD,
        "scoring_method": SCORING_METHOD,
    }


@app.get("/api/v1/audio/{filename}")
async def serve_audio(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists() or ".." in filename:
        return {"error": "not found"}
    return FileResponse(path)


@app.delete("/api/v1/audio/cleanup")
async def cleanup_audio():
    """Remove all temp audio files."""
    count = 0
    for f in UPLOAD_DIR.glob("*"):
        if f.is_file():
            f.unlink()
            count += 1
    return {"deleted": count}
