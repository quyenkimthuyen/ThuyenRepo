"""Gọi Cursor SDK — lớp lõi dùng chung."""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

import cursor_sdk._bridge as cursor_bridge
import cursor_sdk._store_callback as cursor_store_callback
import cursor_sdk._tool_callback as cursor_tool_callback
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


def _patch_windows_bridge_discovery() -> None:
    if os.name != "nt" or getattr(cursor_bridge, "_van_windows_patch", False):
        return

    def new_auth_token() -> str:
        token = secrets.token_urlsafe(32)
        return f"tok_{token}" if token.startswith("-") else token

    cursor_tool_callback._new_auth_token = new_auth_token
    cursor_store_callback._new_auth_token = new_auth_token

    def read_discovery(process: Any, timeout: float) -> dict[str, Any]:
        if process.stderr is None:
            raise cursor_bridge.CursorSDKError("Bridge process stderr is unavailable")

        stderr_fd = process.stderr.fileno()
        was_blocking = os.get_blocking(stderr_fd)
        os.set_blocking(stderr_fd, False)
        try:
            decoder = __import__("codecs").getincrementaldecoder("utf-8")(errors="replace")
            deadline = time.monotonic() + timeout
            stderr_lines: list[str] = []
            pending = ""

            def drain_available() -> dict[str, Any] | None:
                nonlocal pending
                while True:
                    try:
                        chunk = os.read(stderr_fd, 8192)
                    except BlockingIOError:
                        return None
                    if not chunk:
                        final_text = decoder.decode(b"", final=True)
                        if final_text:
                            pending += final_text
                        if pending:
                            line = pending
                            pending = ""
                            stderr_lines.append(line)
                            return cursor_bridge.parse_discovery_line(line)
                        return None
                    pending += decoder.decode(chunk)
                    while "\n" in pending:
                        line, pending = pending.split("\n", 1)
                        line += "\n"
                        stderr_lines.append(line)
                        discovery = cursor_bridge.parse_discovery_line(line)
                        if discovery is not None:
                            return discovery

            while time.monotonic() < deadline:
                discovery = drain_available()
                if discovery is not None:
                    return dict(discovery)
                exit_code = process.poll()
                if exit_code is not None:
                    discovery = drain_available()
                    if discovery is not None:
                        return dict(discovery)
                    raise cursor_bridge.CursorSDKError(
                        f"Bridge exited before discovery with status {exit_code}: "
                        + "".join(stderr_lines)
                        + pending
                    )
                time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
            raise cursor_bridge.CursorSDKError("Timed out waiting for bridge discovery")
        finally:
            os.set_blocking(stderr_fd, was_blocking)

    cursor_bridge._read_discovery = read_discovery
    cursor_bridge._van_windows_patch = True


_patch_windows_bridge_discovery()


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
    except OSError as exc:
        return {
            "error": True,
            "message": (
                "Lỗi khởi động Cursor SDK trên máy này. "
                f"Chi tiết: {exc}"
            ),
            "retryable": False,
        }

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
