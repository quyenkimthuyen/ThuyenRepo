#!/usr/bin/env python3
"""Add Vietnamese translations to existing test JSON files."""

import json
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"
CACHE_FILE = DATA_DIR / "translation_cache.json"

translator = GoogleTranslator(source="en", target="vi")
cache: dict = {}


def load_cache():
    global cache
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            cache = json.load(f)


def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def translate(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 3:
        return ""
    if text in cache:
        return cache[text]
    try:
        if len(text) > 4500:
            parts = []
            for chunk in re.split(r"(?<=[.!?])\s+", text):
                if chunk.strip():
                    parts.append(translate(chunk.strip()))
            result = " ".join(p for p in parts if p)
        else:
            result = translator.translate(text)
            time.sleep(0.1)
        cache[text] = result
        return result
    except Exception as e:
        print(f"  Error: {e}")
        time.sleep(2)
        return ""


def process_test(path: Path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    tid = data["id"]
    print(f"Test {tid:02d}...")

    for q in data["parts"]["1"]["questions"]:
        if not q.get("translation"):
            q["translation"] = translate(" ".join(q["options"].values()))

    for q in data["parts"]["2"]["questions"]:
        if not q.get("translation"):
            text = q["question"] + " " + " ".join(q["options"].values())
            q["translation"] = translate(text)

    for pk in ["3", "4"]:
        for passage in data["parts"][pk]["passages"]:
            if not passage.get("translation") and passage.get("transcript"):
                passage["translation"] = translate(passage["transcript"].replace("\n", " "))
            for q in passage.get("questions", []):
                if not q.get("translation") and q.get("question"):
                    q["translation"] = translate(q["question"])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    save_cache()
    print(f"  Done test {tid:02d}")


def main():
    load_cache()
    tests = sorted(DATA_DIR.glob("test*.json"))
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None
    for path in tests:
        if path.name == "index.json":
            continue
        tid = int(re.search(r"\d+", path.stem).group())
        if only and tid != only:
            continue
        process_test(path)
    print("All translations complete!")


if __name__ == "__main__":
    main()
