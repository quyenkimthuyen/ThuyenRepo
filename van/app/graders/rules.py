"""Kiểm tra hình thức bài làm bằng rule (không cần AI)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FormCheckResult:
    word_count: int
    has_line_breaks: bool
    is_single_paragraph: bool
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "word_count": self.word_count,
            "has_line_breaks": self.has_line_breaks,
            "is_single_paragraph": self.is_single_paragraph,
            "warnings": self.warnings,
        }


def count_vietnamese_words(text: str) -> int:
    """Đếm từ tiếng Việt (tách theo khoảng trắng, bỏ dấu câu rời)."""
    cleaned = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    tokens = [t for t in cleaned.split() if t.strip()]
    return len(tokens)


def check_paragraph_form(text: str, target_words: int = 200, tolerance: int = 50) -> FormCheckResult:
    """Kiểm tra đoạn văn ~200 chữ, một đoạn không xuống dòng."""
    stripped = text.strip()
    has_line_breaks = "\n" in stripped
    word_count = count_vietnamese_words(stripped)

    warnings: list[str] = []
    if has_line_breaks:
        warnings.append("Phát hiện xuống dòng — đoạn văn thi vào 10 thường yêu cầu một đoạn liền mạch.")
    if word_count < target_words - tolerance:
        warnings.append(f"Ngắn hơn mục tiêu (~{target_words} chữ): hiện có {word_count} từ.")
    elif word_count > target_words + tolerance:
        warnings.append(f"Dài hơn mục tiêu (~{target_words} chữ): hiện có {word_count} từ.")

    return FormCheckResult(
        word_count=word_count,
        has_line_breaks=has_line_breaks,
        is_single_paragraph=not has_line_breaks,
        warnings=warnings,
    )


@dataclass
class EssayFormCheckResult:
    word_count: int
    paragraph_count: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "warnings": self.warnings,
        }


def check_essay_form(text: str, min_words: int = 300, max_words: int = 700) -> EssayFormCheckResult:
    """Kiểm tra hình thức bài văn nghị luận."""
    stripped = text.strip()
    word_count = count_vietnamese_words(stripped)
    paragraphs = [p for p in re.split(r"\n\s*\n", stripped) if p.strip()]
    if len(paragraphs) <= 1 and "\n" in stripped:
        paragraphs = [p for p in stripped.split("\n") if p.strip()]
    paragraph_count = max(len(paragraphs), 1)

    warnings: list[str] = []
    if word_count < min_words:
        warnings.append(f"Bài ngắn (hiện {word_count} từ; gợi ý ≥ {min_words} từ).")
    elif word_count > max_words:
        warnings.append(f"Bài dài (hiện {word_count} từ; gợi ý ≤ {max_words} từ).")
    if paragraph_count < 3:
        warnings.append("Có thể thiếu bố cục 3 phần (mở – thân – kết).")

    return EssayFormCheckResult(
        word_count=word_count,
        paragraph_count=paragraph_count,
        warnings=warnings,
    )
