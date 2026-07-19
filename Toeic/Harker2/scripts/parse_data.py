#!/usr/bin/env python3
"""Parse Hacker TOEIC Listening PDFs into JSON for the frontend app."""

import fitz
import json
import re
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "public" / "data"
IMG_DIR = ROOT / "public" / "images"

TRANSCRIPT_PDF = DATA_DIR / "HACKER 2 LISTENING TRANSCRIPT.pdf"
LISTENING_PDF = DATA_DIR / "HACKER 2 LISTENING.pdf"
AUDIO_DIR = DATA_DIR / "AUDIO HACKER"

ACCENT_MAP = {
    "미국식": "Mỹ",
    "영국식": "Anh",
    "호주식": "Úc",
    "캐나다식": "Canada",
}


def clean_text(s: str) -> str:
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_accent(line: str) -> str:
    for kr, vi in ACCENT_MAP.items():
        if kr in line:
            parts = []
            for p in re.split(r"\s*→\s*", line):
                p = p.strip()
                for k, v in ACCENT_MAP.items():
                    if k in p:
                        p = v
                        break
                else:
                    p = re.sub(r"발음", "", p).strip()
                if p:
                    parts.append(p)
            return " → ".join(parts) if parts else line.strip()
    return line.strip()


def parse_answers(block: str) -> dict[int, str]:
    answers = {}
    for m in re.finditer(r"(\d+)\s*\(([A-D])\)", block):
        answers[int(m.group(1))] = m.group(2)
    return answers


def parse_options(text: str) -> dict[str, str]:
    opts = {}
    for m in re.finditer(r"\(([A-D])\)\s*(.+?)(?=\([A-D]\)|$)", text, re.DOTALL):
        opts[m.group(1)] = clean_text(m.group(2))
    return opts


def parse_part1_2(section: str, part: int) -> list[dict]:
    questions = []
    # Split by question number at line start
    chunks = re.split(r"(?=\n\s*\d+\s*\n)", "\n" + section)
    for chunk in chunks:
        m = re.match(r"\s*(\d+)\s*\n(.+)", chunk, re.DOTALL)
        if not m:
            continue
        qnum = int(m.group(1))
        body = m.group(2).strip()
        lines = body.split("\n")
        accent_line = lines[0].strip() if lines else ""
        accent = parse_accent(accent_line)
        rest = "\n".join(lines[1:]) if len(lines) > 1 else body

        if part == 1:
            opts = parse_options(rest)
            questions.append({
                "id": qnum,
                "accent": accent,
                "options": opts,
                "transcript": None,
            })
        else:  # part 2
            # Question text before options
            opt_match = re.search(r"\([A-C]\)", rest)
            if opt_match:
                qtext = clean_text(rest[: opt_match.start()])
                opts = parse_options(rest[opt_match.start() :])
            else:
                qtext = clean_text(rest)
                opts = {}
            if "저작권" in qtext or "스크립트" in qtext and len(qtext) > 80:
                continue
            questions.append({
                "id": qnum,
                "accent": accent,
                "question": qtext,
                "options": opts,
            })
    return questions


def parse_part3_4(section: str, part: int) -> list[dict]:
    passages = []
    pattern = r"Questions\s+(\d+)-(\d+)\s+refer to the following[^.]*\."
    splits = list(re.finditer(pattern, section, re.IGNORECASE))
    for i, m in enumerate(splits):
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(section)
        block = section[start:end].strip()
        q_from, q_to = int(m.group(1)), int(m.group(2))
        q_ids = list(range(q_from, q_to + 1))

        lines = block.split("\n")
        accent = ""
        transcript_lines = []
        accent_done = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if not accent_done and ("발음" in line or "→" in line):
                accent = parse_accent(line)
                accent_done = True
                continue
            if accent_done or not re.match(r"^[WM]\d*:", line) and not line.startswith("Good ") and not line.startswith("Hello"):
                if "발음" in line and not accent:
                    accent = parse_accent(line)
                    accent_done = True
                    continue
            transcript_lines.append(line)

        transcript = clean_text(" ".join(transcript_lines))
        # Better: preserve speaker lines
        raw_lines = []
        for line in lines:
            line = line.strip()
            if not line or ("발음" in line and len(line) < 40):
                if "발음" in line:
                    accent = parse_accent(line)
                continue
            raw_lines.append(line)

        transcript_formatted = "\n".join(raw_lines)
        passages.append({
            "questionIds": q_ids,
            "accent": accent,
            "transcript": transcript_formatted,
        })
    return passages


