#!/usr/bin/env python3
"""Parse Hacker TOEIC Reading PDF into JSON."""

import fitz
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READING_PDF = ROOT / "data" / "HACKER Vol 2 RC" / "HACKER 2 READING.pdf"
ANSWERS_FILE = ROOT / "data" / "HACKER Vol 2 RC" / "reading_answers.json"
OUT_DIR = ROOT / "public" / "data" / "reading"

PAGES_PER_TEST = 30
TEST_START_PAGE = 1  # 0-indexed: page 2 in PDF

NOISE_RE = re.compile(
    r"GO ON TO THE NEXT PAGE|Hackers\.co\.kr|TEST\s*\d+\s*PART|"
    r"^[\s\\>j°•\*mUHJi]+$|^[0-9]+\s+sa",
    re.I | re.M,
)


def clean(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_passage(s: str) -> str:
    lines = []
    for line in s.split("\n"):
        line = line.strip()
        if not line or NOISE_RE.search(line):
            continue
        if re.match(r"^[\d\s°•\*]+$", line) and len(line) < 15:
            continue
        lines.append(line)
    return "\n".join(lines)


def parse_options(text: str) -> dict[str, str]:
    opts = {}
    for m in re.finditer(r"\(([A-D])\)\s*(.+?)(?=\([A-D]\)|$)", text, re.DOTALL):
        val = clean(m.group(2))
        if val:
            opts[m.group(1)] = val
    return opts


def get_test_text(doc, test_num: int) -> str:
    start = TEST_START_PAGE + (test_num - 1) * PAGES_PER_TEST
    end = start + PAGES_PER_TEST
    text = ""
    for i in range(start, min(end, len(doc))):
        text += doc[i].get_text("text") + "\n"
    return text


def parse_part5(text: str) -> list[dict]:
    # Extract Part 5 section only
    m = re.search(r"PART\s*5\s*\nDirections(.+?)(?=PART\s*6)", text, re.DOTALL | re.I)
    if not m:
        m = re.search(r"101\.\s*(.+?)(?=PART\s*6)", text, re.DOTALL | re.I)
        section = m.group(0) if m else text
    else:
        section = m.group(1)

    questions = []
    pattern = r"(\d{3})\.\s*(.+?)(?=\n\d{3}\.\s|\nPART\s*6|\Z)"
    for m in re.finditer(pattern, section, re.DOTALL):
        qnum = int(m.group(1))
        if not 101 <= qnum <= 130:
            continue
        body = m.group(2).strip()
        opt_m = re.search(r"\(A\)", body)
        if not opt_m:
            continue
        sentence = clean(body[: opt_m.start()])
        opts = parse_options(body[opt_m.start():])
        if len(opts) < 2:
            continue
        questions.append({
            "id": qnum,
            "sentence": sentence,
            "options": opts,
        })
    return questions


def parse_question_options_block(block: str, qnum: int, part: int = 6) -> dict:
    """Extract options for a specific question number from a block."""
    if part == 6:
        pattern = rf"(?<!\d){qnum}\.\s*\(A\)\s*(.+?)(?=(?<!\d)\d{{3}}\.\s*\(A\)|GO ON TO THE NEXT|TEST\s*\d|\Z)"
        m = re.search(pattern, block, re.DOTALL | re.I)
        if not m:
            return {}
        return parse_options("(A) " + m.group(1))
    else:
        # Part 7: "147. Question text\n(A) opt..."
        pattern = rf"(?<!\d){qnum}\.\s+.+?\n\s*\(A\)\s*(.+?)(?=(?<!\d)\d{{3}}\.\s+|GO ON TO THE NEXT|TEST\s*\d|\Z)"
        m = re.search(pattern, block, re.DOTALL | re.I)
        if not m:
            # Try same-line format
            pattern2 = rf"(?<!\d){qnum}\.\s+.+?\(A\)\s*(.+?)(?=(?<!\d)\d{{3}}\.|GO ON|\Z)"
            m = re.search(pattern2, block, re.DOTALL | re.I)
            if not m:
                return {}
        return parse_options("(A) " + m.group(1))


def parse_part6_7(text: str, part: int) -> list[dict]:
    if part == 6:
        m = re.search(r"PART\s*6(.+?)PART\s*7", text, re.DOTALL | re.I)
    else:
        m = re.search(r"PART\s*7(.+)", text, re.DOTALL | re.I)

    if not m:
        return []

    section = m.group(1)
    passages = []
    pattern = r"Questions\s+(\d+)-(\d+)\s+refer to the following\s*(\w+)?[^.]*\."
    splits = list(re.finditer(pattern, section, re.I))

    for i, sm in enumerate(splits):
        start = sm.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(section)
        block = section[start:end]
        q_from, q_to = int(sm.group(1)), int(sm.group(2))
        doc_type = (sm.group(3) or "text").lower()
        q_ids = list(range(q_from, q_to + 1))

        # Passage ends at first question line for Part 7, or first "NNN. (A)" for Part 6
        first_opt = None
        if part == 6:
            for qn in q_ids:
                fm = re.search(rf"(?<!\d){qn}\.\s*\(A\)", block)
                if fm and (first_opt is None or fm.start() < first_opt.start()):
                    first_opt = fm
        else:
            fm = re.search(rf"(?<!\d){q_from}\.\s+", block)
            if fm:
                first_opt = fm
        passage_text = clean_passage(block[: first_opt.start()]) if first_opt else clean_passage(block)

        questions = []
        for qnum in q_ids:
            if part == 7:
                qm = re.search(rf"(?<!\d){qnum}\.\s+(.+?)(?=\n\s*\(A\)|\(A\))", block, re.DOTALL)
                qtext = clean(qm.group(1)) if qm else ""
            else:
                qtext = ""

            opts = parse_question_options_block(block, qnum, part)
            if len(opts) >= 2:
                questions.append({"id": qnum, "question": qtext, "options": opts})

        passages.append({
            "questionIds": q_ids,
            "type": doc_type,
            "passage": passage_text,
            "questions": questions,
        })

    return passages


def load_answers() -> dict:
    with open(ANSWERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def attach_answers(test: dict, answers: dict[str, str]):
    for q in test["parts"]["5"]["questions"]:
        q["answer"] = answers.get(str(q["id"]), "")
    for pk in ["6", "7"]:
        for passage in test["parts"][pk]["passages"]:
            for q in passage["questions"]:
                q["answer"] = answers.get(str(q["id"]), "")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(READING_PDF))
    all_answers = load_answers()
    index = []

    for test_num in range(1, 11):
        text = get_test_text(doc, test_num)
        answers = all_answers.get(str(test_num), {})

        part5 = parse_part5(text)
        part6 = parse_part6_7(text, 6)
        part7 = parse_part6_7(text, 7)

        test = {
            "id": test_num,
            "title": f"Test {test_num:02d}",
            "section": "reading",
            "parts": {
                "5": {"questions": part5},
                "6": {"passages": part6},
                "7": {"passages": part7},
            },
            "answers": answers,
        }
        attach_answers(test, answers)

        out = OUT_DIR / f"test{test_num:02d}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(test, f, ensure_ascii=False, indent=2)

        p5 = len(part5)
        p6q = sum(len(p["questions"]) for p in part6)
        p7q = sum(len(p["questions"]) for p in part7)
        print(f"Test {test_num:02d}: P5={p5}/30 P6={p6q}/16 P7={p7q}/54")
        index.append({
            "id": test_num,
            "title": test["title"],
            "file": f"reading/test{test_num:02d}.json",
            "section": "reading",
        })

    with open(OUT_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("Done!")


if __name__ == "__main__":
    main()
