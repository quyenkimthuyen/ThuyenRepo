"""Pydantic schemas cho API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GradeParagraphRequest(BaseModel):
    passage: str
    question: str
    answer: str
    target_words: int = Field(200, ge=100, le=400)
    province_id: str = "generic"
    save_history: bool = True


class ReadingQuestion(BaseModel):
    id: str
    prompt: str
    max_score: float = Field(..., gt=0)
    answer: str


class GradeReadingRequest(BaseModel):
    passage: str
    questions: list[ReadingQuestion]
    province_id: str = "generic"
    save_history: bool = True


class GradeEssayRequest(BaseModel):
    passage: str = ""
    question: str
    answer: str
    province_id: str = "generic"
    save_history: bool = True


class MockExamGradeRequest(BaseModel):
    exam_id: str
    province_id: str = "generic"
    part1_reading: list[ReadingQuestion] = []
    paragraph_answer: str = ""
    part2_reading: list[ReadingQuestion] = []
    essay_answer: str = ""
    save_history: bool = True
