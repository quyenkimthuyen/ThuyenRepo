from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .analyzer import load_strategy
from .config import PIP
from .data_service import load_candles, slice_period
from .detection_config import load_bar_detection_config
from .indicators import add_indicators
from .labels import load_setups
from .pipeline import filter_train_setups
from .bar_annotations import annotation_index_by_time, load_bar_annotations
from .sequence_tags import (
    build_sequence_signatures,
    detect_sequence_tags,
    extract_sequence,
    merge_bar_and_sequence_tags,
)
from .tag_matcher import (
    build_feature_stats,
    build_tag_signatures,
    detect_tags,
    extract_features,
    find_similar_setups,
    suggest_context,
)
from .tags import infer_tags

SWING_WINDOW = 2

REASON_LABELS: dict[str, str] = {
    "near_ema50": "Gần EMA50",
    "near_ema200": "Gần EMA200",
    "swing_high": "Swing high",
    "swing_low": "Swing low",
    "rejection_wick": "Wick từ chối giá",
    "labeled_setup": "Setup đã label",
    "similar_to_setup": "Giống setup train",
    "sequence_match": "Chuỗi nến khớp pattern",
    "user_annotation": "Tag nến đã xác nhận",
}


def _cfg() -> dict[str, Any]:
    return load_bar_detection_config()


def _is_swing_high(df: pd.DataFrame, i: int, window: int = SWING_WINDOW) -> bool:
    if i < window or i >= len(df) - window:
        return False
    high = float(df.iloc[i]["high"])
    for k in range(1, window + 1):
        if high < float(df.iloc[i - k]["high"]) or high < float(df.iloc[i + k]["high"]):
            return False
    return True


def _is_swing_low(df: pd.DataFrame, i: int, window: int = SWING_WINDOW) -> bool:
    if i < window or i >= len(df) - window:
        return False
    low = float(df.iloc[i]["low"])
    for k in range(1, window + 1):
        if low > float(df.iloc[i - k]["low"]) or low > float(df.iloc[i + k]["low"]):
            return False
    return True


def _has_labeled_setup(ts: pd.Timestamp, train_setups: list[dict[str, Any]]) -> bool:
    for setup in train_setups:
        entry = pd.Timestamp(setup["entry_time"])
        if abs((entry - ts).total_seconds()) <= 3600:
            return True
    return False


