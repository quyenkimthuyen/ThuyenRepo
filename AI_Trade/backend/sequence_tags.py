from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import PIP
from .data_service import load_candles
from .indicators import add_indicators
from .tags import infer_tags

SEQUENCE_KEYS = (
    "momentum_pips",
    "pullback_from_high_pips",
    "pullback_from_low_pips",
    "rsi_delta",
    "dist_ema50_min_pips",
    "broke_high",
    "broke_low",
    "touched_ema50",
    "last_rejection",
    "trend_up",
)

BOOL_SEQ_KEYS = ("broke_high", "broke_low", "touched_ema50", "last_rejection", "trend_up")

# Heuristic: sequence shape → tag candidates
HEURISTIC_TAGS: list[dict[str, Any]] = [
    {
        "tag": "breakout",
        "label": "Breakout chuỗi",
        "check": lambda s: s.get("broke_high") and s.get("momentum_pips", 0) > 3,
    },
    {
        "tag": "breakout",
        "label": "Breakout down",
        "check": lambda s: s.get("broke_low") and s.get("momentum_pips", 0) < -3,
    },
    {
        "tag": "retest",
        "label": "Retest EMA50",
        "check": lambda s: s.get("touched_ema50")
        and abs(s.get("dist_ema50_min_pips", 99)) < 8
        and s.get("broke_high"),
    },
    {
        "tag": "pullback",
        "label": "Pullback về EMA",
        "check": lambda s: s.get("trend_up")
        and s.get("touched_ema50")
        and s.get("pullback_from_high_pips", 0) > 5,
    },
    {
        "tag": "rejection",
        "label": "Rejection cuối chuỗi",
        "check": lambda s: s.get("last_rejection"),
    },
    {
        "tag": "reversal",
        "label": "Đảo momentum",
        "check": lambda s: abs(s.get("rsi_delta", 0)) > 8
        and (
            (s.get("momentum_pips", 0) > 0 and s.get("rsi_delta", 0) < 0)
            or (s.get("momentum_pips", 0) < 0 and s.get("rsi_delta", 0) > 0)
        ),
    },
]


def extract_sequence(df: pd.DataFrame, i: int, window: int = 5) -> dict[str, Any] | None:
    if i < window or i >= len(df):
        return None

    sub = df.iloc[i - window + 1 : i + 1]
    if sub.empty or len(sub) < window:
        return None

    row = df.iloc[i]
    atr = float(row.get("atr14") or 0)
    if np.isnan(atr) or atr <= 0:
        return None

    closes = sub["close"].astype(float)
    highs = sub["high"].astype(float)
    lows = sub["low"].astype(float)
    ema50 = sub["ema50"].astype(float)

    momentum = (float(closes.iloc[-1]) - float(closes.iloc[0])) / PIP
    window_high = float(highs.max())
    window_low = float(lows.min())
    close = float(closes.iloc[-1])

    pullback_high = (window_high - close) / PIP
    pullback_low = (close - window_low) / PIP

    prior_high = float(df.iloc[i - window : i]["high"].max()) if i >= window else window_high
    prior_low = float(df.iloc[i - window : i]["low"].min()) if i >= window else window_low
    broke_high = float(row["high"]) > prior_high
    broke_low = float(row["low"]) < prior_low

    dist_ema50 = ((closes - ema50) / PIP).abs()
    touched_ema50 = float(dist_ema50.min()) <= max(8.0, atr / PIP * 0.4)

    rsi_now = float(row.get("rsi14", 50))
    rsi_prev = float(df.iloc[i - min(3, window - 1)].get("rsi14", rsi_now))
    rsi_delta = rsi_now - rsi_prev

    o, h, l, c = float(row["open"]), float(row["high"]), float(row["low"]), close
    body = abs(c - o)
    upper = h - max(c, o)
    lower = min(c, o) - l
    last_rejection = body > 0 and (upper > body * 1.2 or lower > body * 1.2)

    return {
        "window": window,
        "momentum_pips": round(momentum, 1),
        "pullback_from_high_pips": round(pullback_high, 1),
        "pullback_from_low_pips": round(pullback_low, 1),
        "rsi_delta": round(rsi_delta, 1),
        "dist_ema50_min_pips": round(float(dist_ema50.min()), 1),
        "broke_high": bool(broke_high),
        "broke_low": bool(broke_low),
        "touched_ema50": bool(touched_ema50),
        "last_rejection": bool(last_rejection),
        "trend_up": bool(row.get("trend_up", False)),
    }


