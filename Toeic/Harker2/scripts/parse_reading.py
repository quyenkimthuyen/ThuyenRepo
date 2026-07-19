#!/usr/bin/env python3
"""Parse Hacker TOEIC Reading PDF into JSON."""

import fitz
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READING_PDF = ROOT / "data" / "HACKER Vol 2 RC" / "HACKER 2 READING.pdf"
ANSWERS_FILE = ROOT / "data" / "HACKER Vol 2 RC" / "reading_answers.json"
OUT_DIR = ROOT / "public" / "data" / "reading"
IMG_ROOT = ROOT / "public" / "images" / "reading"

PAGES_PER_TEST = 30
TEST_START_PAGE = 1  # 0-indexed: page 2 in PDF
RENDER_MATRIX = fitz.Matrix(2.5, 2.5)
PAGE_MARGIN = 24
FOOTER_MARGIN = 45
MIN_CLIP_HEIGHT = 20

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


def parse_part6(text: str) -> list[dict]:
    """Parse Part 6 with header-based blocks + gap fill for headerless passages."""
    m = re.search(r"PART\s*6(.+?)PART\s*7", text, re.DOTALL | re.I)
    if not m:
        return []
    section = m.group(1)

    groups = [(131, 134), (135, 138), (139, 142), (143, 146)]
    header_re = re.compile(
        r"Questions\s+(\d+)\s*[-–=]\s*(\d+)\s+refer[^\n]*\.\s*",
        re.I,
    )

    def extract_questions(q_from: int, q_to: int) -> list[dict]:
        questions = []
        for qnum in range(q_from, min(q_to, 146) + 1):
            opts = parse_question_options_block(section, qnum, 6)
            if len(opts) >= 2:
                questions.append({"id": qnum, "question": "", "options": opts})
        return questions

    def passage_text_for(q_from: int, q_to: int, block: str) -> str:
        first_opt = None
        for qn in range(q_from, min(q_to, 146) + 1):
            fm = re.search(rf"(?<!\d){qn}\.\s*\(A\)", block)
            if fm and (first_opt is None or fm.start() < first_opt.start()):
                first_opt = fm
        return clean_passage(block[: first_opt.start()]) if first_opt else clean_passage(block)

    raw: dict[int, dict] = {}

    splits = list(header_re.finditer(section))
    for i, sm in enumerate(splits):
        q_from, q_to = int(sm.group(1)), int(sm.group(2))
        if q_from > 146 or q_to < 131:
            continue
        q_to = min(q_to, 146)
        start = sm.end()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(section)
        block = section[start:end]
        type_m = re.search(r"following\s+(\w+)", sm.group(0), re.I)
        doc_type = (type_m.group(1) if type_m else "text").lower()
        raw[q_from] = {
            "questionIds": list(range(q_from, q_to + 1)),
            "type": doc_type,
            "passage": passage_text_for(q_from, q_to, block),
            "questions": extract_questions(q_from, q_to),
        }

    for g_from, g_to in groups:
        if g_from in raw and all(q in raw[g_from]["questionIds"] for q in range(g_from, g_to + 1)):
            continue

        fm = re.search(rf"(?<!\d){g_from}\.\s*\(A\)", section)
        if not fm:
            continue

        prev_end = 0
        if g_from > 131:
            prev_q = g_from - 1
            prev_m = re.search(rf"(?<!\d){prev_q}\.\s*\(A\)", section)
            if prev_m:
                tail = section[prev_m.start(): fm.start()]
                pd = re.search(r"\(D\)", tail)
                if pd:
                    prev_end = prev_m.start() + pd.end()

        block = section[prev_end:fm.start()]
        candidate = {
            "questionIds": list(range(g_from, g_to + 1)),
            "type": "text",
            "passage": passage_text_for(g_from, g_to, block),
            "questions": extract_questions(g_from, g_to),
        }
        if g_from in raw:
            existing = raw[g_from]
            if len(candidate["passage"]) > len(existing["passage"]):
                existing["passage"] = candidate["passage"]
            qmap = {q["id"]: q for q in existing["questions"]}
            for q in candidate["questions"]:
                qmap[q["id"]] = q
            existing["questions"] = sorted(qmap.values(), key=lambda q: q["id"])
        else:
            raw[g_from] = candidate

    passages = []
    for g_from, g_to in groups:
        if g_from in raw:
            p = raw[g_from]
            p["questionIds"] = list(range(g_from, g_to + 1))
            qmap = {q["id"]: q for q in p["questions"]}
            for qnum in range(g_from, g_to + 1):
                if qnum not in qmap:
                    opts = parse_question_options_block(section, qnum, 6)
                    if len(opts) >= 2:
                        qmap[qnum] = {"id": qnum, "question": "", "options": opts}
            p["questions"] = sorted(qmap.values(), key=lambda q: q["id"])
            passages.append(p)
        else:
            passages.append({
                "questionIds": list(range(g_from, g_to + 1)),
                "type": "text",
                "passage": "",
                "questions": extract_questions(g_from, g_to),
            })

    return passages


