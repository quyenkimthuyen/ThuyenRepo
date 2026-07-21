#!/usr/bin/env python3
"""Parse Hacker TOEIC Listening PDFs into JSON for the frontend app."""

import fitz
import json
import re
import os
import io
import time
from pathlib import Path

import numpy as np
from PIL import Image

try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "public" / "data"
IMG_DIR = ROOT / "public" / "images"
CACHE_FILE = OUT_DIR / "translation_cache.json"

TRANSCRIPT_PDF = DATA_DIR / "HACKER 2 LISTENING TRANSCRIPT.pdf"
LISTENING_PDF = DATA_DIR / "HACKER 2 LISTENING.pdf"
AUDIO_DIR = DATA_DIR / "AUDIO HACKER"

# Part 1 picture pages (3 pages × 2 photos = 6 questions) detected from PDF layout
PART1_PAGE_GROUPS = [
    [3, 4, 5], [17, 18, 19], [31, 32, 33], [45, 46, 47], [59, 60, 61],
    [73, 74, 75], [87, 88, 89], [101, 102, 103], [115, 116, 117], [129, 130, 131],
]

# Part 3/4 page ranges (1-indexed) per test
PART3_STARTS = [7, 21, 35, 49, 63, 77, 91, 105, 119, 133]
PART4_STARTS = [11, 25, 39, 53, 67, 81, 95, 109, 123, 137]

# Crop regions for 2 photos per page (PDF coordinates)
PHOTO_REGIONS = [
    fitz.Rect(25, 45, 525, 395),
    fitz.Rect(25, 405, 525, 735),
]

ACCENT_MAP = {
    "미국식": "Mỹ",
    "영국식": "Anh",
    "호주식": "Úc",
    "캐나다식": "Canada",
}

