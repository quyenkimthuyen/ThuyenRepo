from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .config import PIP
from .tags import infer_tags, load_presets

FEATURE_KEYS = (
    "dist_ema50_pips",
    "dist_ema200_pips",
    "atr14_pips",
    "h4_trend_up",
    "trend_up",
    "close_above_ema50",
    "close_above_ema200",
)

BOOL_KEYS = ("h4_trend_up", "trend_up", "close_above_ema50", "close_above_ema200")

FEATURE_WEIGHTS: dict[str, float] = {
    "dist_ema50_pips": 1.4,
    "dist_ema200_pips": 1.0,
    "atr14_pips": 0.6,
    "h4_trend_up": 1.5,
    "trend_up": 0.7,
    "close_above_ema50": 1.0,
    "close_above_ema200": 0.8,
}

DEFAULT_MIN_SIMILARITY = 0.52
DEFAULT_MIN_TAG_SCORE = 0.42
DEFAULT_DETECT_THRESHOLD = 0.45


def tag_definitions() -> list[dict[str, Any]]:
    presets = load_presets()
    return presets.get("tags") or []


def extract_features(row: pd.Series, entry_price: float | None = None) -> dict[str, Any]:
    entry = float(entry_price if entry_price is not None else row["close"])
    ema50 = float(row.get("ema50", entry))
    ema200 = float(row.get("ema200", entry))
    atr = float(row.get("atr14", 0))
    return {
        "dist_ema50_pips": round((entry - ema50) / PIP, 1),
        "dist_ema200_pips": round((entry - ema200) / PIP, 1),
        "atr14_pips": round(atr / PIP, 1),
        "h4_trend_up": bool(row.get("h4_trend_up", row.get("trend_up", False))),
        "trend_up": bool(row.get("trend_up", False)),
        "close_above_ema50": bool(row.get("close_above_ema50", False)),
        "close_above_ema200": bool(row.get("close_above_ema200", False)),
    }


def _features_from_setup(setup: dict[str, Any]) -> dict[str, Any] | None:
    raw = setup.get("features")
    if not raw:
        return None
    entry = float(setup.get("entry_price", 0))
    ema50 = float(raw.get("ema50", entry))
    ema200 = float(raw.get("ema200", entry))
    atr = float(raw.get("atr14", 0))
    h4_trend = raw.get("h4_trend_up")
    if h4_trend is None:
        h4_trend = raw.get("trend_up", False)
    return {
        "dist_ema50_pips": float(raw.get("dist_ema50_pips", (entry - ema50) / PIP)),
        "dist_ema200_pips": round((entry - ema200) / PIP, 1),
        "atr14_pips": round(atr / PIP, 1),
        "h4_trend_up": bool(h4_trend),
        "trend_up": bool(raw.get("trend_up", False)),
        "close_above_ema50": bool(raw.get("close_above_ema50", False)),
        "close_above_ema200": bool(raw.get("close_above_ema200", False)),
    }