def detect_heuristic_sequence_tags(seq: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for rule in HEURISTIC_TAGS:
        try:
            if rule["check"](seq):
                found.append(
                    {
                        "tag": rule["tag"],
                        "score": 0.72,
                        "source": "sequence_heuristic",
                        "label": rule["label"],
                    }
                )
        except (TypeError, KeyError):
            continue

    by_tag: dict[str, dict[str, Any]] = {}
    for item in found:
        tag = item["tag"]
        if tag not in by_tag or item["score"] > by_tag[tag]["score"]:
            by_tag[tag] = item
    return sorted(by_tag.values(), key=lambda x: -x["score"])


def _sequence_vector(seq: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(int(seq[key])) if key in BOOL_SEQ_KEYS else float(seq.get(key, 0))
        for key in SEQUENCE_KEYS
        if key in seq
    }


def build_sequence_signatures(
    train_setups: list[dict[str, Any]],
    *,
    window: int = 5,
    extra_samples: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    df = add_indicators(load_candles())
    by_tag: dict[str, list[dict[str, float]]] = {}

    def _consume(entry_time: str, tags: list[str]) -> None:
        ts = pd.Timestamp(entry_time)
        if ts.tz is None:
            ts = ts.tz_localize("UTC")
        idx = df.index.get_indexer([ts], method="nearest")[0]
        if idx < 0:
            return
        seq = extract_sequence(df, idx, window=window)
        if not seq:
            return
        vec = _sequence_vector(seq)
        for tag in tags:
            by_tag.setdefault(tag, []).append(vec)

    for setup in train_setups:
        if setup.get("result") not in ("win", "loss"):
            continue
        _consume(setup["entry_time"], infer_tags(setup))

    for item in extra_samples or []:
        tags = infer_tags(item)
        entry_time = item.get("entry_time") or item.get("bar_time")
        if tags and entry_time:
            _consume(entry_time, tags)

    signatures: dict[str, dict[str, Any]] = {}
    for tag, rows in by_tag.items():
        frame = pd.DataFrame(rows)
        numeric: dict[str, dict[str, float]] = {}
        for key in SEQUENCE_KEYS:
            if key in BOOL_SEQ_KEYS:
                continue
            numeric[key] = {
                "mean": round(float(frame[key].mean()), 3),
                "std": round(float(max(frame[key].std(ddof=0), 1e-6)), 3),
            }
        bool_rates = {key: round(float(frame[key].mean()), 3) for key in BOOL_SEQ_KEYS if key in frame}
        signatures[tag] = {
            "tag": tag,
            "count": len(rows),
            "window": window,
            "features": numeric,
            "bool_rates": bool_rates,
        }
    return signatures


def score_sequence_tag(seq: dict[str, Any], signature: dict[str, Any]) -> float:
    import math

    total_w = 0.0
    score = 0.0
    weights = {
        "momentum_pips": 1.2,
        "pullback_from_high_pips": 1.0,
        "pullback_from_low_pips": 1.0,
        "rsi_delta": 0.8,
        "dist_ema50_min_pips": 1.1,
    }

    for key, spec in signature.get("features", {}).items():
        w = weights.get(key, 1.0)
        val = float(seq.get(key, 0))
        z = (val - float(spec["mean"])) / max(float(spec["std"]), 1e-6)
        score += w * math.exp(-0.5 * z * z)
        total_w += w

    for key, rate in signature.get("bool_rates", {}).items():
        w = 1.0
        expected = rate >= 0.5
        if bool(seq.get(key)) == expected:
            score += w
        else:
            score += w * 0.2
        total_w += w

    return round(score / total_w, 3) if total_w else 0.0


def detect_sequence_tags(
    seq: dict[str, Any],
    signatures: dict[str, dict[str, Any]] | None = None,
    *,
    min_score: float = 0.45,
) -> list[dict[str, Any]]:
    heuristic = detect_heuristic_sequence_tags(seq)
    learned: list[dict[str, Any]] = []

    if signatures:
        for tag, sig in signatures.items():
            if sig.get("count", 0) < 1:
                continue
            s = score_sequence_tag(seq, sig)
            if s >= min_score:
                learned.append(
                    {
                        "tag": tag,
                        "score": s,
                        "source": "sequence_learned",
                        "label": f"Chuỗi giống {tag} ({sig.get('count')} mẫu)",
                    }
                )
        learned.sort(key=lambda x: -x["score"])

    merged: dict[str, dict[str, Any]] = {}
    for item in heuristic + learned:
        tag = item["tag"]
        prev = merged.get(tag)
        if not prev or item["score"] > prev["score"]:
            merged[tag] = item

    return sorted(merged.values(), key=lambda x: -x["score"])


def merge_bar_and_sequence_tags(
    bar_tags: list[dict[str, Any]],
    seq_tags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for item in bar_tags:
        tag = item["tag"]
        merged[tag] = {**item, "sources": ["bar"]}

    for item in seq_tags:
        tag = item["tag"]
        if tag in merged:
            boosted = min(0.98, merged[tag]["score"] * 0.55 + item["score"] * 0.55 + 0.12)
            merged[tag] = {
                **merged[tag],
                "score": round(boosted, 3),
                "sources": sorted(set(merged[tag].get("sources", []) + ["sequence"])),
                "sequence_label": item.get("label"),
            }
        else:
            merged[tag] = {**item, "sources": ["sequence"]}

    return sorted(merged.values(), key=lambda x: -x["score"])
