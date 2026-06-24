#!/usr/bin/env python3
"""Import vocabulary: one source file = one topic (filename = topic name)."""

from __future__ import annotations

import json
import re
import shutil
import sys
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


def ipa_to_phonemes(ipa: str) -> list[str]:
    clean = re.sub(r"[ˈˌ/]", "", ipa)
    tokens = re.findall(r"tʃ|dʒ|aʊ|aɪ|eɪ|oʊ|ɔɪ|ɜː|iː|uː|.|.", clean)
    return [t for t in tokens if t.strip()]


def enrich_word(entry: dict, topic_name: str) -> dict | None:
    word = str(entry.get("word", "")).strip()
    if not word:
        return None

    ipa_raw = ipa_convert(word) or word
    ipa = f"/{ipa_raw}/"
    phonemes = ipa_to_phonemes(ipa_raw)
    if not phonemes:
        phonemes = list(word.lower())

    return {
        "word": word,
        "ipa": ipa,
        "phonemes": phonemes,
        "meaning": entry.get("meaning", ""),
        "emoji": entry.get("emoji", ""),
        "topic": topic_name,
        "audio_sample_url": "",
    }


def main() -> None:
    if not SRC_DIR.is_dir():
        print(f"Source not found: {SRC_DIR}", file=sys.stderr)
        sys.exit(1)

    if TOPICS_DIR.exists():
        shutil.rmtree(TOPICS_DIR)
    TOPICS_DIR.mkdir(parents=True)

    topics_manifest: list[dict] = []
    total_words = 0
    total_raw = 0

    for path in sorted(SRC_DIR.glob("*.json")):
        if path.name in SKIP_FILES:
            continue

        topic_name = path.stem
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            continue

        seen: set[str] = set()
        words: list[dict] = []
        for row in rows:
            total_raw += 1
            item = enrich_word(row, topic_name)
            if not item:
                continue
            key = item["word"].lower()
            if key in seen:
                continue
            seen.add(key)
            words.append(item)

        words.sort(key=lambda w: w["word"].lower())
        out_path = TOPICS_DIR / f"{topic_name}.json"
        out_path.write_text(
            json.dumps({"topic": topic_name, "words": words}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        topics_manifest.append({
            "id": topic_name,
            "label": topic_name,
            "file": f"{topic_name}.json",
            "count": len(words),
        })
        total_words += len(words)

    topics_manifest.sort(key=lambda t: t["label"])

    manifest = {
        "version": 2,
        "source": "GameDietTauNgam/global-success-vocabulary",
        "topicNaming": "filename",
        "totalWords": total_words,
        "totalTopics": len(topics_manifest),
        "defaultTopicId": topics_manifest[0]["id"] if topics_manifest else "",
        "defaultQuizSize": 30,
        "topics": topics_manifest,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Built {total_words} words in {len(topics_manifest)} topic files (from {total_raw} raw rows)")
    print(f"Output: {TOPICS_DIR}")


if __name__ == "__main__":
    main()
