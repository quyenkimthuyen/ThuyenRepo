"""Pipeline: nến → tag → setup → chiến lược → backtest."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .bar_annotations import load_bar_annotations, annotation_at_time
from .detection_config import load_bar_detection_config
from .tags import infer_tags, normalize_tags

PIPELINE_FLOW = "bar → tag → setup → strategy → backtest"


def context_bars_for_index(
    df: pd.DataFrame, idx: int, window: int | None = None
) -> list[dict[str, Any]]:
    cfg = load_bar_detection_config()
    window = window or int(cfg.get("sequence_window", 5))
    start = max(0, idx - window + 1)
    bars: list[dict[str, Any]] = []
    for i in range(start, idx + 1):
        ts = df.index[i]
        row = df.iloc[i]
        bars.append(
            {
                "time": ts.isoformat(),
                "open": round(float(row["open"]), 5),
                "high": round(float(row["high"]), 5),
                "low": round(float(row["low"]), 5),
                "close": round(float(row["close"]), 5),
                "is_entry": bool(i == idx),
            }
        )
    return bars


def validate_setup_from_bar(payload: dict[str, Any], *, is_create: bool) -> list[str]:
    """Ensure setup tags align with saved bar tags on create."""
    tags = normalize_tags(payload.get("tags"))
    if not tags:
        raise ValueError(
            "Setup phải có ít nhất 1 tag. Luồng: nến → gắn tag → tạo setup."
        )

    if not is_create:
        return tags

    ann = annotation_at_time(payload["entry_time"])
    if not ann or not ann.get("tags"):
        raise ValueError(
            "Luồng bắt buộc: nến → tag → setup. "
            "Hãy lưu tag nến tại thời điểm entry trước khi tạo setup."
        )

    bar_tags = set(normalize_tags(ann.get("tags")))
    if not bar_tags.intersection(tags):
        raise ValueError(
            "Tag setup phải khớp ít nhất 1 tag đã lưu trên nến entry."
        )
    return tags


def pipeline_status() -> dict[str, Any]:
    from .labels import load_setups

    from .periods import is_train_period, normalize_setup_period

    setups = [
        s for s in load_setups()
        if is_train_period(normalize_setup_period(s.get("period")))
    ]
    annotations = [a for a in load_bar_annotations() if a.get("confirmed") and a.get("tags")]
    tagged_setups = [s for s in setups if infer_tags(s)]
    linked = [s for s in setups if s.get("annotation_id") or s.get("bar_tags")]

    return {
        "flow": PIPELINE_FLOW,
        "bar_annotations": len(annotations),
        "setups": len(setups),
        "tagged_setups": len(tagged_setups),
        "setups_with_bar_context": len(linked),
        "ready_for_analyze": len([s for s in setups if s.get("result") in ("win", "loss")]) >= 5,
    }


def filter_train_setups(
    setups: list[dict[str, Any]],
    strategy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Reduce noise + speed similarity matching during backtest."""
    from .bar_annotations import load_bar_annotations
    from .setup_quality import enrich_setup_quality, load_quality_config

    strategy = strategy or {}
    filt = strategy.get("similarity_train_filter") or {}
    cfg = load_quality_config()
    exclude = set(filt.get("exclude_tags") or [])
    tag_info = strategy.get("tags") or {}
    exclude.update(tag_info.get("avoid_tags") or [])

    kept: list[dict[str, Any]] = []
    for setup in setups:
        if setup.get("result") not in ("win", "loss"):
            continue
        tags = infer_tags(setup)
        if exclude.intersection(tags):
            continue
        kept.append(setup)

    max_n = int(filt.get("max_setups") or cfg.get("target_setups_per_year", 50))
    min_q = float(filt.get("min_quality_score") or cfg.get("min_setup_quality_score", 0))

    ann_by_id = {a["id"]: a for a in load_bar_annotations()}

    scored: list[dict[str, Any]] = []
    for setup in kept:
        enriched = enrich_setup_quality(setup, ann_by_id)
        if enriched.get("quality_score", 0) < min_q:
            continue
        scored.append(enriched)

    kept = scored
    if len(kept) > max_n:
        kept.sort(
            key=lambda s: (
                -(s.get("quality_score") or 0),
                0 if s.get("result") == "win" else 1,
                -(s.get("planned_rr") or 0),
                s.get("entry_time") or "",
            )
        )
        kept = kept[:max_n]
    return kept
