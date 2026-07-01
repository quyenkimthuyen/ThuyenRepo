"""Chấm đọc hiểu — nhiều câu, kèm đáp án khung."""

from __future__ import annotations

import json
from typing import Any

from app.graders.cursor_client import call_cursor, load_rubric
from app.models.schemas import ReadingQuestion
from app.services.province import province_prompt_block


def grade_reading(
    *,
    passage: str,
    questions: list[ReadingQuestion],
    province_id: str = "generic",
) -> dict[str, Any]:
    rubric = load_rubric("reading")
    qa_block = "\n\n".join(
        f"Câu {q.id} (tối đa {q.max_score}đ):\nĐề: {q.prompt}\nTrả lời HS: {q.answer}"
        for q in questions
    )

    prompt = f"""Bạn là giám khảo Ngữ văn thi tuyển sinh lớp 10.
Chấm phần ĐỌC HIỂU, chấm chặt như thi thật.

{province_prompt_block(province_id)}

VĂN BẢN:
---
{passage.strip()}
---

CÁC CÂU HỎI VÀ TRẢ LỜI:
---
{qa_block}
---

RUBRIC:
{json.dumps(rubric, ensure_ascii=False, indent=2)}

QUY TẮC:
1. Chấm từng câu theo max_score.
2. Với mỗi câu: nêu missing_points (ý HS thiếu) và framework_answer (2-4 ý đáp án khung, không bắt học thuộc).
3. Chấp nhận diễn đạt khác nếu đúng ý, bám văn bản.
4. revision_hints: gợi ý 1 câu trả lời bổ sung ngắn cho câu điểm thấp nhất.

Trả lời CHỈ JSON:
{{
  "total": <float>,
  "max_score": <float>,
  "question_scores": [
    {{"id": "<id>", "score": <float>, "max": <float>, "note": "<str>",
      "missing_points": ["<ý còn thiếu>"],
      "framework_answer": ["<ý trong đáp án khung>"]}}
  ],
  "revision_hints": [{{"target": "Câu X", "suggestion": "...", "example_sentence": "..."}}],
  "strengths": ["..."],
  "weaknesses": ["..."],
  "next_steps": ["..."]
}}"""

    result = call_cursor(prompt)
    if not result.get("error"):
        result["rubric_type"] = "reading"
        result["province_id"] = province_id
    return result