def parse_part6_7(text: str, part: int) -> list[dict]:
    if part == 6:
        return parse_part6(text)

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
        if q_from < 147:
            continue
        doc_type = (sm.group(3) or "text").lower()
        q_ids = list(range(q_from, q_to + 1))

        first_opt = None
        fm = re.search(rf"(?<!\d){q_from}\.\s+", block)
        if fm:
            first_opt = fm
        passage_text = clean_passage(block[: first_opt.start()]) if first_opt else clean_passage(block)

        questions = []
        for qnum in q_ids:
            qm = re.search(rf"(?<!\d){qnum}\.\s+(.+?)(?=\n\s*\(A\)|\(A\))", block, re.DOTALL)
            qtext = clean(qm.group(1)) if qm else ""
            opts = parse_question_options_block(block, qnum, 7)
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


def find_questions_top(page: fitz.Page, q_from: int, min_y: float, part: int) -> float | None:
    """Return y-coordinate where questions/options begin below min_y."""
    tops: list[float] = []
    if part == 6:
        patterns = [f"{q_from}. (A)", f"{q_from}.("]
    else:
        patterns = [f"{q_from}. ", f"{q_from}."]
    for pat in patterns:
        for rect in page.search_for(pat):
            if rect.y0 > min_y + 12:
                tops.append(rect.y0)
    return min(tops) - 8 if tops else None


def clip_passage_page(page: fitz.Page, top: float, bottom: float) -> fitz.Rect | None:
    rect = fitz.Rect(
        PAGE_MARGIN,
        top,
        page.rect.width - PAGE_MARGIN,
        bottom,
    )
    if rect.height < MIN_CLIP_HEIGHT:
        return None
    return rect


def render_clip(page: fitz.Page, rect: fitz.Rect):
    from PIL import Image

    pix = page.get_pixmap(matrix=RENDER_MATRIX, clip=rect)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def stitch_images(images: list) -> object | None:
    from PIL import Image

    if not images:
        return None
    width = max(im.width for im in images)
    height = sum(im.height for im in images)
    combined = Image.new("RGB", (width, height), (255, 255, 255))
    y = 0
    for im in images:
        if im.width < width:
            padded = Image.new("RGB", (width, im.height), (255, 255, 255))
            padded.paste(im, (0, 0))
            im = padded
        combined.paste(im, (0, y))
        y += im.height
    return combined


def extract_passage_image(
    doc: fitz.Document,
    test_num: int,
    part: int,
    passage: dict,
) -> str | None:
    q_from = passage["questionIds"][0]
    q_to = passage["questionIds"][-1]
    rel_path = f"images/reading/test{test_num:02d}/p{part}_{q_from}-{q_to}.png"
    out_path = ROOT / "public" / rel_path

    page_start = TEST_START_PAGE + (test_num - 1) * PAGES_PER_TEST
    page_end = min(page_start + PAGES_PER_TEST, len(doc))

    clips: list[tuple[fitz.Page, fitz.Rect]] = []
    collecting = False

    for pi in range(page_start, page_end):
        page = doc[pi]
        header = page.search_for(f"Questions {q_from}-{q_to} refer")

        if header:
            collecting = True
            top = header[0].y1 + 6
            q_top = find_questions_top(page, q_from, top, part)
            if q_top:
                rect = clip_passage_page(page, top, q_top)
                if rect:
                    clips.append((page, rect))
                collecting = False
            else:
                rect = clip_passage_page(page, top, page.rect.height - FOOTER_MARGIN)
                if rect:
                    clips.append((page, rect))
            continue

        if collecting:
            q_top = find_questions_top(page, q_from, 30, part)
            if q_top:
                rect = clip_passage_page(page, 36, q_top)
                if rect:
                    clips.append((page, rect))
                collecting = False
            else:
                rect = clip_passage_page(page, 36, page.rect.height - FOOTER_MARGIN)
                if rect:
                    clips.append((page, rect))
            continue

        # Headerless Part 6 passage (e.g. continues on next page without "Questions X-Y refer")
        if part == 6 and not clips:
            opt_markers = page.search_for(f"{q_from}. (A)")
            if not opt_markers:
                continue
            top = 40.0
            for marker in ("To:", "From:", "NOTICE", "Dear ", "ATTENTION"):
                for hit in page.search_for(marker):
                    if 30 < hit.y0 < opt_markers[0].y0:
                        top = min(top, hit.y0 - 4)
            q_top = opt_markers[0].y0 - 8
            rect = clip_passage_page(page, top, q_top)
            if rect:
                clips.append((page, rect))

    if not clips:
        return None

    images = [render_clip(page, rect) for page, rect in clips]
    combined = stitch_images(images)
    if combined is None:
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.save(str(out_path), optimize=True)
    return rel_path


def attach_passage_images(doc: fitz.Document, test: dict, test_num: int):
    for part_key in ("6", "7"):
        part = int(part_key)
        for passage in test["parts"][part_key]["passages"]:
            rel = extract_passage_image(doc, test_num, part, passage)
            if rel:
                passage["image"] = rel


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
        attach_passage_images(doc, test, test_num)

        p6img = sum(1 for p in part6 if p.get("image"))
        p7img = sum(1 for p in part7 if p.get("image"))

        out = OUT_DIR / f"test{test_num:02d}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(test, f, ensure_ascii=False, indent=2)

        p5 = len(part5)
        p6q = sum(len(p["questions"]) for p in part6)
        p7q = sum(len(p["questions"]) for p in part7)
        print(
            f"Test {test_num:02d}: P5={p5}/30 P6={p6q}/16 P7={p7q}/54 "
            f"images P6={p6img}/{len(part6)} P7={p7img}/{len(part7)}"
        )
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
