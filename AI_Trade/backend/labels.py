from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .bar_annotations import annotation_at_time, link_setup_to_annotation
from .config import LABELS_PATH, PIP
from .data_service import load_candles, period_for_timestamp
from .periods import (
    default_train_period,
    is_train_period,
    normalize_setup_period,
    period_config,
    resolve_period,
    timestamp_in_period,
)
from .detection_config import load_bar_detection_config
from .entity_codes import assign_setup_code, display_bar_code, display_setup_code
from .indicators import add_indicators
from .strategy_registry import dist_ema_pips, infer_setup_tags
from .pipeline import context_bars_for_index, validate_setup_from_bar
from .tags import normalize_tags


def _ensure_file() -> None:
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LABELS_PATH.exists():
        LABELS_PATH.write_text(json.dumps({"setups": []}, indent=2), encoding="utf-8")


def load_setups() -> list[dict[str, Any]]:
    _ensure_file()
    payload = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    return payload.get("setups", [])


def save_setups(setups: list[dict[str, Any]]) -> None:
    _ensure_file()
    LABELS_PATH.write_text(json.dumps({"setups": setups}, indent=2), encoding="utf-8")


def planned_rr(direction: str, entry: float, sl: float, tp: float) -> float:
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    return round(reward / risk, 2) if risk > 0 else 0.0


def resolve_outcome(
    df: pd.DataFrame,
    entry_time: pd.Timestamp,
    direction: str,
    sl: float,
    tp: float,
) -> tuple[str, pd.Timestamp | None]:
    """Walk forward from entry bar; return win/loss/open."""
    future = df.loc[entry_time:]
    if future.empty:
        return "pending", None

    for ts, row in future.iloc[1:].iterrows():
        high, low = float(row["high"]), float(row["low"])
        if direction == "long":
            hit_sl = low <= sl
            hit_tp = high >= tp
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp

        if hit_sl and hit_tp:
            return "loss", ts
        if hit_sl:
            return "loss", ts
        if hit_tp:
            return "win", ts
    return "open", None