KOREAN_RE = re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]+")
COPYRIGHT_RE = re.compile(
    r"저작권|스크립트|해커스|배포|복제|Listening\s*$", re.I
)


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    s = s.replace("\t", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*\^\s*", " ", s)
    return s


def strip_non_english(s: str) -> str:
    """Remove Korean and copyright boilerplate."""
    if not s:
        return ""
    lines = []
    for line in s.split("\n"):
        line = KOREAN_RE.sub("", line).strip()
        if COPYRIGHT_RE.search(line):
            continue
        if line:
            lines.append(line)
    return strip_pdf_page_markers("\n".join(lines))


_SEQ_1_10_NL = r"1\n2\n3\n4\n5\n6\n7\n8\n9\n10"
_SEQ_1_10_SP = r"1\s+2\s+3\s+4\s+5\s+6\s+7\s+8\s+9\s+10"
_TEST_WORD = r"(?:TEST|KIỂM TRA|BÀI KIỂM TRA|THỬ NGHIỆM|Năm THỬ|THỬ)"
_1000 = r"1000\s*2"

PDF_MARKER_PATTERNS = [
    # multiline: page, 1000 2, ., 1-10, TEST
    rf"\n\d{{1,2}}\n{_1000}\n\.\n{_SEQ_1_10_NL}\n{_TEST_WORD}\b",
    rf"\n{_1000}\n\.\n{_SEQ_1_10_NL}\n{_TEST_WORD}\b",
    # multiline: page, 1-10, TEST, 1000 2, .
    rf"\n\d{{1,2}}\n{_SEQ_1_10_NL}\n{_TEST_WORD}\b\n{_1000}\n\.",
    rf"\n{_SEQ_1_10_NL}\n{_TEST_WORD}\b\n{_1000}\n\.",
    # multiline: page, 1000 2, ., TEST, 1-10
    rf"\n\d{{1,2}}\n{_1000}\n\.\n{_TEST_WORD}\b\n{_SEQ_1_10_NL}",
    rf"\n{_1000}\n\.\n{_TEST_WORD}\b\n{_SEQ_1_10_NL}",
    # partial footer at end of passage
    rf"\n\d{{1,2}}\n{_1000}\n\.",
    rf"\n{_1000}\n\.",
    # inline (translations): page 1000 2 . 1-10 TEST
    rf"(?:\s\d{{1,2}})?\s+{_1000}\s*\.?\s+{_SEQ_1_10_SP}(?:\s+\w+)*\s+{_TEST_WORD}\b",
    # inline: page 1-10 TEST 1000 2 .
    rf"\s\d{{1,2}}\s+{_SEQ_1_10_SP}(?:\s+\w+)*\s+{_TEST_WORD}\b\s+{_1000}\s*\.?",
    # inline: page 1000 2 . (partial, may sit inside a sentence)
    rf"\s\d{{1,2}}\s+{_1000}\s*\.?",
    # standalone at start
    rf"^{_1000}\s*\.?\s*",
]


def strip_pdf_page_markers(s: str) -> str:
    """Remove PDF footer circle markers (page num, 1000 2, 1-10, TEST)."""
    if not s:
        return ""
    for pattern in PDF_MARKER_PATTERNS:
        s = re.sub(pattern, "", s, flags=re.IGNORECASE)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


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
                if p and not KOREAN_RE.search(p):
                    parts.append(p)
            return " → ".join(parts) if parts else ""
    return ""


def parse_answers(block: str) -> dict[int, str]:
    answers = {}
    for m in re.finditer(r"(\d+)\s*\(([A-D])\)", block):
        answers[int(m.group(1))] = m.group(2)
    return answers


def parse_options(text: str) -> dict[str, str]:
    opts = {}
    for m in re.finditer(r"\(([A-D])\)\s*(.+?)(?=\([A-D]\)|$)", text, re.DOTALL):
        val = clean_text(m.group(2))
        if val and not KOREAN_RE.search(val):
            opts[m.group(1)] = val
    return opts


# ── Part 1 image extraction ──────────────────────────────────────────

def auto_crop_pixmap(pix) -> Image.Image:
    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
    arr = np.array(img)
    mask = arr < 240
    if not mask.any():
        return Image.open(io.BytesIO(pix.tobytes("png")))
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    pad = 8
    rmin, cmin = max(0, rmin - pad), max(0, cmin - pad)
    rmax, cmax = min(arr.shape[0], rmax + pad), min(arr.shape[1], cmax + pad)
    return img.crop((cmin, rmin, cmax, rmax))


def extract_part1_images(doc: fitz.Document):
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    mat = fitz.Matrix(3, 3)

    for test_idx, pages in enumerate(PART1_PAGE_GROUPS):
        test_num = test_idx + 1
        test_dir = IMG_DIR / f"test{test_num:02d}"
        test_dir.mkdir(parents=True, exist_ok=True)
        q_num = 1
        for page_num in pages:
            page = doc[page_num - 1]
            for region in PHOTO_REGIONS:
                pix = page.get_pixmap(matrix=mat, clip=region)
                img = auto_crop_pixmap(pix)
                out = test_dir / f"q{q_num:02d}.png"
                img.save(str(out), optimize=True)
                print(f"  Test {test_num:02d} Q{q_num}: {out.name} ({img.size[0]}×{img.size[1]})")
                q_num += 1


# ── Listening PDF question parser ────────────────────────────────────

def parse_questions_from_pages(doc, page_start, page_end, q_min, q_max) -> dict:
    """Robust line-based parser for Part 3/4 questions."""
    lines = []
    for i in range(page_start - 1, page_end):
        for line in doc[i].get_text("text").split("\n"):
            lines.append(line.rstrip())

    questions = {}
    pending_nums = []
    current_q = None
    current_lines = []
    in_options = False

    def flush():
        nonlocal current_q, current_lines, in_options
        if current_q is None:
            return
        body = "\n".join(current_lines)
        q = parse_single_question(body)
        if q:
            questions[current_q] = q
        current_q = None
        current_lines = []
        in_options = False

    def is_noise(stripped):
        if not stripped:
            return True
        if stripped.startswith("GO ON TO THE NEXT PAGE"):
            return True
        if re.match(r"PART\s*[34]", stripped, re.I):
            return True
        if re.match(r"TEST\s*\d+\s*PART", stripped, re.I):
            return True
        if re.match(r"Hackers\.co\.kr", stripped, re.I):
            return True
        if re.match(r"^\d+\s*\?\S+", stripped):  # footer garbage
            return True
        # Graphic table headers (no question number prefix)
        if re.match(r"^(Show Name|Channel|LEPA|FIRST-TIME|Locations?:|\*not participating)", stripped, re.I):
            return True
        if re.match(r"^(Wake-Up|Morning Buzz|Pennsylvania|Mornings with)", stripped, re.I):
            return True
        if re.match(r"^(Tulsa|Shelbyville|Reno|Carson City)\s*$", stripped, re.I):
            return True
        if re.match(r"^[\d\s\"%-]+$", stripped) and len(stripped) < 30:
            return True
        if re.match(r"^[mUHJi\s\\>;:'\^■°•\*]+$", stripped) and len(stripped) < 20:
            return True
        return False

    def looks_like_question(stripped):
        if re.match(r"^\([A-D]\)", stripped):
            return False
        if "?" in stripped:
            return True
        return bool(re.match(
            r"^(Who|What|Where|When|Why|How|Which|Look at|According|Where most|What type|"
            r"What does|What is|What are|What was|What will|Why does|Why was|Why is|"
            r"Why will|Where does|How many|How much|How long|How often)",
            stripped, re.I
        ))

    for line in lines:
        stripped = line.strip()
        if is_noise(stripped):
            continue

        # Question number only: "62." or "62. "
        m_num_only = re.match(r"^(\d+)\.\s*$", stripped)
        if m_num_only:
            qnum = int(m_num_only.group(1))
            if q_min <= qnum <= q_max:
                pending_nums.append(qnum)
            continue

        # Question number with text: "32. Who is the woman?"
        m_num_text = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if m_num_text:
            qnum = int(m_num_text.group(1))
            if q_min <= qnum <= q_max:
                flush()
                current_q = qnum
                pending_nums = [n for n in pending_nums if n != qnum]
                rest = m_num_text.group(2).strip()
                current_lines = [rest] if rest else []
                in_options = bool(re.match(r"^\([A-D]\)", rest))
            elif qnum > q_max:
                flush()
                break
            continue

        # New question text while working on previous (Q62-64 layout)
        if current_q is not None and in_options and looks_like_question(stripped):
            flush()
            if pending_nums:
                current_q = pending_nums.pop(0)
                current_lines = [stripped]
                in_options = False
            continue

        # Assign text to pending question number if no current question
        if pending_nums and current_q is None and looks_like_question(stripped):
            current_q = pending_nums.pop(0)
            current_lines = [stripped]
            in_options = False
            continue

        if current_q is not None:
            if re.match(r"^\([A-D]\)", stripped):
                in_options = True
            current_lines.append(stripped)

    flush()
    return questions


def parse_single_question(body: str) -> dict | None:
    body = strip_non_english(body)
    if not body:
        return None

    opt_match = re.search(r"\(A\)", body)
    if not opt_match:
        return None

    qtext = clean_text(body[: opt_match.start()])
    opts = parse_options(body[opt_match.start() :])
    if len(opts) < 2:
        return None

    # Clean OCR garbage from options (trailing junk after valid text)
    for letter, val in list(opts.items()):
        val = re.sub(r"\s+[mUHJi\s\\>;:'\^■°•\*]{3,}.*$", "", val)
        val = re.sub(r"\s+GO ON.*$", "", val, flags=re.I)
        opts[letter] = clean_text(val)

    return {"question": qtext, "options": opts}


# ── Transcript PDF parser ────────────────────────────────────────────

def parse_part1_2(section: str, part: int) -> list[dict]:
    questions = []
    chunks = re.split(r"(?=\n\s*\d+\s*\n)", "\n" + section)
    for chunk in chunks:
        m = re.match(r"\s*(\d+)\s*\n(.+)", chunk, re.DOTALL)
        if not m:
            continue
        qnum = int(m.group(1))
        body = strip_non_english(m.group(2).strip())
        if not body:
            continue
        lines = body.split("\n")
        accent_line = lines[0].strip() if lines else ""
        accent = parse_accent(accent_line)
        rest = "\n".join(lines[1:]) if len(lines) > 1 else body

        if part == 1:
            opts = parse_options(rest)
            if not opts:
                continue
            questions.append({"id": qnum, "accent": accent, "options": opts})
        else:
            opt_match = re.search(r"\([A-C]\)", rest)
            if opt_match:
                qtext = clean_text(rest[: opt_match.start()])
                opts = parse_options(rest[opt_match.start() :])
            else:
                qtext = clean_text(rest)
                opts = {}
            if not qtext or len(qtext) < 5 or COPYRIGHT_RE.search(qtext):
                continue
            questions.append({
                "id": qnum,
                "accent": accent,
                "question": qtext,
                "options": opts,
            })
    return questions


def parse_part3_4(section: str) -> list[dict]:
    passages = []
    pattern = r"Questions\s+(\d+)-(\d+)\s+refer to the following[^.]*\."
    splits = list(re.finditer(pattern, section, re.IGNORECASE))
    for i, m in enumerate(splits):
        start = m.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(section)
        block = strip_non_english(section[start:end].strip())
        q_from, q_to = int(m.group(1)), int(m.group(2))
        q_ids = list(range(q_from, q_to + 1))

        accent = ""
        transcript_lines = []
        for line in block.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "발음" in line or (re.search(r"[→]", line) and len(line) < 60):
                a = parse_accent(line)
                if a:
                    accent = a
                continue
            if KOREAN_RE.search(line):
                continue
            transcript_lines.append(line)

        transcript = strip_non_english("\n".join(transcript_lines))
        passages.append({
            "questionIds": q_ids,
            "accent": accent,
            "transcript": transcript,
        })
    return passages


def parse_test_block(block: str, test_num: int) -> dict:
    ak_match = re.search(r"Answer Keys\s*(.+?)(?=PART 1|\Z)", block, re.DOTALL)
    answers = parse_answers(ak_match.group(1)) if ak_match else {}

    part1_match = re.search(r"PART 1\s*(.+?)(?=PART 2)", block, re.DOTALL)
    part2_match = re.search(r"PART 2\s*(.+?)(?=PART 3)", block, re.DOTALL)
    part3_match = re.search(r"PART 3\s*(.+?)(?=PART 4)", block, re.DOTALL)
    part4_match = re.search(r"PART 4\s*(.+?)(?=TEST\s*\d|\Z)", block, re.DOTALL)

    part1 = parse_part1_2(part1_match.group(1), 1) if part1_match else []
    part2 = parse_part1_2(part2_match.group(1), 2) if part2_match else []
    part3 = parse_part3_4(part3_match.group(1)) if part3_match else []
    part4 = parse_part3_4(part4_match.group(1)) if part4_match else []

    for q in part1 + part2:
        q["answer"] = answers.get(q["id"], "")

    for passage in part3 + part4:
        for qid in passage["questionIds"]:
            passage.setdefault("answers", {})[str(qid)] = answers.get(qid, "")

    return {
        "id": test_num,
        "title": f"Test {test_num:02d}",
        "audio": f"audio/test{test_num:02d}.mp3",
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
        tests.append(parse_test_block(full_text[start:end], test_num))
    return tests


def merge_listening_questions(tests: list[dict], doc: fitz.Document):
    for test_idx, test in enumerate(tests):
        p3_start = PART3_STARTS[test_idx]
        p3_end = PART4_STARTS[test_idx] - 1
        p4_start = PART4_STARTS[test_idx]
        p4_end = PART3_STARTS[test_idx + 1] - 1 if test_idx + 1 < len(PART3_STARTS) else len(doc)

        p3_q = parse_questions_from_pages(doc, p3_start, p3_end, 32, 70)
        p4_q = parse_questions_from_pages(doc, p4_start, p4_end, 71, 100)

        for passage in test["parts"]["3"]["passages"]:
            passage["questions"] = []
            for qid in passage["questionIds"]:
                qdata = p3_q.get(qid, {})
                passage["questions"].append({
                    "id": qid,
                    "question": qdata.get("question", ""),
                    "options": qdata.get("options", {}),
                    "answer": test["answers"].get(str(qid), ""),
                })

        for passage in test["parts"]["4"]["passages"]:
            passage["questions"] = []
            for qid in passage["questionIds"]:
                qdata = p4_q.get(qid, {})
                passage["questions"].append({
                    "id": qid,
                    "question": qdata.get("question", ""),
                    "options": qdata.get("options", {}),
                    "answer": test["answers"].get(str(qid), ""),
                })


def fix_audio_paths(tests: list[dict]):
    for test in tests:
        preferred = AUDIO_DIR / f"test{test['id']:02d}.mp3"
        if preferred.exists():
            test["audio"] = f"audio/test{test['id']:02d}.mp3"
            continue
        # Legacy fallback: match by test number in filename
        audio_files = {}
        for f in AUDIO_DIR.glob("*.mp3"):
            key = re.sub(r"[^0-9]", "", f.stem)
            audio_files[key] = f.name
        key = str(test["id"])
        if key in audio_files:
            test["audio"] = f"audio/{audio_files[key]}"


# ── Vietnamese translation ───────────────────────────────────────────

_translation_cache: dict = {}
_translator = None


def load_translation_cache():
    global _translation_cache
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            _translation_cache = json.load(f)


def save_translation_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(_translation_cache, f, ensure_ascii=False, indent=2)


def translate_text(text: str) -> str:
    if not text or not HAS_TRANSLATOR:
        return ""
    text = clean_text(text.replace("\n", " "))
    if len(text) < 3:
        return ""
    if text in _translation_cache:
        return _translation_cache[text]

    global _translator
    if _translator is None:
        _translator = GoogleTranslator(source="en", target="vi")

    try:
        # Split long text into chunks (Google limit ~5000 chars)
        if len(text) > 4500:
            chunks = []
            sentences = re.split(r"(?<=[.!?])\s+", text)
            current = ""
            for s in sentences:
                if len(current) + len(s) > 4000:
                    if current:
                        chunks.append(current)
                    current = s
                else:
                    current = (current + " " + s).strip()
            if current:
                chunks.append(current)
            result = " ".join(translate_text(c) for c in chunks)
        else:
            result = _translator.translate(text)
            time.sleep(0.15)
        _translation_cache[text] = result
        return result
    except Exception as e:
        print(f"    Translation error: {e}")
        return ""


def add_translations(tests: list[dict]):
    if not HAS_TRANSLATOR:
        print("  deep-translator not available, skipping translations")
        return

    load_translation_cache()
    total = 0
    for test in tests:
        tid = test["id"]
        print(f"  Translating Test {tid:02d}...")
        for q in test["parts"]["1"]["questions"]:
            opts_text = " ".join(q["options"].values())
            q["translation"] = translate_text(opts_text)

        for q in test["parts"]["2"]["questions"]:
            full = q["question"] + " " + " ".join(q["options"].values())
            q["translation"] = translate_text(full)

        for part_key in ["3", "4"]:
            for passage in test["parts"][part_key]["passages"]:
                passage["translation"] = translate_text(passage["transcript"])
                for q in passage.get("questions", []):
                    if q.get("question"):
                        q["translation"] = translate_text(q["question"])
        total += 1
        if total % 2 == 0:
            save_translation_cache()

    save_translation_cache()


def main():
    import sys
    skip_translate = "--skip-translate" in sys.argv

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Extracting Part 1 images...")
    listening_doc = fitz.open(str(LISTENING_PDF))
    extract_part1_images(listening_doc)

    print("Parsing transcript PDF...")
    tests = parse_transcript_pdf()
    print(f"  Found {len(tests)} tests")

    print("Parsing listening questions (Part 3/4)...")
    merge_listening_questions(tests, listening_doc)

    fix_audio_paths(tests)

    print("Adding Vietnamese translations..." if not skip_translate else "Skipping translations.")
    if not skip_translate:
        add_translations(tests)

    index = []
    for test in tests:
        out_path = OUT_DIR / f"test{test['id']:02d}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(test, f, ensure_ascii=False, indent=2)
        p3q = sum(len(p.get("questions", [])) for p in test["parts"]["3"]["passages"])
        p3ok = sum(1 for p in test["parts"]["3"]["passages"]
                   for q in p.get("questions", []) if q.get("question"))
        index.append({"id": test["id"], "title": test["title"], "file": f"test{test['id']:02d}.json"})
        print(f"  test{test['id']:02d}: P3 questions {p3ok}/{p3q}")

    with open(OUT_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print("Done!")


if __name__ == "__main__":
    main()
