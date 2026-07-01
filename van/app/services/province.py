"""Tiện ích tỉnh/thành và ngữ cảnh chấm."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def load_provinces() -> dict[str, Any]:
    return json.loads((DATA_DIR / "provinces.json").read_text(encoding="utf-8"))


def get_province(province_id: str) -> dict[str, Any]:
    provinces = load_provinces()["provinces"]
    for p in provinces:
        if p["id"] == province_id:
            return p
    return provinces[-1]  # generic fallback


def province_prompt_block(province_id: str) -> str:
    p = get_province(province_id)
    return f"""BỐI CẢNH TỈNH/THÀNH: {p['name']}
- Cấu trúc đề: {p['exam_style']}
- Lưu ý chấm: {p['grading_notes']}"""
