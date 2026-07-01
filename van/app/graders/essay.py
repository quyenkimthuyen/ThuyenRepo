"""Chấm bài văn nghị luận xã hội (4 điểm)."""

from __future__ import annotations

from typing import Any

from app.graders.cursor_client import build_grading_prompt, call_cursor, load_rubric
from app.graders.rules import check_essay_form


def grade_essay(
    *,
    passage: str,
    question: str,
    answer: str,
    province_id: str = "generic",
) -> dict[str, Any]:
    form = check_essay_form(answer)
    rubric = load_rubric("essay_social")
    prompt = build_grading_prompt(
        question_type="Bài văn nghị luận xã hội (4 điểm)",
        rubric=rubric,
        passage=passage,
        question=question,
        student_answer=answer,
        province_id=province_id,
        form_check=form.to_dict(),
        extra_rules="6. Kiểm tra mở bài, thân bài, kết bài. sample_argument là 1 luận điểm mẫu ngắn.",
    )
    result = call_cursor(prompt)
    if not result.get("error"):
        result["form_check"] = form.to_dict()
        result["rubric_type"] = "essay_social"
        result["province_id"] = province_id
    return result
