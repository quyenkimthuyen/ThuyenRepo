"""Cấu hình ứng dụng từ biến môi trường hoặc file api.key."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATIC_DIR = ROOT / "static"
EXAMS_DIR = Path(__file__).resolve().parent / "exams"
RUBRICS_DIR = Path(__file__).resolve().parent / "rubrics"
API_KEY_FILE = ROOT / "api.key"

DATA_DIR.mkdir(exist_ok=True)


def _load_api_key() -> str | None:
    env_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if env_key:
        return env_key
    if API_KEY_FILE.exists():
        return API_KEY_FILE.read_text(encoding="utf-8").strip() or None
    return None


CURSOR_API_KEY: str | None = _load_api_key()
CURSOR_MODEL: str = os.environ.get("CURSOR_MODEL", "composer-2.5")
DB_PATH = DATA_DIR / "van_on_luyen.db"