def build_feature_stats(setups: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    rows: list[dict[str, float]] = []
    for setup in setups:
        feats = _features_from_setup(setup)
        if feats:
            rows.append({k: float(feats[k]) if k not in BOOL_KEYS else float(int(feats[k])) for k in FEATURE_KEYS})

    if not rows:
        return {
            key: {"mean": 0.0, "std": 1.0}
            for key in FEATURE_KEYS
            if key not in BOOL_KEYS
        }

    frame = pd.DataFrame(rows)
    stats: dict[str, dict[str, float]] = {}
    for key in FEATURE_KEYS:
        if key in BOOL_KEYS:
            continue
        mean = float(frame[key].mean())
        std = float(frame[key].std(ddof=0))
        stats[key] = {"mean": round(mean, 4), "std": round(max(std, 1e-6), 4)}
    return stats


def _normalize_value(key: str, value: float, stats: dict[str, dict[str, float]]) -> float:
    if key in BOOL_KEYS:
        return float(value)
    spec = stats.get(key, {"mean": 0.0, "std": 1.0})
    return (float(value) - spec["mean"]) / spec["std"]


def _vectorize(features: dict[str, Any], stats: dict[str, dict[str, float]]) -> np.ndarray:
    return np.array(
        [_normalize_value(k, float(features[k]) if k not in BOOL_KEYS else int(bool(features[k])), stats) for k in FEATURE_KEYS],
        dtype=float,
    )


def _gaussian_similarity(z: float) -> float:
    return math.exp(-0.5 * z * z)


def build_tag_signatures(
    setups: list[dict[str, Any]],
    extra_samples: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    by_tag: dict[str, list[dict[str, Any]]] = {}

    def _consume(item: dict[str, Any]) -> None:
        feats = _features_from_setup(item) or item.get("features")
        if not feats:
            return
        tags = infer_tags(item)
        if not tags:
            return
        for tag in tags:
            by_tag.setdefault(tag, []).append(feats)

    for setup in setups:
        if setup.get("result") not in ("win", "loss"):
            continue
        _consume(setup)

    for item in extra_samples or []:
        _consume(item)

    signatures: dict[str, dict[str, Any]] = {}
    for tag, rows in by_tag.items():
        frame = pd.DataFrame(rows)
        numeric: dict[str, dict[str, float]] = {}
        for key in FEATURE_KEYS:
            if key in BOOL_KEYS:
                continue
            numeric[key] = {
                "mean": round(float(frame[key].mean()), 3),
                "std": round(float(max(frame[key].std(ddof=0), 1e-6)), 3),
            }
        bool_rates = {key: round(float(frame[key].mean()), 3) for key in BOOL_KEYS}
        signatures[tag] = {
            "tag": tag,
            "count": len(rows),
            "features": numeric,
            "bool_rates": bool_rates,
        }
    return signatures


def score_tag(features: dict[str, Any], signature: dict[str, Any]) -> float:
    total_w = 0.0
    score = 0.0

    for key, spec in signature.get("features", {}).items():
        w = FEATURE_WEIGHTS.get(key, 1.0)
        z = (float(features[key]) - float(spec["mean"])) / max(float(spec["std"]), 1e-6)
        score += w * _gaussian_similarity(z)
        total_w += w

    for key, rate in signature.get("bool_rates", {}).items():
        w = FEATURE_WEIGHTS.get(key, 1.0)
        expected = rate >= 0.5
        if bool(features.get(key)) == expected:
            score += w
        else:
            score += w * max(0.15, 1.0 - abs(rate - 0.5) * 2)
        total_w += w

    return round(score / total_w, 3) if total_w else 0.0


def detect_tags(
    features: dict[str, Any],
    signatures: dict[str, dict[str, Any]],
    *,
    threshold: float = DEFAULT_DETECT_THRESHOLD,
    top_k: int = 4,
) -> list[dict[str, Any]]:
    scored = []
    for tag, sig in signatures.items():
        if sig.get("count", 0) < 1:
            continue
        s = score_tag(features, sig)
        if s >= threshold:
            scored.append({"tag": tag, "score": s, "count": sig.get("count", 0)})
    scored.sort(key=lambda item: (-item["score"], -item["count"]))
    return scored[:top_k]


def setup_similarity(
    features: dict[str, Any],
    setup: dict[str, Any],
    stats: dict[str, dict[str, float]],
) -> float | None:
    setup_feats = _features_from_setup(setup)
    if not setup_feats:
        return None
    a = _vectorize(features, stats)
    b = _vectorize(setup_feats, stats)
    dist = float(np.linalg.norm(a - b))
    max_dist = math.sqrt(len(FEATURE_KEYS))
    return round(max(0.0, 1.0 - dist / max_dist), 3)


def find_similar_setups(
    features: dict[str, Any],
    setups: list[dict[str, Any]],
    stats: dict[str, dict[str, float]],
    *,
    detected_tags: list[str] | None = None,
    k: int = 5,
    min_similarity: float = 0.0,
) -> list[dict[str, Any]]:
    tag_set = set(detected_tags or [])
    ranked: list[dict[str, Any]] = []

    for setup in setups:
        if setup.get("result") not in ("win", "loss"):
            continue
        setup_tags = infer_tags(setup)
        if tag_set and not tag_set.intersection(setup_tags):
            continue
        sim = setup_similarity(features, setup, stats)
        if sim is None or sim < min_similarity:
            continue
        ranked.append(
            {
                "setup_id": setup.get("id"),
                "similarity": sim,
                "direction": setup.get("direction"),
                "result": setup.get("result"),
                "tags": setup_tags,
                "entry_time": setup.get("entry_time"),
                "planned_rr": setup.get("planned_rr"),
            }
        )

    ranked.sort(key=lambda item: (-item["similarity"], item["entry_time"] or ""))
    return ranked[:k]


def build_setup_index(setups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = []
    for setup in setups:
        feats = _features_from_setup(setup)
        if not feats:
            continue
        index.append(
            {
                "id": setup.get("id"),
                "direction": setup.get("direction"),
                "result": setup.get("result"),
                "tags": infer_tags(setup),
                "planned_rr": setup.get("planned_rr"),
                "entry_time": setup.get("entry_time"),
                "features": feats,
            }
        )
    return index


def suggest_context(
    features: dict[str, Any],
    train_setups: list[dict[str, Any]],
    signatures: dict[str, dict[str, Any]],
    stats: dict[str, dict[str, float]],
    *,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> dict[str, Any]:
    detected = detect_tags(features, signatures)
    detected_tag_ids = [item["tag"] for item in detected]
    similar = find_similar_setups(
        features,
        train_setups,
        stats,
        detected_tags=detected_tag_ids or None,
        k=5,
    )

    if not similar:
        similar = find_similar_setups(features, train_setups, stats, k=5)

    best = similar[0] if similar else None
    suggested_direction = None
    confidence = 0.0
    if best and best["similarity"] >= min_similarity:
        suggested_direction = best["direction"]
        confidence = best["similarity"]

    win_rate = None
    if similar:
        wins = sum(1 for item in similar if item["result"] == "win")
        win_rate = round(wins / len(similar), 3)

    suggested_tags = [item["tag"] for item in detected]
    if not suggested_tags and best:
        suggested_tags = list(best.get("tags") or [])

    return {
        "features": features,
        "detected_tags": detected,
        "suggested_tags": suggested_tags,
        "similar_setups": similar,
        "suggested_direction": suggested_direction,
        "confidence": confidence,
        "cluster_win_rate": win_rate,
    }


def match_entry_from_similarity(
    row: pd.Series,
    strategy: dict[str, Any],
    train_setups: list[dict[str, Any]],
) -> tuple[str | None, dict[str, Any] | None, dict[str, Any] | None]:
    signatures = strategy.get("tag_signatures") or {}
    stats = strategy.get("feature_stats") or build_feature_stats(train_setups)
    if not signatures or not train_setups:
        return None, None, None

    min_sim = float(strategy.get("min_similarity", DEFAULT_MIN_SIMILARITY))
    min_cluster_wr = float(strategy.get("min_cluster_win_rate", 0.45))

    features = extract_features(row)
    ctx = suggest_context(features, train_setups, signatures, stats, min_similarity=min_sim)
    similar = ctx.get("similar_setups") or []
    if not similar:
        return None, None, None

    best = similar[0]
    if best["similarity"] < min_sim:
        return None, None, None

    cluster_wr = ctx.get("cluster_win_rate")
    if cluster_wr is not None and cluster_wr < min_cluster_wr:
        return None, None, None

    direction = best.get("direction")
    if direction not in ("long", "short"):
        return None, None, None

    ref_setup = next((s for s in train_setups if s.get("id") == best.get("setup_id")), None)
    return direction, ref_setup, ctx
