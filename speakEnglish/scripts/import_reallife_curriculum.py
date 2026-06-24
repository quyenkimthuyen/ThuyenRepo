#!/usr/bin/env python3
"""Import RealLifeEnglish curriculum (3 levels) → phrases + sentences topic JSON."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    from eng_to_ipa import convert as ipa_convert
except ImportError:
    print("Install: pip install eng-to-ipa", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[1]
CURRICULUM_JS = Path("/home/toc/thuyen/repo/RealLifeEnglish/src/curriculum.js")
TOPICS_DIR = REPO / "frontend" / "data" / "vocabulary" / "topics"
MANIFEST_PATH = REPO / "frontend" / "data" / "vocabulary" / "manifest.json"

TOPIC_MAP: dict[str, tuple[str, str]] = {
    "level-1": ("reallife-level-1", "Real Life L1 — Beginner Daily Life"),
    "level-2": ("reallife-level-2", "Real Life L2 — Daily Conversation"),
    "level-3": ("reallife-level-3", "Real Life L3 — Advanced Communication"),
}

KIND_EMOJI = {"phrase": "🗣️", "sentence": "💬"}


def ipa_to_phonemes(ipa: str) -> list[str]:
    clean = re.sub(r"[ˈˌ/]", "", ipa)
    tokens = re.findall(r"tʃ|dʒ|aʊ|aɪ|eɪ|oʊ|ɔɪ|ɜː|iː|uː|.|.", clean)
    return [t for t in tokens if t.strip()]


def norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def extract_levels() -> dict:
    js = f"""
import {{ levels }} from {json.dumps(CURRICULUM_JS.as_uri())};
const out = {{}};
for (const lv of levels) {{
  const items = [];
  for (const topic of lv.topics) {{
    for (const sit of topic.situations ?? []) {{
      for (const s of sit.sentences ?? []) {{
        items.push({{
          type: 'sentence',
          text: s.english,
          meaning: s.meaning,
          sourceTopic: topic.title,
          situation: sit.title,
        }});
      }}
      for (const p of sit.phrases ?? []) {{
        items.push({{
          type: 'phrase',
          text: p.phrase,
          meaning: p.meaning,
          sourceTopic: topic.title,
          situation: sit.title,
        }});
      }}
    }}
  }}
  out[lv.id] = {{ title: lv.title, subtitle: lv.subtitle, items }};
}}
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def dedupe_items(items: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    order: list[str] = []
    for it in items:
        key = norm_key(it["text"])
        if not key:
            continue
        if key not in seen:
            seen[key] = it
            order.append(key)
            continue
        if it["type"] == "sentence" and seen[key]["type"] == "phrase":
            seen[key] = it
    return [seen[k] for k in order]


def enrich_item(text: str, meaning: str, topic_id: str, kind: str) -> dict:
    word = text.strip()
    ipa_raw = ipa_convert(word) or word
    ipa = f"/{ipa_raw}/"
    phonemes = ipa_to_phonemes(ipa_raw) or list(word.lower())
    return {
        "word": word,
        "ipa": ipa,
        "phonemes": phonemes,
        "meaning": meaning or "",
        "emoji": KIND_EMOJI.get(kind, "💬"),
        "topic": topic_id,
        "kind": kind,
        "audio_sample_url": "",
    }


def update_manifest(new_topics: list[dict]) -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    new_ids = {t["id"] for t in new_topics}
    topics = [t for t in manifest.get("topics", []) if t["id"] not in new_ids]
    topics.extend(new_topics)
    topics.sort(key=lambda t: t["label"].lower())

    manifest["topics"] = topics
    manifest["totalTopics"] = len(topics)
    manifest["totalWords"] = sum(t["count"] for t in topics)
    source = manifest.get("source", "")
    if "RealLifeEnglish" not in source:
        manifest["source"] = f"{source}; RealLifeEnglish/curriculum.js".strip("; ")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    if not CURRICULUM_JS.is_file():
        print(f"Curriculum not found: {CURRICULUM_JS}", file=sys.stderr)
        sys.exit(1)

    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    levels = extract_levels()
    manifest_rows: list[dict] = []

    for level_id, (topic_id, label) in TOPIC_MAP.items():
        level = levels[level_id]
        items = dedupe_items(level["items"])
        words = [
            enrich_item(it["text"], it["meaning"], topic_id, it["type"])
            for it in items
        ]
        words.sort(key=lambda w: (w["kind"], w["word"].lower()))

        phrases = sum(1 for w in words if w["kind"] == "phrase")
        sentences = sum(1 for w in words if w["kind"] == "sentence")

        payload = {
            "topic": topic_id,
            "level": level_id,
            "label": label,
            "subtitle": level.get("subtitle", ""),
            "words": words,
        }
        out_path = TOPICS_DIR / f"{topic_id}.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest_rows.append({
            "id": topic_id,
            "label": label,
            "file": f"{topic_id}.json",
            "count": len(words),
        })
        print(f"{topic_id}: {len(words)} items ({phrases} phrases, {sentences} sentences)")

    update_manifest(manifest_rows)
    print(f"Updated manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
