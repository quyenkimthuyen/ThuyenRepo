"""API routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.config import CURSOR_API_KEY, CURSOR_MODEL, EXAMS_DIR
from app.db.history import get_stats, list_history, save_grade, save_mock_exam
from app.graders.essay import grade_essay
from app.graders.paragraph import grade_paragraph
from app.graders.reading import grade_reading
from app.models.schemas import (
    GradeEssayRequest,
    GradeParagraphRequest,
    GradeReadingRequest,
    MockExamGradeRequest,
)
from app.services.province import load_provinces
from app.services.weaknesses import analyze_weaknesses

router = APIRouter(prefix="/api")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _handle_result(result: dict[str, Any], question_type: str, save: bool) -> dict[str, Any]:
    if result.get("error"):
        raise HTTPException(status_code=502, detail=result.get("message", "Lỗi chấm bài"))
    if save:
        result["history_id"] = save_grade(question_type=question_type, result=result)
    return result


@router.get("/health")
def health():
    return {
        "status": "ok",
        "cursor_api_configured": bool(CURSOR_API_KEY),
        "model": CURSOR_MODEL,
    }


@router.get("/provinces")
def api_provinces():
    return load_provinces()


@router.get("/roadmap")
def api_roadmap():
    path = DATA_DIR / "roadmap.json"
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/weaknesses")
def api_weaknesses():
    return analyze_weaknesses()


@router.post("/grade/paragraph")
def api_grade_paragraph(body: GradeParagraphRequest):
    if not body.answer.strip():
        raise HTTPException(400, "Bài làm không được để trống.")
    if not body.passage.strip():
        raise HTTPException(400, "Ngữ liệu không được để trống.")
    result = grade_paragraph(
        passage=body.passage,
        question=body.question,
        answer=body.answer,
        target_words=body.target_words,
        province_id=body.province_id,
    )
    return _handle_result(result, "paragraph_200", body.save_history)


@router.post("/grade/reading")
def api_grade_reading(body: GradeReadingRequest):
    if not body.passage.strip():
        raise HTTPException(400, "Văn bản không được để trống.")
    if not body.questions:
        raise HTTPException(400, "Cần ít nhất một câu hỏi.")
    for q in body.questions:
        if not q.answer.strip():
            raise HTTPException(400, f"Câu {q.id} chưa có câu trả lời.")
    result = grade_reading(
        passage=body.passage,
        questions=body.questions,
        province_id=body.province_id,
    )
    return _handle_result(result, "reading", body.save_history)


@router.post("/grade/essay")
def api_grade_essay(body: GradeEssayRequest):
    if not body.answer.strip():
        raise HTTPException(400, "Bài làm không được để trống.")
    if not body.question.strip():
        raise HTTPException(400, "Đề bài không được để trống.")
    result = grade_essay(
        passage=body.passage,
        question=body.question,
        answer=body.answer,
        province_id=body.province_id,
    )
    return _handle_result(result, "essay_social", body.save_history)


@router.post("/grade/mock-exam")
def api_grade_mock_exam(body: MockExamGradeRequest):
    path = EXAMS_DIR / f"{body.exam_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Không tìm thấy đề: {body.exam_id}")
    exam = json.loads(path.read_text(encoding="utf-8"))
    p1, p2 = exam["part1"], exam["part2"]
    pid = body.province_id or exam.get("province", "generic")

    parts: list[dict[str, Any]] = []
    total = 0.0

    if body.part1_reading:
        r = grade_reading(passage=p1["literary_passage"], questions=body.part1_reading, province_id=pid)
        if r.get("error"):
            raise HTTPException(502, r.get("message"))
        parts.append({"section": "Đọc hiểu P1", "max_score": sum(q.max_score for q in body.part1_reading), **r})
        total += r["total"]

    if body.paragraph_answer.strip():
        r = grade_paragraph(
            passage=p1["literary_passage"],
            question=p1["paragraph"]["prompt"],
            answer=body.paragraph_answer,
            province_id=pid,
        )
        if r.get("error"):
            raise HTTPException(502, r.get("message"))
        parts.append({"section": "Đoạn văn P1", "max_score": p1["paragraph"]["max_score"], **r})
        total += r["total"]

    if body.part2_reading:
        r = grade_reading(passage=p2["info_passage"], questions=body.part2_reading, province_id=pid)
        if r.get("error"):
            raise HTTPException(502, r.get("message"))
        parts.append({"section": "Đọc hiểu P2", "max_score": sum(q.max_score for q in body.part2_reading), **r})
        total += r["total"]

    if body.essay_answer.strip():
        r = grade_essay(
            passage=p2["info_passage"],
            question=p2["essay"]["prompt"],
            answer=body.essay_answer,
            province_id=pid,
        )
        if r.get("error"):
            raise HTTPException(502, r.get("message"))
        parts.append({"section": "NL xã hội P2", "max_score": p2["essay"]["max_score"], **r})
        total += r["total"]

    result = {
        "total": round(total, 2),
        "max_score": exam.get("total_score", 10),
        "exam_id": body.exam_id,
        "province_id": pid,
        "score_sheet": [
            {"section": p["section"], "score": p["total"], "max": p["max_score"]} for p in parts
        ],
        "parts": parts,
        "strengths": [s for p in parts for s in (p.get("strengths") or [])][:4],
        "weaknesses": [w for p in parts for w in (p.get("weaknesses") or [])][:4],
        "next_steps": [n for p in parts for n in (p.get("next_steps") or [])][:5],
        "revision_hints": [h for p in parts for h in (p.get("revision_hints") or [])][:6],
    }

    if body.save_history:
        result["history_id"] = save_mock_exam(result)

    return result


@router.get("/exams")
def list_exams(province: str | None = Query(None)):
    exams = []
    if not EXAMS_DIR.exists():
        return {"exams": exams}
    for path in sorted(EXAMS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        prov = data.get("province", "generic")
        if province and province != "all" and prov != province:
            continue
        exams.append({
            "id": data.get("id", path.stem),
            "title": data.get("title", path.stem),
            "province": prov,
        })
    return {"exams": exams}


@router.get("/exams/{exam_id}")
def get_exam(exam_id: str):
    path = EXAMS_DIR / f"{exam_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Không tìm thấy đề: {exam_id}")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/history")
def api_history(limit: int = 30):
    return {"items": list_history(limit=limit)}


@router.get("/stats")
def api_stats():
    return get_stats()
