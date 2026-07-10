"""Score and curate train setups — target ~50 high-quality labels per year."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .bar_annotations import load_bar_annotations, save_bar_annotations
from .config import LABELS_PATH, ROOT

QUALITY_PATH = ROOT / "config" / "quality.json"
SETUPS_ARCHIVE_PATH = LABELS_PATH.parent / "setups_archive.json"
BAR_ARCHIVE_PATH = LABELS_PATH.parent / "bar_annotations_archive.json"


def load_quality_config() -> dict[str, Any]:
    if not QUALITY_PATH.exists():
        return {}
    return json.loads(QUALITY_PATH.read_text(encoding="utf-8"))


def _cfg() -> dict[str, Any]:
    return load_quality_config()


def score_setup(
    setup: dict[str, Any],
    *,
    annotation: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return quality score 0–100 and reason chips for a setup."""
    cfg = config or _cfg()
    weights = cfg.get("scoring") or {}
    reasons: list[str] = []
    pts = 0

    bar_score = None
    if annotation:
        bar_score = annotation.get("score")
    if bar_score is None and setup.get("bar_score") is not None:
        bar_score = setup.get("bar_score")

    if bar_score is not None:
        if bar_score >= 75:
            pts += int(weights.get("bar_score_75", 30))
            reasons.append("bar_score_high")
        elif bar_score >= 65:
            pts += int(weights.get("bar_score_65", 20))
            reasons.append("bar_score_good")
        elif bar_score >= 55:
            pts += int(weights.get("bar_score_55", 10))
            reasons.append("bar_score_ok")
        else:
            reasons.append("bar_score_low")

    tags = set(setup.get("tags") or [])
    if "rejection" in tags:
        pts += int(weights.get("rejection_tag", 15))
        reasons.append("rejection")
    if "pullback" in tags and "retest" in tags:
        pts += int(weights.get("pullback_retest", 10))
        reasons.append("pullback_retest")
    if len(tags) >= 4:
        pts -= int(weights.get("over_tag_penalty", 10))
        reasons.append("over_tagged")

    features = setup.get("features") or {}
    dist50 = abs(float(features.get("dist_ema50_pips", 99)))
    if dist50 <= 8:
        pts += int(weights.get("ema_near_8_pips", 15))
        reasons.append("near_ema50")
    elif dist50 <= 15:
        pts += int(weights.get("ema_near_15_pips", 8))
        reasons.append("ema50_ok")

    trend_up = bool(features.get("trend_up"))
    direction = setup.get("direction", "long")
    if (direction == "long" and trend_up) or (direction == "short" and not trend_up):
        pts += int(weights.get("trend_aligned", 12))
        reasons.append("trend_aligned")

    rsi = float(features.get("rsi14", 50))
    if 35 <= rsi <= 65:
        pts += int(weights.get("rsi_sweet_spot", 8))
        reasons.append("rsi_ok")

    rr = float(setup.get("planned_rr") or 0)
    rr_min = float(weights.get("min_rr_threshold", 2.5))
    if rr >= rr_min:
        pts += int(weights.get("min_rr_bonus", 5))
        reasons.append("rr_ok")

    if setup.get("result") == "win":
        pts += int(cfg.get("prefer_win_bonus", 10))
        reasons.append("win")

    score = max(0, min(100, pts))
    return {
        "quality_score": score,
        "quality_reasons": reasons,
        "bar_score": bar_score,
    }