def parse_test_block(block: str, test_num: int) -> dict:
    # Answer keys
    ak_match = re.search(r"Answer Keys\s*(.+?)(?=PART 1|\Z)", block, re.DOTALL)
    answers = parse_answers(ak_match.group(1)) if ak_match else {}

    part1_match = re.search(r"PART 1\s*(.+?)(?=PART 2)", block, re.DOTALL)
    part2_match = re.search(r"PART 2\s*(.+?)(?=PART 3)", block, re.DOTALL)
    part3_match = re.search(r"PART 3\s*(.+?)(?=PART 4)", block, re.DOTALL)
    part4_match = re.search(r"PART 4\s*(.+?)(?=TEST\s*\d|\Z)", block, re.DOTALL)

    part1 = parse_part1_2(part1_match.group(1), 1) if part1_match else []
    part2 = parse_part1_2(part2_match.group(1), 2) if part2_match else []
    part3 = parse_part3_4(part3_match.group(1), 3) if part3_match else []
    part4 = parse_part3_4(part4_match.group(1), 4) if part4_match else []

    # Attach answers
    for q in part1 + part2:
        q["answer"] = answers.get(q["id"], "")

    for passage in part3 + part4:
        for qid in passage["questionIds"]:
            passage.setdefault("answers", {})[str(qid)] = answers.get(qid, "")

    return {
        "id": test_num,
        "title": f"Test {test_num:02d}",
        "audio": f"audio/TEST {test_num}.mp3",
        "parts": {
            "1": {"questions": part1},
            "2": {"questions": part2},
            "3": {"passages": part3},
            "4": {"passages": part4},
        },
        "answers": {str(k): v for k, v in sorted(answers.items())},
    }


def parse_transcript_pdf() -> list[dict]:
    doc = fitz.open(str(TRANSCRIPT_PDF))
    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"

    tests = []
    markers = list(re.finditer(r"TEST\s*0?(\d+)\s*Answer Keys", full_text))
    for i, m in enumerate(markers):
        test_num = int(m.group(1))
        start = m.start()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(full_text)
        block = full_text[start:end]
        tests.append(parse_test_block(block, test_num))
    return tests


def parse_listening_questions() -> dict[int, dict]:
    """Parse Part 3 & 4 questions from listening PDF."""
    doc = fitz.open(str(LISTENING_PDF))
    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"

    result = {}
    test_markers = list(re.finditer(r"TEST\s*(\d+)\s*PART\s*3|PART 3", full_text))

    # Split by test - find TEST N PART 3 sections
    test_splits = list(re.finditer(r"(?:TEST\s*(\d+)\s*)?PART 3", full_text, re.IGNORECASE))

    current_test = 1
    for i, m in enumerate(test_splits):
        if m.group(1):
            current_test = int(m.group(1))
        start = m.end()
        end = test_splits[i + 1].start() if i + 1 < len(test_splits) else len(full_text)
        section = full_text[start:end]

        # Part 3 questions until Part 4
        p3_end = re.search(r"PART\s*4", section, re.IGNORECASE)
        p3_text = section[: p3_end.start()] if p3_end else section
        p4_text = section[p3_end.end() :] if p3_end else ""

        if current_test not in result:
            result[current_test] = {"part3": {}, "part4": {}}

        for qm in re.finditer(
            r"(\d+)\.\s+(.+?)(?=\n\s*\d+\.\s+|\nGO ON|\nTEST|\Z)",
            p3_text,
            re.DOTALL,
        ):
            qnum = int(qm.group(1))
            if qnum < 32 or qnum > 70:
                continue
            body = qm.group(2).strip()
            qtext_match = re.match(r"(.+?)(?=\n\s*\(A\))", body, re.DOTALL)
            qtext = clean_text(qtext_match.group(1)) if qtext_match else ""
            opts = parse_options(body)
            result[current_test]["part3"][qnum] = {"question": qtext, "options": opts}

        for qm in re.finditer(
            r"(\d+)\.\s+(.+?)(?=\n\s*\d+\.\s+|\nGO ON|\nTEST|\Z)",
            p4_text,
            re.DOTALL,
        ):
            qnum = int(qm.group(1))
            if qnum < 71 or qnum > 100:
                continue
            body = qm.group(2).strip()
            qtext_match = re.match(r"(.+?)(?=\n\s*\(A\))", body, re.DOTALL)
            qtext = clean_text(qtext_match.group(1)) if qtext_match else ""
            opts = parse_options(body)
            result[current_test]["part4"][qnum] = {"question": qtext, "options": opts}

    return result