def enrich_setup(
    setup: dict[str, Any],
    df: pd.DataFrame | None = None,
    *,
    strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    df = df if df is not None else add_indicators(load_candles())
    entry_time = pd.Timestamp(setup["entry_time"])
    if entry_time.tz is None:
        entry_time = entry_time.tz_localize("UTC")
    else:
        entry_time = entry_time.tz_convert("UTC")

    nearest_idx = df.index.get_indexer([entry_time], method="nearest")[0]
    bar_time = df.index[nearest_idx]
    row = df.iloc[nearest_idx]
    cfg = load_bar_detection_config()
    window = int(cfg.get("sequence_window", 5))
    ann = annotation_at_time(setup.get("entry_time") or bar_time.isoformat())

    direction = setup["direction"]
    entry = float(setup["entry_price"])
    sl = float(setup["stop_loss"])
    tp = float(setup["take_profit"])

    result, exit_time = resolve_outcome(df, bar_time, direction, sl, tp)

    period = normalize_setup_period(setup.get("period")) or period_for_timestamp(bar_time)
    if strategy is None:
        from .analyzer import load_strategy

        strat = load_strategy(period, setup.get("strategy_id"))
    else:
        strat = strategy
    classification = infer_setup_tags(df, nearest_idx, direction, strat)
    auto_tags = classification.get("tags") or []
    manual_tags = normalize_tags(setup.get("tags"))
    merged_tags = sorted(set(auto_tags) | set(manual_tags))
    if not merged_tags and classification.get("tag"):
        merged_tags = [classification["tag"]]

    rsi_h4 = float(row.get("rsi14_h4", 50)) if pd.notna(row.get("rsi14_h4")) else None
    bands = (strat or {}).get("bands") or {"low": [28, 32], "mid": [48, 52], "high": [68, 72]}
    mid = bands.get("mid", [48, 52])

    enriched = {
        **setup,
        "code": setup.get("code") or display_setup_code(setup),
        "entry_time": bar_time.isoformat(),
        "planned_rr": planned_rr(direction, entry, sl, tp),
        "result": result,
        "exit_time": exit_time.isoformat() if exit_time is not None else None,
        "period": period,
        "strategy_id": (strat or {}).get("strategy_id") or setup.get("strategy_id"),
        "tags": merged_tags,
        "strategy_setup": classification.get("setup"),
        "context_bars": setup.get("context_bars")
        or context_bars_for_index(df, nearest_idx, window),
        "bar_tags": setup.get("bar_tags") or (ann.get("tags") if ann else []),
        "sequence_tags": setup.get("sequence_tags") or [],
        "annotation_id": setup.get("annotation_id") or (ann.get("id") if ann else None),
        "features": {
            "ema50": round(float(row.get("ema50", 0)), 5),
            "ema200": round(float(row.get("ema200", 0)), 5),
            "atr14": round(float(row.get("atr14", 0)), 5),
            "rsi14_h4": round(rsi_h4, 1) if rsi_h4 is not None else None,
            "rsi_h4_zone": (
                "high"
                if rsi_h4 is not None and rsi_h4 >= bands.get("high", [68, 72])[0]
                else "low"
                if rsi_h4 is not None and rsi_h4 <= bands.get("low", [28, 32])[1]
                else "mid"
                if rsi_h4 is not None and mid[0] <= rsi_h4 <= mid[1]
                else "neutral"
            ),
            "strategy_setup": classification.get("setup"),
            "trend_up": bool(row.get("trend_up", False)),
            "close_above_ema50": bool(row.get("close_above_ema50", False)),
            "close_above_ema200": bool(row.get("close_above_ema200", False)),
            **dist_ema_pips(row, strat),
        },
    }
    return enriched


def retag_all_setups(strategy_id: str | None = None) -> int:
    """Gắn lại tag theo chiến lược đang chọn."""
    from .bar_annotations import load_bar_annotations, save_bar_annotations
    from .strategy_registry import default_strategy_id, resolve_strategy_id

    sid = resolve_strategy_id(strategy_id or default_strategy_id())
    df = add_indicators(load_candles())
    setups = load_setups()
    changed = 0
    setup_by_ann: dict[str, dict[str, Any]] = {}
    for i, setup in enumerate(setups):
        period = normalize_setup_period(setup.get("period"))
        from .analyzer import load_strategy

        strat = load_strategy(period, sid) or {"strategy_id": sid}
        enriched = enrich_setup(setup, df, strategy=strat)
        if (
            enriched.get("tags") != setup.get("tags")
            or enriched.get("strategy_setup") != setup.get("strategy_setup")
            or enriched.get("strategy_id") != setup.get("strategy_id")
        ):
            changed += 1
        setups[i] = enriched
        ann_id = enriched.get("annotation_id")
        if ann_id:
            setup_by_ann[ann_id] = enriched
    save_setups(setups)

    annotations = load_bar_annotations()
    ann_changed = 0
    for ann in annotations:
        setup = setup_by_ann.get(ann.get("id"))
        if not setup:
            continue
        new_tags = setup.get("tags") or []
        if new_tags and set(ann.get("tags") or []) != set(new_tags):
            ann["tags"] = new_tags
            ann_changed += 1
    if ann_changed:
        save_bar_annotations(annotations)
    return changed + ann_changed


def restore_missing_bar_annotations(train_period: str | None = None) -> dict[str, Any]:
    """Tạo lại bar annotation cho setup thiếu link (vd. sau curation ghi đè file)."""
    from .bar_annotations import enrich_annotation, load_bar_annotations, save_bar_annotations
    from .entity_codes import assign_bar_code

    period = resolve_period(train_period or default_train_period())
    df = add_indicators(load_candles())
    setups = load_setups()
    annotations = load_bar_annotations()
    ann_by_id = {a["id"]: a for a in annotations}
    restored = 0

    for i, setup in enumerate(setups):
        if normalize_setup_period(setup.get("period")) != period:
            continue
        ann_id = setup.get("annotation_id")
        if ann_id and ann_id in ann_by_id:
            continue

        payload: dict[str, Any] = {
            "bar_time": setup["entry_time"],
            "close": setup["entry_price"],
            "tags": setup.get("tags") or [],
            "note": setup.get("note", ""),
            "train_period": period,
            "confirmed": True,
        }
        enriched = enrich_annotation(payload, df)
        enriched["tags"] = [t for t in (setup.get("tags") or []) if t]
        enriched["auto_detected_tags"] = setup.get("bar_tags") or []
        enriched["setup_id"] = setup["id"]
        enriched["setup_code"] = setup.get("code")
        if not enriched.get("code"):
            enriched["code"] = assign_bar_code(enriched, annotations)

        annotations.append(enriched)
        ann_by_id[enriched["id"]] = enriched
        setup["annotation_id"] = enriched["id"]
        setups[i] = setup
        restored += 1

    if restored:
        save_bar_annotations(annotations)
        save_setups(setups)
    return {"train_period": period, "restored": restored, "annotations_total": len(annotations)}


def setup_summary(setup: dict[str, Any], *, bar_lookup: dict[str, dict] | None = None) -> dict[str, Any]:
    ann_id = setup.get("annotation_id")
    bar = bar_lookup.get(ann_id) if bar_lookup and ann_id else None
    return {
        "id": setup.get("id"),
        "code": display_setup_code(setup),
        "direction": setup.get("direction"),
        "entry_time": setup.get("entry_time"),
        "entry_price": setup.get("entry_price"),
        "stop_loss": setup.get("stop_loss"),
        "take_profit": setup.get("take_profit"),
        "planned_rr": setup.get("planned_rr"),
        "result": setup.get("result"),
        "tags": setup.get("tags") or [],
        "bar_tags": setup.get("bar_tags") or [],
        "sequence_tags": setup.get("sequence_tags") or [],
        "annotation_id": ann_id,
        "bar_code": display_bar_code(bar) if bar else None,
        "context_bar_count": len(setup.get("context_bars") or []),
        "note": setup.get("note", ""),
        "period": normalize_setup_period(setup.get("period", "train")),
        "quality_score": setup.get("quality_score"),
        "quality_reasons": setup.get("quality_reasons") or [],
    }


def create_setup(payload: dict[str, Any]) -> dict[str, Any]:
    entry_time = pd.Timestamp(payload["entry_time"])
    train_period = resolve_period(payload.get("train_period") or default_train_period())
    if not is_train_period(train_period):
        raise ValueError("train_period phải là năm train (vd. train_2022).")
    if not timestamp_in_period(entry_time, train_period):
        year = period_config(train_period).get("year", train_period)
        raise ValueError(f"Chỉ được đánh dấu setup trong năm Train {year}.")

    df = add_indicators(load_candles())
    tags = validate_setup_from_bar(payload, is_create=True)
    ann = annotation_at_time(payload["entry_time"])
    setups_existing = load_setups()
    setup_id = payload.get("id")
    setup_code_val = payload.get("code")
    if not setup_id and not setup_code_val:
        setup_code_val = assign_setup_code(payload, setups_existing)
        setup_id = setup_code_val
    setup = {
        "id": setup_id or str(uuid.uuid4())[:8],
        "code": setup_code_val or display_setup_code({"direction": payload["direction"], "entry_time": payload["entry_time"]}),
        "symbol": payload.get("symbol", "EURUSD"),
        "timeframe": payload.get("timeframe", "1H"),
        "direction": payload["direction"],
        "entry_time": payload["entry_time"],
        "entry_price": float(payload["entry_price"]),
        "stop_loss": float(payload["stop_loss"]),
        "take_profit": float(payload["take_profit"]),
        "tags": tags,
        "bar_tags": payload.get("bar_tags") or (ann.get("tags") if ann else []),
        "sequence_tags": payload.get("sequence_tags") or [],
        "annotation_id": payload.get("annotation_id") or (ann.get("id") if ann else None),
        "note": payload.get("note", ""),
        "period": train_period,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    enriched = enrich_setup(setup, df)
    from .setup_quality import enrich_setup_quality, passes_quality_gate

    ann_for_gate = annotation_at_time(payload["entry_time"])
    ok, msg = passes_quality_gate(enriched, annotation=ann_for_gate)
    if not ok:
        raise ValueError(
            f"Setup chưa đủ chất lượng: {msg}. "
            "Chọn nến RSI H4 đúng setup (break+retest hoặc extreme bounce), EMA H1 xác nhận, RR ≥ 2.5."
        )
    enriched = enrich_setup_quality(enriched, {ann_for_gate["id"]: ann_for_gate} if ann_for_gate else None)
    setups = [s for s in setups_existing if s["id"] != enriched["id"]]
    setups.append(enriched)
    save_setups(setups)
    if enriched.get("annotation_id"):
        link_setup_to_annotation(
            enriched["annotation_id"],
            enriched["id"],
            display_setup_code(enriched),
        )
    return enriched


def update_setup(setup_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    setups = load_setups()
    idx = next((i for i, s in enumerate(setups) if s["id"] == setup_id), None)
    if idx is None:
        raise KeyError(setup_id)

    merged = {**setups[idx], **payload, "id": setup_id}
    entry_time = pd.Timestamp(merged["entry_time"])
    train_period = normalize_setup_period(merged.get("period"))
    if not is_train_period(train_period):
        raise ValueError("Chỉ được sửa setup trong năm train.")
    if not timestamp_in_period(entry_time, train_period):
        year = period_config(train_period).get("year", train_period)
        raise ValueError(f"Setup phải nằm trong năm Train {year}.")
    merged["entry_price"] = float(merged["entry_price"])
    merged["stop_loss"] = float(merged["stop_loss"])
    merged["take_profit"] = float(merged["take_profit"])
    merged["tags"] = validate_setup_from_bar(merged, is_create=False)
    if payload.get("bar_tags") is not None:
        merged["bar_tags"] = normalize_tags(payload.get("bar_tags"))
    if payload.get("sequence_tags") is not None:
        merged["sequence_tags"] = payload.get("sequence_tags") or []
    if payload.get("annotation_id") is not None:
        merged["annotation_id"] = payload.get("annotation_id")
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()

    enriched = enrich_setup(merged)
    setups[idx] = enriched
    save_setups(setups)
    return enriched


def delete_setup(setup_id: str) -> None:
    from .bar_annotations import clear_setup_link

    clear_setup_link(setup_id)
    setups = [s for s in load_setups() if s["id"] != setup_id]
    save_setups(setups)
