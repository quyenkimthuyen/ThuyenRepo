#!/usr/bin/env python3
"""Import Global Success vocabulary into frontend/data/vocabulary/."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from eng_to_ipa import convert as ipa_convert
except ImportError:
    print("Install: pip install eng-to-ipa", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[1]
SRC_DIR = Path("/home/toc/thuyen/repo/GameDietTauNgam/global-success-vocabulary")
OUT_DIR = REPO / "frontend" / "data" / "vocabulary"
TOPICS_DIR = OUT_DIR / "topics"

SKIP_FILES = {"merged_all_grades.json", "quality_report.json"}
SOURCE_LABELS = {
    "grade1": "Lớp 1",
    "grade2": "Lớp 2",
    "grade3": "Lớp 3",
    "grade4": "Lớp 4",
    "grade5": "Lớp 5",
    "grade6": "Lớp 6",
    "grade7": "Lớp 7",
    "grade8": "Lớp 8",
    "grade9": "Lớp 9",
    "grade10": "Lớp 10",
    "grade11": "Lớp 11",
    "grade12": "Lớp 12",
    "toeic": "TOEIC",
}


def topic_id(label: str) -> str:
    key = label.strip().lower()
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"t-{digest}"


def ipa_to_phonemes(ipa: str) -> list[str]:
    clean = re.sub(r"[ˈˌ/]", "", ipa)
    tokens = re.findall(r"tʃ|dʒ|aʊ|aɪ|eɪ|oʊ|ɔɪ|ɜː|iː|uː|.|.", clean)
    return [t for t in tokens if t.strip()]


def enrich_word(entry: dict, source: str, grade: int | None) -> dict:
    word = str(entry.get("word", "")).strip()
    if not word:
        return {}

    ipa_raw = ipa_convert(word) or word
    ipa = f"/{ipa_raw}/"
    phonemes = ipa_to_phonemes(ipa_raw)
    if not phonemes:
        phonemes = list(word.lower())

    topic = str(entry.get("topic") or "Khác").strip()
    return {
        "word": word,
        "ipa": ipa,
        "phonemes": phonemes,
        "meaning": entry.get("meaning", ""),
        "emoji": entry.get("emoji", ""),
        "topic": topic,
        "topicId": topic_id(topic),
        "grade": grade if grade is not None else entry.get("grade"),
        "source": source,
        "audio_sample_url": "",
    }


def load_sources() -> list[tuple[str, list[dict]]]:
    sources: list[tuple[str, list[dict]]] = []
    for path in sorted(SRC_DIR.glob("*.json")):
        if path.name in SKIP_FILES:
            continue
        source_id = path.stem
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        grade = None
        m = re.match(r"grade(\d+)", source_id)
        if m:
            grade = int(m.group(1))
        sources.append((source_id, data, grade))  # type: ignore[arg-type]
    return sources  # type: ignore[return-value]


def main() -> None:
    if not SRC_DIR.is_dir():
        print(f"Source not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    TOPICS_DIR.mkdir(parents=True, exist_ok=True)

    by_topic: dict[str, list[dict]] = defaultdict(list)
    seen_per_topic: dict[str, set[str]] = defaultdict(set)
    source_meta: list[dict] = []
    total_raw = 0

    for source_id, rows, grade in load_sources():
        count = 0
        for row in rows:
            total_raw += 1
            item = enrich_word(row, source_id, grade)
            if not item:
                continue
            tid = item["topicId"]
            key = item["word"].lower()
            if key in seen_per_topic[tid]:
                continue
            seen_per_topic[tid].add(key)
            by_topic[tid].append(item)
            count += 1
        source_meta.append({
            "id": source_id,
            "label": SOURCE_LABELS.get(source_id, source_id),
            "wordCount": count,
        })

    topic_labels: dict[str, str] = {}
    for items in by_topic.values():
        for item in items:
            topic_labels[item["topicId"]] = item["topic"]

    topics_manifest = []
    for tid in sorted(by_topic.keys(), key=lambda x: topic_labels[x]):
        items = sorted(by_topic[tid], key=lambda w: w["word"].lower())
        out_path = TOPICS_DIR / f"{tid}.json"
        out_path.write_text(
            json.dumps({"topicId": tid, "label": topic_labels[tid], "words": items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        topics_manifest.append({
            "id": tid,
            "label": topic_labels[tid],
            "count": len(items),
        })

    topics_manifest.sort(key=lambda t: (-t["count"], t["label"]))

    manifest = {
        "version": 1,
        "source": "GameDietTauNgam/global-success-vocabulary",
        "totalWords": sum(t["count"] for t in topics_manifest),
        "totalTopics": len(topics_manifest),
        "defaultTopicId": topics_manifest[0]["id"] if topics_manifest else "",
        "defaultQuizSize": 30,
        "sources": source_meta,
        "topics": topics_manifest,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Built {manifest['totalWords']} words in {manifest['totalTopics']} topics (from {total_raw} raw rows)")
    print(f"Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