def passes_quality_gate(
    setup: dict[str, Any],
    *,
    annotation: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    cfg = config or _cfg()
    scored = score_setup(setup, annotation=annotation, config=cfg)
    min_q = float(cfg.get("min_setup_quality_score", 55))
    min_rr = float(cfg.get("min_planned_rr", 2.0))
    min_bar = float(cfg.get("min_bar_score", 55))

    if float(setup.get("planned_rr") or 0) < min_rr:
        return False, f"RR tối thiểu {min_rr} — setup hiện {setup.get('planned_rr')}"

    bar_score = scored.get("bar_score")
    if bar_score is not None and bar_score < min_bar:
        return False, f"Score nến {bar_score} < ngưỡng {min_bar}"

    if scored["quality_score"] < min_q:
        return False, f"Điểm chất lượng {scored['quality_score']} < {min_q}"

    return True, ""


def _too_close(
    setup: dict[str, Any],
    selected: list[dict[str, Any]],
    spacing_hours: int,
) -> bool:
    ts = pd.Timestamp(setup["entry_time"])
    for prev in selected:
        if prev.get("direction") != setup.get("direction"):
            continue
        pt = pd.Timestamp(prev["entry_time"])
        if abs((ts - pt).total_seconds()) < spacing_hours * 3600:
            return True
    return False


def curate_train_setups(
    setups: list[dict[str, Any]] | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pick top-quality setups spread across the year."""
    from .labels import load_setups

    cfg = config or _cfg()
    from .periods import filter_setups_for_train

    train = filter_setups_for_train(
        setups if setups is not None else load_setups(),
    )
    annotations = load_bar_annotations()
    ann_by_id = {a["id"]: a for a in annotations}

    target = int(cfg.get("target_setups_per_year", 50))
    max_month = int(cfg.get("max_setups_per_month", 5))
    spacing = int(cfg.get("min_spacing_hours", 48))

    scored_items: list[tuple[int, dict[str, Any]]] = []
    for setup in train:
        ann = ann_by_id.get(setup.get("annotation_id", ""))
        meta = score_setup(setup, annotation=ann, config=cfg)
        enriched = {**setup, **meta}
        scored_items.append((meta["quality_score"], enriched))

    scored_items.sort(key=lambda item: (-item[0], item[1].get("entry_time", "")))

    selected: list[dict[str, Any]] = []
    by_month: dict[str, int] = {}

    for _score, setup in scored_items:
        if len(selected) >= target:
            break
        month = str(setup.get("entry_time", ""))[:7]
        if by_month.get(month, 0) >= max_month:
            continue
        if _too_close(setup, selected, spacing):
            continue
        selected.append(setup)
        by_month[month] = by_month.get(month, 0) + 1

    selected_ids = {s["id"] for s in selected}
    rejected = [s for s in train if s["id"] not in selected_ids]

    wins = sum(1 for s in selected if s.get("result") == "win")
    resolved = sum(1 for s in selected if s.get("result") in ("win", "loss"))

    return {
        "selected": selected,
        "rejected": rejected,
        "selected_ids": list(selected_ids),
        "stats": {
            "before": len(train),
            "after": len(selected),
            "rejected": len(rejected),
            "win_rate": round(wins / resolved, 3) if resolved else 0,
            "avg_quality_score": round(
                sum(s.get("quality_score", 0) for s in selected) / len(selected), 1
            )
            if selected
            else 0,
            "by_month": by_month,
        },
    }


def curate_bar_annotations(
    selected_setup_ids: set[str],
    selected_annotation_ids: set[str],
    annotations: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep annotations linked to curated setups only."""
    all_ann = annotations if annotations is not None else load_bar_annotations()
    kept = []
    rejected = []
    for ann in all_ann:
        ann_id = ann.get("id")
        setup_id = ann.get("setup_id")
        if ann_id in selected_annotation_ids or setup_id in selected_setup_ids:
            kept.append(ann)
        else:
            rejected.append(ann)
    return kept, rejected


def apply_curation(*, dry_run: bool = False) -> dict[str, Any]:
    """Archive rejected labels and persist curated train set."""
    from .labels import load_setups, save_setups

    result = curate_train_setups()
    selected = result["selected"]
    rejected = result["rejected"]

    selected_ids = {s["id"] for s in selected}
    selected_ann_ids = {s.get("annotation_id") for s in selected if s.get("annotation_id")}

    from .periods import is_train_period, normalize_setup_period

    all_setups = load_setups()
    non_train = [s for s in all_setups if not is_train_period(normalize_setup_period(s.get("period")))]
    new_setups = non_train + selected

    all_ann = load_bar_annotations()
    kept_ann, rejected_ann = curate_bar_annotations(selected_ids, selected_ann_ids, all_ann)

    report = {
        **result["stats"],
        "annotations_before": len(all_ann),
        "annotations_after": len(kept_ann),
        "dry_run": dry_run,
    }

    if dry_run:
        return report

    SETUPS_ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETUPS_ARCHIVE_PATH.write_text(
        json.dumps({"setups": rejected, "archived_at": pd.Timestamp.utcnow().isoformat()}, indent=2),
        encoding="utf-8",
    )
    BAR_ARCHIVE_PATH.write_text(
        json.dumps(
            {"annotations": rejected_ann, "archived_at": pd.Timestamp.utcnow().isoformat()},
            indent=2,
        ),
        encoding="utf-8",
    )
    save_setups(new_setups)
    save_bar_annotations(kept_ann)
    return report


def enrich_setup_quality(
    setup: dict[str, Any],
    annotations_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ann = None
    if annotations_by_id and setup.get("annotation_id"):
        ann = annotations_by_id.get(setup["annotation_id"])
    meta = score_setup(setup, annotation=ann)
    return {**setup, **meta}
