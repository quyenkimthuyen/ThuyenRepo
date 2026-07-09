from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BAR_DETECTION_PATH = ROOT / "config" / "bar_detection.json"

DEFAULTS: dict[str, Any] = {
    "min_score": 35,
    "max_bars": 500,
    "sequence_window": 5,
    "sequence_min_score": 0.45,
    "bar_tag_threshold": 0.45,
    "backtest_min_score": 35,
    "require_sequence_tag": False,
    "score_weights": {
        "near_ema50_strong": 22,
        "near_ema50_medium": 12,
        "near_ema200": 18,
        "swing_high": 20,
        "swing_low": 20,
        "rejection_wick": 16,
        "labeled_setup": 40,
        "similar_to_setup_mult": 28,
        "sequence_match_mult": 30,
    },
    "thresholds": {
        "ema50_near_atr": 0.35,
        "ema50_medium_atr": 0.65,
        "ema200_near_atr": 0.35,
        "wick_body_ratio": 1.2,
        "setup_similarity_min": 0.52,
    },
    "feature_weights": {
        "rsi14": 1.0,
        "dist_ema50_pips": 1.4,
        "dist_ema200_pips": 1.0,
        "atr14_pips": 0.6,
        "trend_up": 0.9,
        "close_above_ema50": 1.0,
        "close_above_ema200": 0.8,
    },
}


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_bar_detection_config() -> dict[str, Any]:
    if not BAR_DETECTION_PATH.exists():
        return deepcopy(DEFAULTS)
    try:
        raw = json.loads(BAR_DETECTION_PATH.read_text(encoding="utf-8"))
        return _deep_merge(DEFAULTS, raw)
    except (json.JSONDecodeError, OSError):
        return deepcopy(DEFAULTS)


def save_bar_detection_config(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_bar_detection_config()
    merged = _deep_merge(current, patch)
    BAR_DETECTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    BAR_DETECTION_PATH.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged
