#!/usr/bin/env python3
"""Generate candidate bar tags + setups for a train year from important bars."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.bar_annotations import enrich_annotation, link_setup_to_annotation, load_bar_annotations, save_bar_annotations
from backend.bar_importance import scan_important_bars
from backend.config import PIP
from backend.data_service import load_candles, slice_period
from backend.entity_codes import assign_bar_code, assign_setup_code, display_setup_code
from backend.indicators import add_indicators
from backend.labels import enrich_setup, load_setups, save_setups
from backend.periods import default_train_period, filter_setups_for_train, period_config, resolve_period
from backend.setup_quality import apply_curation, load_quality_config, score_setup
from backend.tags import normalize_tags

PREFERRED_TAGS = ("rejection", "pullback", "retest", "trend")


def _pick_tags(item: dict) -> list[str]:
    """Pick 1 primary + optional 1 secondary tag — avoid tagging everything."""
    detected = sorted(
        (d for d in (item.get("detected_tags") or []) if d.get("tag")),
        key=lambda d: (-float(d.get("score", 0)), d["tag"]),
    )
    if detected:
        tags = [detected[0]["tag"]]
        for d in detected[1:]:
            if float(d.get("score", 0)) < 0.58:
                continue
            if d["tag"] in tags:
                continue
            if d["tag"] in PREFERRED_TAGS:
                tags.append(d["tag"])
                break
        return normalize_tags(tags)[:2]

    pool = list(dict.fromkeys([*(item.get("suggested_tags") or []), item.get("primary_tag")]))
    return normalize_tags([t for t in pool if t in PREFERRED_TAGS][:2] or pool[:2])


def _pick_direction(item: dict, row: pd.Series) -> str | None:
    direction = item.get("suggested_direction")
    if direction in ("long", "short"):
        return direction
    tags = set(_pick_tags(item))
    trend_up = bool(row.get("trend_up"))
    if "rejection" in tags:
        return "short" if float(row["close"]) >= float(row.get("ema50", row["close"])) else "long"
    return "long" if trend_up else "short"


def _sl_tp(direction: str, entry: float, atr: float, *, sl_mult: float, rr: float) -> tuple[float, float]:
    risk = sl_mult * atr
    if direction == "long":
        return entry - risk, entry + risk * rr
    return entry + risk, entry - risk * rr


def _tag_label(tags: list[str]) -> str:
    labels = {
        "pullback": "Pullback",
        "retest": "Retest",
        "rejection": "Rejection",
        "trend": "Trend",
        "breakout": "Breakout",
        "range": "Range",
    }
    return " + ".join(labels.get(t, t.title()) for t in tags)


def _worth_labeling(item: dict, tags: list[str], min_score: float) -> bool:
    if float(item.get("score") or 0) < min_score:
        return False
    tag_set = set(tags)
    if "rejection" in tag_set:
        return True
    if "pullback" in tag_set and "retest" in tag_set:
        return True
    if float(item.get("score") or 0) >= 70 and len(tag_set) >= 2:
        return True
    return False


def generate_candidates(
    train_period: str,
    *,
    min_score: float | None = None,
    max_bars: int = 400,
    sl_atr: float = 1.0,
    target_rr: float = 2.5,
    curate: bool = True,
) -> dict:
    train_period = resolve_period(train_period)
    year = period_config(train_period).get("year", train_period)
    qcfg = load_quality_config()
    min_score = float(min_score if min_score is not None else qcfg.get("min_bar_score", 55))
    target_rr = float(target_rr or qcfg.get("default_planned_rr", 2.5))

    ref_period = default_train_period()
    ref_setups = filter_setups_for_train(load_setups(), ref_period)
    if train_period != ref_period and not ref_setups:
        ref_setups = []

    scan = scan_important_bars(
        train_period,
        min_score=min_score,
        with_tags=True,
        max_bars=max_bars,
    )
    df = add_indicators(slice_period(load_candles(), train_period))

    existing_times = {
        pd.Timestamp(s["entry_time"]).tz_convert("UTC")
        for s in load_setups()
        if s.get("period") == train_period
    }

    new_annotations: list[dict] = []
    new_setups: list[dict] = []
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    for item in scan.get("bars") or []:
        tags = _pick_tags(item)
        if not _worth_labeling(item, tags, min_score):
            skipped += 1
            continue

        ts = pd.Timestamp(item["time"], unit="s", tz="UTC")
        if ts in existing_times:
            skipped += 1
            continue

        idx = df.index.get_indexer([ts], method="nearest")[0]
        if idx < 0:
            skipped += 1
            continue
        row = df.iloc[idx]
        bar_ts = df.index[idx]
        if abs((bar_ts - ts).total_seconds()) > 3600:
            skipped += 1
            continue

        direction = _pick_direction(item, row)
        if direction not in ("long", "short"):
            skipped += 1
            continue

        entry = float(row["close"])
        atr = float(row.get("atr14") or 0)
        if atr <= 0 or pd.isna(atr):
            skipped += 1
            continue

        sl, tp = _sl_tp(direction, entry, atr, sl_mult=sl_atr, rr=target_rr)
        reasons = item.get("reason_labels") or item.get("reasons") or []
        reason_txt = ", ".join(str(r) for r in reasons[:3])
        note = (
            f"Auto từ nến score {int(item.get('score', 0))} · "
            f"{_tag_label(tags)} · score {int(item.get('score', 0))}"
            + (f" · {reason_txt}" if reason_txt else "")
        )

        ann_payload = {
            "id": str(uuid.uuid4())[:8],
            "bar_time": bar_ts.isoformat(),
            "close": round(entry, 5),
            "tags": tags,
            "note": note,
            "confirmed": True,
            "auto_detected_tags": [d.get("tag") for d in (item.get("detected_tags") or []) if d.get("tag")],
            "score": float(item.get("score") or 0),
            "train_period": train_period,
        }
        ann = enrich_annotation(ann_payload, df)
        ann["code"] = assign_bar_code(ann, load_bar_annotations() + new_annotations)
        ann["period"] = train_period
        ann["created_at"] = now

        setup_payload = {
            "id": str(uuid.uuid4())[:8],
            "direction": direction,
            "entry_time": bar_ts.isoformat(),
            "entry_price": entry,
            "stop_loss": round(sl, 5),
            "take_profit": round(tp, 5),
            "tags": tags,
            "bar_tags": tags,
            "sequence_tags": [t.get("tag") for t in (item.get("sequence_tags") or []) if t.get("tag")],
            "annotation_id": ann["id"],
            "note": note,
            "period": train_period,
            "train_period": train_period,
        }
        setup = enrich_setup(setup_payload, df)
        setup["code"] = assign_setup_code(setup, load_setups() + new_setups)
        setup["period"] = train_period
        setup["created_at"] = now
        meta = score_setup(setup, annotation=ann)
        setup = {**setup, **meta}

        if float(setup.get("planned_rr") or 0) < target_rr - 0.01:
            skipped += 1
            continue

        new_annotations.append(ann)
        new_setups.append(setup)
        existing_times.add(bar_ts)

    other_ann = [
        a for a in load_bar_annotations() if a.get("period") != train_period
    ]
    other_setups = [
        s for s in load_setups() if s.get("period") != train_period
    ]

    save_bar_annotations(other_ann + new_annotations)
    save_setups(other_setups + new_setups)

    for ann, setup in zip(new_annotations, new_setups):
        link_setup_to_annotation(ann["id"], setup["id"], display_setup_code(setup))

    report = {
        "train_period": train_period,
        "year": year,
        "scanned": scan.get("count", 0),
        "generated": len(new_setups),
        "skipped": skipped,
        "min_score": min_score,
    }

    if curate and new_setups:
        curation = apply_curation(train_period=train_period)
        report["curation"] = curation
    elif curate:
        report["curation"] = apply_curation(train_period=train_period, dry_run=True)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate train labels from important bars")
    parser.add_argument("--period", default="train_2024", help="Train period id (default: train_2024)")
    parser.add_argument("--min-score", type=float, default=None, help="Min bar importance score")
    parser.add_argument("--max-bars", type=int, default=400, help="Max candidate bars to scan")
    parser.add_argument("--no-curate", action="store_true", help="Skip curation to 50 labels")
    parser.add_argument("--sl-atr", type=float, default=1.0, help="SL distance in ATR multiples")
    parser.add_argument("--rr", type=float, default=None, help="Target RR (default from quality.json)")
    args = parser.parse_args()

    report = generate_candidates(
        args.period,
        min_score=args.min_score,
        max_bars=args.max_bars,
        sl_atr=args.sl_atr,
        target_rr=args.rr or load_quality_config().get("default_planned_rr", 2.5),
        curate=not args.no_curate,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
