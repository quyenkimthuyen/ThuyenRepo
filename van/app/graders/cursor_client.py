"""Gọi Cursor SDK — lớp lõi dùng chung."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cursor_sdk import Agent, AgentOptions, CursorAgentError, LocalAgentOptions

from app.config import CURSOR_API_KEY, CURSOR_MODEL, ROOT
from app.services.province import province_prompt_block

RUBRICS_DIR = Path(__file__).resolve().parent.parent / "rubrics"

FEEDBACK_JSON_EXTRA = """
  "revision_hints": [
    {{"target": "<tiêu chí hoặc câu>", "suggestion": "<gợi ý sửa cụ thể>", "example_sentence": "<câu mẫu ngắn>"}}
  ],
  "sample_opening": "<gợi ý mở bài/đoạn 1-2 câu>",
  "sample_argument": "<gợi ý 1 luận điểm ngắn>"
"""


def load_rubric(rubric_name: str) -> dict[str, Any]:
    path = RUBRICS_DIR / f"{rubric_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy rubric: {rubric_name}")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group())
    raise ValueError("AI không trả về JSON hợp lệ")


def call_cursor(prompt: str, api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
    key = (api_key or CURSOR_API_KEY or "").strip()
    if not key:
        raise ValueError("Thiếu CURSOR_API_KEY. Tạo file api.key hoặc .env.")

    model_id = model or CURSOR_MODEL
    try:
        result = Agent.prompt(
            prompt,
            AgentOptions(
                api_key=key,
                model=model_id,
                local=LocalAgentOptions(cwd=str(ROOT)),
            ),
        )
    except CursorAgentError as exc:
        return {"error": True, "message": f"Lỗi Cursor API: {exc.message}", "retryable": exc.is_retryable}

    if result.status == "error":
        return {"error": True, "message": "Agent chạy lỗi.", "run_id": getattr(result, "id", None)}

    raw = result.result or ""
    try:
        parsed = extract_json(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        return {"error": True, "message": str(exc), "raw_response": raw[:2000]}

    parsed["error"] = False
    return parsed


def build_grading_prompt(
    *,
    question_type: str,
    rubric: dict[str, Any],
    passage: str,
    question: str,
    student_answer: str,
    province_id: str = "generic",
    form_check: dict[str, Any] | None = None,
    extra_rules: str = "",
    include_revision: bool = True,
) -> str:
    rubric_text = json.dumps(rubric, ensure_ascii=False, indent=2)
    form_hint = ""
    if form_check:
        form_hint = f"\n\nKết quả kiểm tra hình thức (rule):\n{json.dumps(form_check, ensure_ascii=False, indent=2)}"

    revision_block = ""
    if include_revision:
        revision_block = f",{FEEDBACK_JSON_EXTRA}"

    return f"""Bạn là giám khảo môn Ngữ văn kỳ thi tuyển sinh lớp 10 THPT tại Việt Nam.
Chấm bài theo rubric, chấm hơi chặt như thi thật.

{province_prompt_block(province_id)}

LOẠI BÀI: {question_type}

NGỮ LIỆU:
---
{passage.strip() or "(Không có ngữ liệu riêng)"}
---

YÊU CẦU:
---
{question.strip()}
---

BÀI LÀM HỌC SINH:
---
{student_answer.strip()}
---

RUBRIC:
{rubric_text}
{form_hint}

QUY TẮC:
1. Chấm từng tiêu chí, chọn đúng mức điểm trong rubric.
2. Đáp án mở: chấp nhận diễn đạt khác nếu đúng ý, bám ngữ liệu.
3. Không thưởng cao khi thiếu dẫn chứng.
4. revision_hints: gợi ý SỬA CỤ THỂ (câu mẫu ngắn), KHÔNG viết hộ cả bài.
5. sample_opening / sample_argument: chỉ 1-2 câu gợi ý hướng viết.
{extra_rules}

Trả lời CHỈ JSON (không markdown):
{{
  "total": <float>,
  "max_score": <float>,
  "breakdown": {{"<id>": {{"score": <float>, "max": <float>, "note": "<str>"}}}},
  "strengths": ["..."],
  "weaknesses": ["..."],
  "next_steps": ["..."]{revision_block}
}}"""
