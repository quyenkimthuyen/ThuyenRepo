from __future__ import annotations

import re
from typing import Any

TAG_KEYWORDS: dict[str, list[str]] = {
    "pullback": ["pullback", "pull back", "ema50", "ema 50", "ema bounce", "bounce"],
    "breakout": ["breakout", "break out"],
    "retest": ["retest", "re-test", "break retest"],
    "rejection": ["rejection", "reject", "pin bar", "pinbar"],
    "reversal": ["reversal", "reverse"],
    "trend": ["trend", "continuation"],
}


def infer_tags(setup: dict[str, Any]) -> list[str]:
    tags = {t.strip().lower() for t in (setup.get("tags") or []) if t and str(t).strip()}
    note = (setup.get("note") or "").lower()
    for tag, keywords in TAG_KEYWORDS.items():
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
