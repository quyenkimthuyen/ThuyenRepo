"""Chấm đoạn văn ~200 chữ."""

from __future__ import annotations

from typing import Any

from app.graders.cursor_client import build_grading_prompt, call_cursor, load_rubric
from app.graders.rules import check_paragraph_form


def grade_paragraph(
    *,
    passage: str,
    question: str,
    answer: str,
    target_words: int = 200,
    province_id: str = "generic",
) -> dict[str, Any]:
    form = check_paragraph_form(answer, target_words=target_words)
    rubric = load_rubric("paragraph_200")
    prompt = build_grading_prompt(
        question_type="Viết đoạn văn ~200 chữ (2 điểm)",
        rubric=rubric,
        passage=passage,
        question=question,
        student_answer=answer,
        province_id=province_id,
        form_check=form.to_dict(),
    )
    result = call_cursor(prompt)
    if not result.get("error"):
        result["form_check"] = form.to_dict()
        result["rubric_type"] = "paragraph_200"
        result["province_id"] = province_id
    return result
