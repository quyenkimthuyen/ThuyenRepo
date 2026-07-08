from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRESETS_PATH = ROOT / "config" / "presets.json"

DEFAULT_TAG_KEYWORDS: dict[str, list[str]] = {
    "pullback": ["pullback", "pull back", "ema50", "ema 50", "ema bounce", "bounce"],
    "breakout": ["breakout", "break out"],
    "retest": ["retest", "re-test", "break retest"],
    "rejection": ["rejection", "reject", "pin bar", "pinbar"],
    "reversal": ["reversal", "reverse"],
    "trend": ["trend", "continuation"],
    "range": ["range", "sideway", "sideways", "đi ngang"],
    "liquidity": ["liquidity", "sweep", "liquidity sweep"],
}


def load_presets() -> dict[str, Any]:
    if PRESETS_PATH.exists():
        return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    return {"tags": [], "notes": []}


def tag_keywords() -> dict[str, list[str]]:
    presets = load_presets()
    keywords = dict(DEFAULT_TAG_KEYWORDS)
    for item in presets.get("tags", []):
        tag_id = item.get("id", "").strip().lower()
        if tag_id and tag_id not in keywords:
            keywords[tag_id] = [tag_id.replace("_", " ")]
    return keywords


def infer_tags(setup: dict[str, Any]) -> list[str]:
    tags = {t.strip().lower() for t in (setup.get("tags") or []) if t and str(t).strip()}
    note = (setup.get("note") or "").lower()
    for tag, keywords in tag_keywords().items():
        if any(kw in note for kw in keywords):
            tags.add(tag)
    return sorted(tags)


def normalize_tags(raw: list[str] | str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[,;]+", raw)
    else:
        parts = raw
    return sorted({p.strip().lower() for p in parts if p and str(p).strip()})
