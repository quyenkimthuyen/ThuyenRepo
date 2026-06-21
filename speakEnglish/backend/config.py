"""Configuration for PronounceLab Personal backend."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "tmp" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Alignment method: "mfa" | "gentle" | "fallback"
ALIGNMENT_METHOD = os.getenv("ALIGNMENT_METHOD", "fallback")

# Scoring method: "gop" | "wav2vec2" | "fallback"
SCORING_METHOD = os.getenv("SCORING_METHOD", "fallback")

# Thresholds (tunable)
THRESHOLD_OK = float(os.getenv("THRESHOLD_OK", "0.75"))
THRESHOLD_WARN = float(os.getenv("THRESHOLD_WARN", "0.50"))
OVERALL_PASS_SCORE = int(os.getenv("OVERALL_PASS_SCORE", "80"))

# Audio settings
TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1

# Gentle / MFA paths (set via env when installed)
GENTLE_URL = os.getenv("GENTLE_URL", "http://localhost:8765")
MFA_MODEL_DIR = os.getenv("MFA_MODEL_DIR", "")

# CORS
CORS_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "null",  # file:// protocol
]