def score_bar(
    row: pd.Series,
    df: pd.DataFrame,
    i: int,
    train_setups: list[dict[str, Any]],
    *,
    feature_stats: dict[str, dict[str, float]] | None = None,
    config: dict[str, Any] | None = None,
    sequence_tags: list[dict[str, Any]] | None = None,
    annotation_index: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cfg = config or _cfg()
    weights = cfg.get("score_weights", {})
    thresholds = cfg.get("thresholds", {})
    min_score = float(cfg.get("min_score", 35))

    score = 0
    reasons: list[str] = []

    atr = float(row.get("atr14") or 0)
    if np.isnan(atr) or atr <= 0:
        return {"score": 0, "important": False, "reasons": []}

    atr_pips = atr / PIP
    close = float(row["close"])
    ema_near = float(thresholds.get("ema50_near_atr", 0.35))
    ema_med = float(thresholds.get("ema50_medium_atr", 0.65))
    ema200_near = float(thresholds.get("ema200_near_atr", 0.35))
    wick_ratio = float(thresholds.get("wick_body_ratio", 1.2))
    sim_min = float(thresholds.get("setup_similarity_min", 0.52))

    dist50 = abs(close - float(row["ema50"])) / PIP
    if dist50 <= atr_pips * ema_near:
        score += int(weights.get("near_ema50_strong", 22))
        reasons.append("near_ema50")
    elif dist50 <= atr_pips * ema_med:
        score += int(weights.get("near_ema50_medium", 12))
        reasons.append("near_ema50")

    dist200 = abs(close - float(row["ema200"])) / PIP
    if dist200 <= atr_pips * ema200_near:
        score += int(weights.get("near_ema200", 18))
        reasons.append("near_ema200")

    if _is_swing_high(df, i):
        score += int(weights.get("swing_high", 20))
        reasons.append("swing_high")
    if _is_swing_low(df, i):
        score += int(weights.get("swing_low", 20))
        reasons.append("swing_low")

    o, h, l, c = float(row["open"]), float(row["high"]), float(row["low"]), close
    body = abs(c - o)
    if body > 0:
        upper = h - max(c, o)
        lower = min(c, o) - l
        if upper > body * wick_ratio or lower > body * wick_ratio:
            score += int(weights.get("rejection_wick", 16))
            reasons.append("rejection_wick")

    ts = df.index[i]
    ts_unix = int(ts.timestamp())
    if annotation_index and ts_unix in annotation_index:
        score += int(weights.get("user_annotation", 35))
        reasons.append("user_annotation")
    elif _has_labeled_setup(ts, train_setups):
        score += int(weights.get("labeled_setup", 40))
        reasons.append("labeled_setup")

    if train_setups and feature_stats:
        features = extract_features(row)
        similar = find_similar_setups(
            features, train_setups, feature_stats, k=1, min_similarity=sim_min
        )
        if similar:
            mult = int(weights.get("similar_to_setup_mult", 28))
            score += int(similar[0]["similarity"] * mult)
            reasons.append("similar_to_setup")

    if sequence_tags:
        best_seq = sequence_tags[0]["score"] if sequence_tags else 0
        if best_seq >= float(cfg.get("sequence_min_score", 0.45)):
            mult = int(weights.get("sequence_match_mult", 30))
            score += int(best_seq * mult)
            reasons.append("sequence_match")

    score = min(100, score)
    return {
        "score": score,
        "important": score >= min_score,
        "reasons": reasons,
        "reason_labels": [REASON_LABELS.get(r, r) for r in reasons],
    }


_CTX_CACHE: dict[str, dict[str, Any]] = {}


_ANN_INDEX_CACHE: dict[int, dict[str, Any]] | None = None


def clear_detection_cache() -> None:
    global _ANN_INDEX_CACHE
    _ANN_INDEX_CACHE = None
    _CTX_CACHE.clear()


def annotation_index_by_time_cached() -> dict[int, dict[str, Any]]:
    global _ANN_INDEX_CACHE
    if _ANN_INDEX_CACHE is None:
        _ANN_INDEX_CACHE = annotation_index_by_time()
    return _ANN_INDEX_CACHE


def _load_detection_context(
    train_setups: list[dict[str, Any]], config: dict[str, Any] | None = None
) -> dict[str, Any]:
    cfg = config or _cfg()
    window = int(cfg.get("sequence_window", 5))
    strategy = load_strategy()
    cache_key = f"{len(train_setups)}:{window}:{len((strategy or {}).get('tag_signatures') or {})}"
    if cache_key in _CTX_CACHE:
        return _CTX_CACHE[cache_key]

    ctx = {
        "config": cfg,
        "signatures": (strategy or {}).get("tag_signatures") or build_tag_signatures(train_setups),
        "sequence_signatures": (strategy or {}).get("sequence_signatures")
        or build_sequence_signatures(train_setups, window=window),
        "feature_stats": (strategy or {}).get("feature_stats") or build_feature_stats(train_setups),
        "feature_weights": cfg.get("feature_weights"),
    }
    _CTX_CACHE[cache_key] = ctx
    return ctx


def inspect_bar(
    row: pd.Series,
    ts: pd.Timestamp,
    df: pd.DataFrame,
    idx: int,
    train_setups: list[dict[str, Any]],
    *,
    ctx: dict[str, Any] | None = None,
    importance: dict[str, Any] | None = None,
    annotation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = ctx or _load_detection_context(train_setups)
    cfg = ctx["config"]
    fw = ctx.get("feature_weights")

    features = extract_features(row)
    bar_ctx = suggest_context(
        features,
        train_setups,
        ctx["signatures"],
        ctx["feature_stats"],
        min_similarity=float(cfg.get("thresholds", {}).get("setup_similarity_min", 0.52)),
    )
    bar_tags = detect_tags(
        features,
        ctx["signatures"],
        threshold=float(cfg.get("bar_tag_threshold", 0.45)),
    )
    for item in bar_tags:
        item["source"] = "bar"

    seq = extract_sequence(df, idx, window=int(cfg.get("sequence_window", 5)))
    seq_tags: list[dict[str, Any]] = []
    if seq:
        seq_tags = detect_sequence_tags(
            seq,
            ctx.get("sequence_signatures"),
            min_score=float(cfg.get("sequence_min_score", 0.45)),
        )

    detected = merge_bar_and_sequence_tags(bar_tags, seq_tags)
    primary_tag = detected[0]["tag"] if detected else None
    if annotation and annotation.get("tags"):
        primary_tag = annotation["tags"][0]
    elif not primary_tag and bar_ctx.get("similar_setups"):
        tags = bar_ctx["similar_setups"][0].get("tags") or []
        primary_tag = tags[0] if tags else None

    if importance is None:
        importance = score_bar(
            row,
            df,
            idx,
            train_setups,
            feature_stats=ctx["feature_stats"],
            config=cfg,
            sequence_tags=seq_tags,
            annotation_index=annotation_index_by_time(),
        )

    suggested_tags = [item["tag"] for item in detected]
    if annotation and annotation.get("tags"):
        suggested_tags = list(annotation["tags"])
    elif not suggested_tags:
        suggested_tags = bar_ctx.get("suggested_tags") or []

    return {
        "time": int(ts.timestamp()),
        "entry_time": ts.isoformat(),
        "close": round(float(row["close"]), 5),
        "importance": importance,
        "features": features,
        "sequence": seq,
        "bar_tags": bar_tags,
        "sequence_tags": seq_tags,
        "detected_tags": detected,
        "suggested_tags": suggested_tags,
        "primary_tag": primary_tag,
        "similar_setups": bar_ctx.get("similar_setups") or [],
        "suggested_direction": bar_ctx.get("suggested_direction"),
        "confidence": bar_ctx.get("confidence"),
        "cluster_win_rate": bar_ctx.get("cluster_win_rate"),
        "annotation": annotation,
        "user_confirmed": bool(annotation and annotation.get("confirmed")),
    }


def scan_important_bars(
    period: str = "train",
    *,
    month: str | None = None,
    min_score: float | None = None,
    with_tags: bool = True,
    max_bars: int | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or _cfg()
    if min_score is None:
        min_score = float(cfg.get("min_score", 35))
    if max_bars is None:
        max_bars = int(cfg.get("max_bars", 500))

    from .data_service import slice_month

    df = add_indicators(slice_period(load_candles(), period))
    if month:
        df = slice_month(df, month)
        if df.empty:
            return {
                "period": period,
                "month": month,
                "min_score": min_score,
                "count": 0,
                "bars": [],
                "config": cfg,
            }
    train_setups = [s for s in load_setups() if s.get("period") == "train"]
    det_ctx = _load_detection_context(train_setups, cfg)
    ann_index = annotation_index_by_time()

    bars: list[dict[str, Any]] = []
    start = max(200, SWING_WINDOW, int(cfg.get("sequence_window", 5)))

    for i in range(start, len(df)):
        row = df.iloc[i]
        if np.isnan(row.get("rsi14")) or np.isnan(row.get("atr14")):
            continue

        seq = extract_sequence(df, i, window=int(cfg.get("sequence_window", 5)))
        seq_tags = (
            detect_sequence_tags(
                seq,
                det_ctx.get("sequence_signatures"),
                min_score=float(cfg.get("sequence_min_score", 0.45)),
            )
            if seq
            else []
        )

        importance = score_bar(
            row,
            df,
            i,
            train_setups,
            feature_stats=det_ctx["feature_stats"],
            config=cfg,
            sequence_tags=seq_tags,
            annotation_index=ann_index,
        )
        if importance["score"] < min_score:
            continue

        ts = df.index[i]
        ts_unix = int(ts.timestamp())
        ann = ann_index.get(ts_unix)
        item: dict[str, Any] = {
            "time": ts_unix,
            "score": importance["score"],
            "reasons": importance["reasons"],
            "reason_labels": importance["reason_labels"],
            "user_confirmed": bool(ann),
            "annotation_id": ann.get("id") if ann else None,
            "confirmed_tags": ann.get("tags") if ann else [],
        }

        if with_tags:
            detail = inspect_bar(
                row,
                ts,
                df,
                i,
                train_setups,
                ctx=det_ctx,
                importance=importance,
                annotation=ann,
            )
            if ann and ann.get("tags"):
                detail["primary_tag"] = ann["tags"][0]
                detail["suggested_tags"] = ann["tags"]
            item["detected_tags"] = detail["detected_tags"]
            item["sequence_tags"] = detail["sequence_tags"]
            item["suggested_tags"] = detail["suggested_tags"]
            item["primary_tag"] = detail["primary_tag"]
            item["similarity"] = detail.get("confidence")
            item["similar_setups"] = (detail.get("similar_setups") or [])[:3]
            item["suggested_direction"] = detail.get("suggested_direction")
            item["sequence"] = detail.get("sequence")

        bars.append(item)

    bars.sort(key=lambda b: -b["score"])
    if len(bars) > max_bars:
        bars = bars[:max_bars]
    bars.sort(key=lambda b: b["time"])
    result = {
        "period": period,
        "min_score": min_score,
        "count": len(bars),
        "bars": bars,
        "config": cfg,
    }
    if month:
        result["month"] = month
    return result


def inspect_bar_at_time(
    entry_time: str,
    *,
    entry_price: float | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or _cfg()
    df = add_indicators(load_candles())
    ts = pd.Timestamp(entry_time)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")

    idx = df.index.get_indexer([ts], method="nearest")[0]
    if idx < 0:
        raise ValueError("Invalid time")

    row = df.iloc[idx]
    bar_ts = df.index[idx]
    train_setups = [s for s in load_setups() if s.get("period") == "train"]
    ann_index = annotation_index_by_time()
    ann = ann_index.get(int(bar_ts.timestamp()))

    if entry_price is not None:
        row = row.copy()
        row["close"] = float(entry_price)

    detail = inspect_bar(
        row,
        bar_ts,
        df,
        idx,
        train_setups,
        ctx=_load_detection_context(train_setups, cfg),
        annotation=ann,
    )
    detail["important"] = detail["importance"]["score"] >= float(cfg.get("min_score", 35))
    return detail


def match_entry_from_inspection(
    df: pd.DataFrame,
    i: int,
    strategy: dict[str, Any],
    train_setups: list[dict[str, Any]] | None = None,
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    """Unified entry matcher: importance gate + tag/sequence + setup similarity."""
    cfg = _cfg()
    raw_setups = train_setups or [s for s in load_setups() if s.get("period") == "train"]
    train_setups = filter_train_setups(raw_setups, strategy)
    if not train_setups:
        return None, None, None

    row = df.iloc[i]
    ts = df.index[i]
    if np.isnan(row.get("rsi14")) or np.isnan(row.get("atr14")):
        return None, None, None

    det_ctx = _load_detection_context(train_setups, cfg)
    ann_index = annotation_index_by_time_cached()
    ann = ann_index.get(int(ts.timestamp()))

    seq = extract_sequence(df, i, window=int(cfg.get("sequence_window", 5)))
    seq_tags = (
        detect_sequence_tags(
            seq,
            det_ctx.get("sequence_signatures"),
            min_score=float(cfg.get("sequence_min_score", 0.45)),
        )
        if seq
        else []
    )

    importance = score_bar(
        row,
        df,
        i,
        train_setups,
        feature_stats=det_ctx["feature_stats"],
        config=cfg,
        sequence_tags=seq_tags,
        annotation_index=ann_index,
    )

    min_score = float(strategy.get("backtest_min_score", cfg.get("backtest_min_score", cfg.get("min_score", 35))))
    if importance["score"] < min_score:
        return None, None, None

    require_seq = strategy.get(
        "require_sequence_tag",
        cfg.get("require_sequence_tag", False),
    )
    if require_seq and not seq_tags:
        return None, None, None

    features = extract_features(row)
    tag_threshold = float(
        strategy.get(
            "bar_tag_threshold",
            cfg.get("bar_tag_threshold", cfg.get("thresholds", {}).get("bar_tag_threshold", 0.45)),
        )
    )
    bar_tags = detect_tags(
        features,
        det_ctx["signatures"],
        threshold=tag_threshold,
    )
    for item in bar_tags:
        item["source"] = "bar"
    detected = merge_bar_and_sequence_tags(bar_tags, seq_tags)

    require_tag = strategy.get("require_detected_tag", True)
    entry_tags: set[str] = set()
    if ann and ann.get("tags"):
        entry_tags.update(infer_tags(ann))
    for item in detected:
        if float(item.get("score", 0)) >= tag_threshold:
            entry_tags.add(item["tag"])

    if require_tag and not entry_tags:
        return None, None, None

    min_sim = float(
        strategy.get(
            "min_similarity",
            cfg.get("thresholds", {}).get("setup_similarity_min", 0.52),
        )
    )
    detected_tag_ids = [t for t in entry_tags]
    similar = find_similar_setups(
        features,
        train_setups,
        det_ctx["feature_stats"],
        detected_tags=detected_tag_ids or None,
        k=5,
        min_similarity=min_sim,
    )
    if not similar:
        return None, None, None

    cluster_wr = None
    if similar:
        wins = sum(1 for item in similar if item.get("result") == "win")
        cluster_wr = round(wins / len(similar), 3)

    primary_tag = detected[0]["tag"] if detected else None
    if ann and ann.get("tags"):
        primary_tag = ann["tags"][0]
    elif not primary_tag and similar:
        tags = similar[0].get("tags") or []
        primary_tag = tags[0] if tags else None

    detail = {
        "features": features,
        "detected_tags": detected,
        "sequence_tags": seq_tags,
        "similar_setups": similar,
        "cluster_win_rate": cluster_wr,
        "primary_tag": primary_tag,
        "suggested_direction": similar[0].get("direction") if similar else None,
        "importance": importance,
    }

    best = similar[0]
    if best.get("similarity", 0) < min_sim:
        return None, None, None

    min_cluster_wr = float(strategy.get("min_cluster_win_rate", 0.45))
    if cluster_wr is not None and cluster_wr < min_cluster_wr:
        return None, None, None

    direction = best.get("direction") or detail.get("suggested_direction")
    if direction not in ("long", "short"):
        return None, None, None

    ref_setup = next((s for s in train_setups if s.get("id") == best.get("setup_id")), None)
    if not ref_setup:
        return None, None, None

    avoid = set((strategy.get("tags") or {}).get("avoid_tags") or [])
    setup_tags = set(infer_tags(ref_setup))
    if avoid.intersection(setup_tags):
        return None, None, None

    if entry_tags and not setup_tags.intersection(entry_tags):
        return None, None, None

    primary_tag = detail.get("primary_tag")
    if not primary_tag and detected:
        primary_tag = detected[0].get("tag")
    if not primary_tag and entry_tags:
        primary_tag = next(iter(entry_tags))
    if require_tag and not primary_tag:
        return None, None, None
    if primary_tag and primary_tag in avoid:
        return None, None, None

    detail = {**detail, "similar_setups": similar}

    meta = {
        "ref_setup": ref_setup,
        "context": detail,
        "importance": importance,
        "sequence_tags": seq_tags,
    }
    return direction, primary_tag, meta