def merge_questions(tests: list[dict], listening_q: dict[int, dict]):
    for test in tests:
        tid = test["id"]
        lq = listening_q.get(tid, {})
        for passage in test["parts"]["3"]["passages"]:
            passage["questions"] = []
            for qid in passage["questionIds"]:
                qdata = lq.get("part3", {}).get(qid, {})
                passage["questions"].append({
                    "id": qid,
                    "question": qdata.get("question", ""),
                    "options": qdata.get("options", {}),
                    "answer": test["answers"].get(str(qid), ""),
                })
        for passage in test["parts"]["4"]["passages"]:
            passage["questions"] = []
            for qid in passage["questionIds"]:
                qdata = lq.get("part4", {}).get(qid, {})
                passage["questions"].append({
                    "id": qid,
                    "question": qdata.get("question", ""),
                    "options": qdata.get("options", {}),
                    "answer": test["answers"].get(str(qid), ""),
                })


def extract_part1_images():
    """Extract Part 1 pictures from listening PDF."""
    doc = fitz.open(str(LISTENING_PDF))
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # Map pages to tests - each test has 6 Part 1 image pages (questions 1-6)
    # Test 1 starts around page 3 (0-indexed: 2)
    test_page_ranges = {
        1: (2, 8),   # approximate
    }

    # Find pages with single large image (Part 1 pictures)
    image_pages = []
    for i in range(len(doc)):
        page = doc[i]
        imgs = page.get_images(full=True)
        text = page.get_text("text").strip()
        # Part 1 pages: mostly image, little text, question number
        if len(imgs) >= 1 and len(text) < 200:
            q_match = re.search(r"^(\d+)\.", text) or re.search(r"'✓\s*(\d+)", text)
            qnum = int(q_match.group(1)) if q_match else None
            image_pages.append((i, qnum, len(imgs)))

    # Group by test (6 images per test for q 1-6)
    test_num = 1
    q_in_test = 0
    for page_idx, qnum, _ in image_pages:
        q_in_test += 1
        if q_in_test > 6:
            test_num += 1
            q_in_test = 1
        actual_q = qnum if qnum and 1 <= qnum <= 6 else q_in_test

        test_img_dir = IMG_DIR / f"test{test_num:02d}"
        test_img_dir.mkdir(parents=True, exist_ok=True)

        page = doc[page_idx]
        imgs = page.get_images(full=True)
        if imgs:
            xref = imgs[0][0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n > 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            out_path = test_img_dir / f"q{actual_q:02d}.png"
            pix.save(str(out_path))
            print(f"  Saved {out_path}")


def fix_audio_paths(tests: list[dict]):
    """Map to actual audio filenames."""
    audio_files = {f.stem.upper().replace("TEST ", ""): f.name for f in AUDIO_DIR.glob("*.mp3")}
    for test in tests:
        key = str(test["id"])
        # Handle "Test 8" vs "TEST 8"
        for k, v in audio_files.items():
            if k == key or k == f"0{key}":
                test["audio"] = f"audio/{v}"
                break


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Parsing transcript PDF...")
    tests = parse_transcript_pdf()
    print(f"  Found {len(tests)} tests")

    print("Parsing listening questions...")
    listening_q = parse_listening_questions()

    print("Merging...")
    merge_questions(tests, listening_q)
    fix_audio_paths(tests)

    # Write individual test files + index
    index = []
    for test in tests:
        out_path = OUT_DIR / f"test{test['id']:02d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(test, f, ensure_ascii=False, indent=2)
        index.append({"id": test["id"], "title": test["title"], "file": f"test{test['id']:02d}.json"})
        print(f"  Wrote {out_path} - P1:{len(test['parts']['1']['questions'])} P2:{len(test['parts']['2']['questions'])} P3:{len(test['parts']['3']['passages'])} P4:{len(test['parts']['4']['passages'])}")

    with open(OUT_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print("Extracting Part 1 images...")
    extract_part1_images()

    # Copy audio symlinks info
    print("Done!")


if __name__ == "__main__":
    main()
