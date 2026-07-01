"""Tiện ích tỉnh/thành và ngữ cảnh chấm."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEFAULT_PROVINCES: dict[str, Any] = {
    "provinces": [
        {
            "id": "hcm",
            "name": "TP.HCM",
            "exam_style": "De tuyen sinh lop 10 theo cau truc TP.HCM.",
            "grading_notes": "Uu tien kha nang hieu van ban, lap luan ro va tra loi dung yeu cau cau hoi.",
        }
    ]
}


@lru_cache
def load_provinces() -> dict[str, Any]:
    path = DATA_DIR / "provinces.json"
    if not path.exists():
        return DEFAULT_PROVINCES
    return json.loads(path.read_text(encoding="utf-8"))


def get_province(province_id: str) -> dict[str, Any]:
    provinces = load_provinces()["provinces"]
    for p in provinces:
        if p["id"] == province_id:
            return p
    return provinces[0]  # HCM-only fallback


def province_prompt_block(province_id: str) -> str:
    p = get_province(province_id)
    return f"""BỐI CẢNH TỈNH/THÀNH: {p['name']}
- Cấu trúc đề: {p['exam_style']}
- Lưu ý chấm: {p['grading_notes']}"""
