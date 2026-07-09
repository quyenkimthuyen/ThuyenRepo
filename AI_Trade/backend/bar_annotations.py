from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .config import BAR_ANNOTATIONS_PATH, PIP
from .data_service import load_candles, period_for_timestamp
from .indicators import add_indicators
from .tags import infer_tags, normalize_tags


def _ensure_file() -> None:
    BAR_ANNOTATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BAR_ANNOTATIONS_PATH.exists():
        BAR_ANNOTATIONS_PATH.write_text(
            json.dumps({"annotations": []}, indent=2), encoding="utf-8"
        )


def load_bar_annotations() -> list[dict[str, Any]]:
    _ensure_file()
    payload = json.loads(BAR_ANNOTATIONS_PATH.read_text(encoding="utf-8"))
    return payload.get("annotations", [])


def save_bar_annotations(annotations: list[dict[str, Any]]) -> None:
    _ensure_file()
    BAR_ANNOTATIONS_PATH.write_text(
        json.dumps({"annotations": annotations}, indent=2), encoding="utf-8"
    )


def annotation_by_time(annotations: list[dict[str, Any]], bar_time: str) -> dict[str, Any] | None:
    ts = pd.Timestamp(bar_time)
    for ann in annotations:
        if pd.Timestamp(ann["bar_time"]) == ts:
            return ann
    return None


def annotation_at_time(bar_time: str) -> dict[str, Any] | None:
    ts = pd.Timestamp(bar_time)
    for ann in load_bar_annotations():
        if not ann.get("confirmed"):
            continue
        if abs((pd.Timestamp(ann["bar_time"]) - ts).total_seconds()) < 1:
            return ann
    return None


def enrich_annotation(
    payload: dict[str, Any], df: pd.DataFrame | None = None
) -> dict[str, Any]:
    df = df if df is not None else add_indicators(load_candles())
    bar_time = pd.Timestamp(payload["bar_time"])
    if bar_time.tz is None:
        bar_time = bar_time.tz_localize("UTC")
    else:
        bar_time = bar_time.tz_convert("UTC")

    if period_for_timestamp(bar_time) != "train":
        raise ValueError("Chỉ gắn tag nến trong năm Train (2022).")

    idx = df.index.get_indexer([bar_time], method="nearest")[0]
    row = df.iloc[idx]
    bar_ts = df.index[idx]
    close = float(payload.get("close") or row["close"])

    enriched = {
        **payload,
        "id": payload.get("id") or str(uuid.uuid4())[:8],
        "bar_time": bar_ts.isoformat(),
        "close": round(close, 5),
        "period": "train",
        "tags": normalize_tags(payload.get("tags")),
        "note": payload.get("note", ""),
        "confirmed": bool(payload.get("confirmed", True)),
        "auto_detected_tags": payload.get("auto_detected_tags") or [],
        "score": payload.get("score"),
        "features": {
            "rsi14": round(float(row.get("rsi14", 0)), 2),
            "ema50": round(float(row.get("ema50", 0)), 5),
            "ema200": round(float(row.get("ema200", 0)), 5),
            "atr14": round(float(row.get("atr14", 0)), 5),
            "trend_up": bool(row.get("trend_up", False)),
            "close_above_ema50": bool(row.get("close_above_ema50", False)),
            "close_above_ema200": bool(row.get("close_above_ema200", False)),
            "dist_ema50_pips": round((close - float(row.get("ema50", close))) / PIP, 1),
            "dist_ema200_pips": round((close - float(row.get("ema200", close))) / PIP, 1),
            "atr14_pips": round(float(row.get("atr14", 0)) / PIP, 1),
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if not enriched.get("created_at"):
        enriched["created_at"] = enriched["updated_at"]
    enriched["tags"] = infer_tags(enriched) or enriched["tags"]
    return enriched


def upsert_annotation(payload: dict[str, Any]) -> dict[str, Any]:
    df = add_indicators(load_candles())
    enriched = enrich_annotation(payload, df)
    annotations = load_bar_annotations()
    idx = next((i for i, a in enumerate(annotations) if a["id"] == enriched["id"]), None)
    if idx is None:
        bar_ts = pd.Timestamp(enriched["bar_time"])
        idx = next(
            (
                i
                for i, a in enumerate(annotations)
                if abs((pd.Timestamp(a["bar_time"]) - bar_ts).total_seconds()) < 1
            ),
            None,
        )
    if idx is not None:
        enriched["id"] = annotations[idx]["id"]
        enriched["created_at"] = annotations[idx].get("created_at", enriched["created_at"])
        annotations[idx] = enriched
    else:
        annotations.append(enriched)
    save_bar_annotations(annotations)
    return enriched


def delete_annotation(annotation_id: str) -> None:
    annotations = [a for a in load_bar_annotations() if a["id"] != annotation_id]
    save_bar_annotations(annotations)


def link_setup_to_annotation(annotation_id: str, setup_id: str) -> None:
    annotations = load_bar_annotations()
    changed = False
    for ann in annotations:
        if ann["id"] == annotation_id:
            ann["setup_id"] = setup_id
            changed = True
        elif ann.get("setup_id") == setup_id and ann["id"] != annotation_id:
            ann.pop("setup_id", None)
            changed = True
    if changed:
        save_bar_annotations(annotations)


def clear_setup_link(setup_id: str) -> None:
    annotations = load_bar_annotations()
    changed = False
    for ann in annotations:
        if ann.get("setup_id") == setup_id:
            ann.pop("setup_id", None)
            changed = True
    if changed:
        save_bar_annotations(annotations)


def annotations_as_learning_samples() -> list[dict[str, Any]]:
    """Shape compatible with tag/sequence signature builders."""
    samples = []
    for ann in load_bar_annotations():
        if not ann.get("confirmed") or not ann.get("tags"):
            continue
        samples.append(
            {
                "id": ann["id"],
                "entry_time": ann["bar_time"],
                "entry_price": ann["close"],
                "tags": ann["tags"],
                "features": ann.get("features"),
                "source": "bar_annotation",
                "result": "annotation",
            }
        )
    return samples


def annotation_index_by_time() -> dict[int, dict[str, Any]]:
    index: dict[int, dict[str, Any]] = {}
    for ann in load_bar_annotations():
        if not ann.get("confirmed"):
            continue
        ts = int(pd.Timestamp(ann["bar_time"]).timestamp())
        index[ts] = ann
    return index
