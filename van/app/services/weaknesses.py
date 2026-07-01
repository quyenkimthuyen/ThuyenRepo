"""Phân tích lỗi hay mắc từ lịch sử chấm."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from app.db.history import get_conn

WEAKNESS_PATTERNS = [
    (r"xuống dòng|hình thức|dung lượng|200 chữ", "hinh_thuc_doan_van", "Hình thức đoạn văn / dung lượng"),
    (r"dẫn chứng|bám văn bản|ngữ liệu", "thieu_dan_chung", "Thiếu dẫn chứng từ văn bản"),
    (r"bố cục|mở bài|kết bài", "bo_cuc", "Bố cục bài văn chưa chặt"),
    (r"chính tả|ngữ pháp|lỗi", "ngon_ngu", "Lỗi chính tả / ngôn ngữ"),
    (r"chung chung|sơ sài|lan man", "noi_dung_so", "Nội dung còn chung chung"),
    (r"lạc đề|sai đề|hiểu đề", "lac_de", "Xác định đề / lạc đề"),
    (r"biện pháp|nghệ thuật|hình ảnh", "nghe_thuat", "Phân tích nghệ thuật chưa gắn nội dung"),
    (r"lập luận|luận điểm", "lap_luan", "Lập luận chưa chặt"),
]

PRACTICE_MAP = {
    "hinh_thuc_doan_van": {"type": "paragraph_200", "tip": "Luyện 1 đoạn 200 chữ, không Enter, đếm từ trước khi nộp."},
    "thieu_dan_chung": {"type": "reading", "tip": "Mỗi ý trả lời kèm 1 chi tiết trích từ bài đọc."},
    "bo_cuc": {"type": "essay_social", "tip": "Lập dàn ý 3 phần trước khi viết NL xã hội."},
    "ngon_ngu": {"type": "paragraph_200", "tip": "Đọc lại bài, sửa 5 lỗi chính tả hay mắc."},
    "noi_dung_so": {"type": "paragraph_200", "tip": "Chọn 2 chi tiết tiêu biểu, phân tích sâu."},
    "lac_de": {"type": "essay_social", "tip": "Gạch từ khóa đề, kiểm tra mỗi đoạn bám đề."},
    "nghe_thuat": {"type": "paragraph_200", "tip": "Công thức: hình ảnh → biện pháp → ý nghĩa."},
    "lap_luan": {"type": "essay_social", "tip": "Mỗi luận điểm: ý + lý lẽ + ví dụ."},
}


def _extract_text_from_payload(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("weaknesses", "next_steps"):
        parts.extend(payload.get(key) or [])
    for val in (payload.get("breakdown") or {}).values():
        if isinstance(val, dict) and val.get("note"):
            parts.append(str(val["note"]))
    for q in payload.get("question_scores") or []:
        if q.get("note"):
            parts.append(str(q["note"]))
    fc = payload.get("form_check") or {}
    parts.extend(fc.get("warnings") or [])
    return " ".join(parts).lower()


def analyze_weaknesses(limit: int = 100) -> dict[str, Any]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT payload FROM grade_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        type_rows = conn.execute(
            """
            SELECT question_type, AVG(total / NULLIF(max_score, 0)) AS ratio
            FROM grade_history GROUP BY question_type
            ORDER BY ratio ASC
            """
        ).fetchall()

    counter: Counter[str] = Counter()
    for row in rows:
        payload = json.loads(row["payload"])
        text = _extract_text_from_payload(payload)
        for pattern, key, _ in WEAKNESS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                counter[key] += 1

    items = []
    for key, count in counter.most_common(5):
        info = PRACTICE_MAP.get(key, {"type": "reading", "tip": "Ôn lại dạng bài yếu."})
        label = next(lbl for pat, k, lbl in WEAKNESS_PATTERNS if k == key)
        items.append({
            "id": key,
            "label": label,
            "count": count,
            "practice_type": info["type"],
            "tip": info["tip"],
        })

    weakest_type = type_rows[0]["question_type"] if type_rows else None

    return {
        "top_weaknesses": items[:3],
        "weakest_type": weakest_type,
        "recommendation": items[0]["tip"] if items else "Làm 1 bài và chấm để app phân tích lỗi của bạn.",
    }
