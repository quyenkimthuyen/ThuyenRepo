from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRESETS_PATH = ROOT / "config" / "presets.json"

STRATEGY_TAG_KEYWORDS: dict[str, list[str]] = {
    "rsi_break_retest": [
        "rsi break",
        "break retest",
        "retest 50",
        "setup 1",
        "break_retest",
        "rsi_break_retest",
    ],
    "rsi_extreme_bounce": [
        "extreme bounce",
        "chạm 70",
        "chạm 30",
        "hồi 50",
        "setup 2",
        "extreme_bounce",
        "rsi_extreme_bounce",
    ],
    "ema_h1_confirm": [
        "ema h1",
        "ema50",
        "ema 50",
        "ema200",
        "hỗ trợ ema",
        "kháng cự ema",
        "ema_h1",
    ],
}


def load_presets() -> dict[str, Any]:
    if PRESETS_PATH.exists():
        return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    return {"tags": [], "notes": []}


def tag_keywords() -> dict[str, list[str]]:
    presets = load_presets()
    keywords = dict(STRATEGY_TAG_KEYWORDS)
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
    bar_tags = setup.get("bar_tags") or []
    for t in bar_tags:
        if t:
            tags.add(str(t).strip().lower())
    return sorted(tags)


def normalize_tags(raw: list[str] | str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = re.split(r"[,;]+", raw)
    else:
        parts = raw
    allowed = set(tag_keywords().keys())
    out = {p.strip().lower() for p in parts if p and str(p).strip()}
    return sorted(out.intersection(allowed) if allowed else out)


def strategy_tag_ids() -> list[str]:
    return sorted(tag_keywords().keys())
