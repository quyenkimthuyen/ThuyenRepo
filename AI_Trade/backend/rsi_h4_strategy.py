"""Chiến lược RSI H4 band + EMA 50/200 H1 — Setup 1 break/retest, Setup 2 extreme bounce."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import PIP, ROOT

CONFIG_PATH = ROOT / "config" / "rsi_h4_strategy.json"

TAG_BREAK_RETEST = "rsi_break_retest"
TAG_EXTREME_BOUNCE = "rsi_extreme_bounce"
TAG_EMA_CONFIRM = "ema_h1_confirm"

SETUP_META = {
    "break_retest": {
        "tag": TAG_BREAK_RETEST,
        "label": "Break vùng 50 → test lại → tiếp tục",
    },
    "extreme_bounce": {
        "tag": TAG_EXTREME_BOUNCE,
        "label": "Chạm 70/30 → hồi 50 → bật (lần 1–2)",
    },
}


def load_rsi_h4_config(strategy: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if strategy:
        for key in (
            "bands",
            "setups",
            "risk",
            "ema_tolerance_atr",
            "lookback_bars",
            "entry_cooldown_bars",
            "rsi_rise_min",
        ):
            if key in strategy and strategy[key] is not None:
                if isinstance(base.get(key), dict) and isinstance(strategy[key], dict):
                    base[key] = {**base[key], **strategy[key]}
                else:
                    base[key] = strategy[key]
    return base


def _band(cfg: dict[str, Any], name: str) -> tuple[float, float]:
    raw = cfg["bands"][name]
    return float(raw[0]), float(raw[1])


def in_band(value: float, band: tuple[float, float]) -> bool:
    return band[0] <= value <= band[1]


def above_band(value: float, band: tuple[float, float]) -> bool:
    return value > band[1]


def below_band(value: float, band: tuple[float, float]) -> bool:
    return value < band[0]


def ema_h1_supports_long(row: pd.Series, *, tol_atr: float = 0.35) -> bool:
    close = float(row["close"])
    ema50 = float(row.get("ema50", close))
    ema200 = float(row.get("ema200", close))
    atr = float(row.get("atr14", 0))
    if np.isnan(atr) or atr <= 0:
        return True
    tol = atr * tol_atr
    return close >= ema50 - tol or close >= ema200 - tol


def ema_h1_resists_short(row: pd.Series, *, tol_atr: float = 0.35) -> bool:
    close = float(row["close"])
    ema50 = float(row.get("ema50", close))
    ema200 = float(row.get("ema200", close))
    atr = float(row.get("atr14", 0))
    if np.isnan(atr) or atr <= 0:
        return True
    tol = atr * tol_atr
    return close <= ema50 + tol or close <= ema200 + tol


def _rsi_bounce_up(rsi: float, prev: float, min_delta: float) -> bool:
    return rsi >= prev - 0.05 and rsi > prev - min_delta


def _rsi_bounce_down(rsi: float, prev: float, min_delta: float) -> bool:
    return rsi <= prev + 0.05 and rsi < prev + min_delta


def _count_mid_touches(rsi_arr: np.ndarray, start: int, end: int, mid: tuple[float, float]) -> int:
    touches = 0
    in_mid = False
    for j in range(start, end + 1):
        val = rsi_arr[j]
        if np.isnan(val):
            continue
        inside = in_band(float(val), mid)
        if inside and not in_mid:
            touches += 1
        in_mid = inside
    return touches


def _setup1_long(rsi_arr: np.ndarray, i: int, mid: tuple[float, float], lookback: int) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi < lo or not _rsi_bounce_up(rsi, prev, 0.1):
        return False
    start = max(1, i - lookback)
    broke_up = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) > hi for j in range(start, i))
    if not broke_up:
        return False
    return not any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) < lo for j in range(start, i + 1))


def _setup1_short(rsi_arr: np.ndarray, i: int, mid: tuple[float, float], lookback: int) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi > hi or not _rsi_bounce_down(rsi, prev, 0.1):
        return False
    start = max(1, i - lookback)
    broke_down = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) < lo for j in range(start, i))
    if not broke_down:
        return False
    return not any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) > hi for j in range(start, i + 1))


def _setup2_long(
    rsi_arr: np.ndarray,
    i: int,
    mid: tuple[float, float],
    high: tuple[float, float],
    lookback: int,
    max_touches: int,
) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi < lo or not _rsi_bounce_up(rsi, prev, 0.1):
        return False
    start = max(1, i - lookback)
    touched_high = any(
        not np.isnan(rsi_arr[j]) and in_band(float(rsi_arr[j]), high) for j in range(start, i)
    )
    if not touched_high:
        return False
    was_above = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) > hi for j in range(start, i))
    if not was_above:
        return False
    touches = _count_mid_touches(rsi_arr, start, i, mid)
    return 1 <= touches <= max_touches


def _setup2_short(
    rsi_arr: np.ndarray,
    i: int,
    mid: tuple[float, float],
    low: tuple[float, float],
    lookback: int,
    max_touches: int,
) -> bool:
    lo, hi = mid
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev) or not in_band(rsi, mid):
        return False
    if rsi > hi or not _rsi_bounce_down(rsi, prev, 0.1):
        return False
    start = max(1, i - lookback)
    touched_low = any(
        not np.isnan(rsi_arr[j]) and in_band(float(rsi_arr[j]), low) for j in range(start, i)
    )
    if not touched_low:
        return False
    was_below = any(not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) < lo for j in range(start, i))
    if not was_below:
        return False
    touches = _count_mid_touches(rsi_arr, start, i, mid)
    return 1 <= touches <= max_touches


def detect_entry_at_bar(
    df: pd.DataFrame,
    i: int,
    strategy: dict[str, Any],
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    if i < 2:
        return None, None, None

    cfg = load_rsi_h4_config(strategy)
    lookback = int(cfg.get("lookback_bars", 120))
    tol = float(cfg.get("ema_tolerance_atr", 0.35))
    setups_cfg = cfg.get("setups") or {}
    max_touches = int((setups_cfg.get("extreme_bounce") or {}).get("max_mid_touches", 2))

    rsi_arr = df["rsi14_h4"].to_numpy(dtype=float)
    row = df.iloc[i]
    rsi = float(rsi_arr[i])
    if np.isnan(rsi):
        return None, None, None

    mid = _band(cfg, "mid")
    high = _band(cfg, "high")
    low = _band(cfg, "low")

    candidates: list[dict[str, Any]] = []

    if (setups_cfg.get("extreme_bounce") or {}).get("enabled", True):
        if _setup2_long(rsi_arr, i, mid, high, lookback, max_touches) and ema_h1_supports_long(row, tol_atr=tol):
            candidates.append(
                {
                    "direction": "long",
                    "setup": "extreme_bounce",
                    "tag": TAG_EXTREME_BOUNCE,
                    "tags": [TAG_EXTREME_BOUNCE, TAG_EMA_CONFIRM],
                }
            )
        if _setup2_short(rsi_arr, i, mid, low, lookback, max_touches) and ema_h1_resists_short(row, tol_atr=tol):
            candidates.append(
                {
                    "direction": "short",
                    "setup": "extreme_bounce",
                    "tag": TAG_EXTREME_BOUNCE,
                    "tags": [TAG_EXTREME_BOUNCE, TAG_EMA_CONFIRM],
                }
            )

    if (setups_cfg.get("break_retest") or {}).get("enabled", True):
        if _setup1_long(rsi_arr, i, mid, lookback) and ema_h1_supports_long(row, tol_atr=tol):
            candidates.append(
                {
                    "direction": "long",
                    "setup": "break_retest",
                    "tag": TAG_BREAK_RETEST,
                    "tags": [TAG_BREAK_RETEST, TAG_EMA_CONFIRM],
                }
            )
        if _setup1_short(rsi_arr, i, mid, lookback) and ema_h1_resists_short(row, tol_atr=tol):
            candidates.append(
                {
                    "direction": "short",
                    "setup": "break_retest",
                    "tag": TAG_BREAK_RETEST,
                    "tags": [TAG_BREAK_RETEST, TAG_EMA_CONFIRM],
                }
            )

    if not candidates:
        return None, None, None

    candidates.sort(key=lambda c: (0 if c["setup"] == "extreme_bounce" else 1))
    signal = candidates[0]

    meta = {
        "setup_type": signal["setup"],
        "tags": signal.get("tags") or [signal["tag"]],
        "rsi14_h4": round(rsi, 1),
        "context": {
            "setup": signal["setup"],
            "rsi14_h4": round(rsi, 1),
            "detected_tags": [{"tag": signal["tag"], "score": 1.0}],
            "suggested_tags": signal.get("tags") or [signal["tag"]],
            "suggested_direction": signal["direction"],
        },
    }
    return signal["direction"], signal["tag"], meta


def infer_setup_tags_for_label(
    df: pd.DataFrame,
    i: int,
    direction: str,
    strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gắn tag setup cho label lịch sử — strict trước, suy luận RSI path nếu không khớp."""
    strict = classify_bar_for_direction(df, i, direction, strategy)
    if strict.get("setup"):
        return strict

    cfg = load_rsi_h4_config(strategy)
    rsi_arr = df["rsi14_h4"].to_numpy(dtype=float)
    if np.isnan(rsi_arr[i]):
        return {"tags": [], "setup": None, "tag": None}

    lookback = int(cfg.get("lookback_bars", 120))
    start = max(0, i - lookback)
    mid = _band(cfg, "mid")
    high = _band(cfg, "high")
    low = _band(cfg, "low")
    rsi = float(rsi_arr[i])
    row = df.iloc[i]
    tol = float(cfg.get("ema_tolerance_atr", 0.35))
    ema_ok = (
        ema_h1_supports_long(row, tol_atr=tol)
        if direction == "long"
        else ema_h1_resists_short(row, tol_atr=tol)
    )
    tags: list[str] = [TAG_EMA_CONFIRM] if ema_ok else []

    def touched_band(band: tuple[float, float], a: int, b: int) -> bool:
        return any(
            not np.isnan(rsi_arr[j]) and in_band(float(rsi_arr[j]), band)
            for j in range(a, b + 1)
        )

    setup = None
    if direction == "long":
        touched_high = touched_band(high, start, i)
        touched_mid = touched_band(mid, start, i)
        was_above = any(
            not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) > mid[1] for j in range(start, i + 1)
        )
        if touched_high and (in_band(rsi, mid) or rsi <= mid[1] + 6):
            setup = "extreme_bounce"
        elif touched_mid and was_above:
            setup = "break_retest"
        elif rsi > mid[1]:
            setup = "break_retest"
        elif touched_high:
            setup = "extreme_bounce"
    else:
        touched_low = touched_band(low, start, i)
        touched_mid = touched_band(mid, start, i)
        was_below = any(
            not np.isnan(rsi_arr[j]) and float(rsi_arr[j]) < mid[0] for j in range(start, i + 1)
        )
        if touched_low and (in_band(rsi, mid) or rsi >= mid[0] - 6):
            setup = "extreme_bounce"
        elif touched_mid and was_below:
            setup = "break_retest"
        elif rsi < mid[0]:
            setup = "break_retest"
        elif touched_low:
            setup = "extreme_bounce"

    if setup == "extreme_bounce":
        tags = sorted(set(tags) | {TAG_EXTREME_BOUNCE})
    elif setup == "break_retest":
        tags = sorted(set(tags) | {TAG_BREAK_RETEST})

    tag = None
    if setup == "extreme_bounce":
        tag = TAG_EXTREME_BOUNCE
    elif setup == "break_retest":
        tag = TAG_BREAK_RETEST

    return {"tags": sorted(set(tags)), "setup": setup, "tag": tag}


def classify_bar_for_direction(
    df: pd.DataFrame,
    i: int,
    direction: str,
    strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = load_rsi_h4_config(strategy)
    lookback = int(cfg.get("lookback_bars", 120))
    tol = float(cfg.get("ema_tolerance_atr", 0.35))
    max_touches = int((cfg.get("setups", {}).get("extreme_bounce") or {}).get("max_mid_touches", 2))
    rsi_arr = df["rsi14_h4"].to_numpy(dtype=float)
    row = df.iloc[i]
    mid = _band(cfg, "mid")
    high = _band(cfg, "high")
    low = _band(cfg, "low")

    if direction == "long":
        if _setup2_long(rsi_arr, i, mid, high, lookback, max_touches) and ema_h1_supports_long(row, tol_atr=tol):
            return {"tags": [TAG_EXTREME_BOUNCE, TAG_EMA_CONFIRM], "setup": "extreme_bounce", "tag": TAG_EXTREME_BOUNCE}
        if _setup1_long(rsi_arr, i, mid, lookback) and ema_h1_supports_long(row, tol_atr=tol):
            return {"tags": [TAG_BREAK_RETEST, TAG_EMA_CONFIRM], "setup": "break_retest", "tag": TAG_BREAK_RETEST}
    else:
        if _setup2_short(rsi_arr, i, mid, low, lookback, max_touches) and ema_h1_resists_short(row, tol_atr=tol):
            return {"tags": [TAG_EXTREME_BOUNCE, TAG_EMA_CONFIRM], "setup": "extreme_bounce", "tag": TAG_EXTREME_BOUNCE}
        if _setup1_short(rsi_arr, i, mid, lookback) and ema_h1_resists_short(row, tol_atr=tol):
            return {"tags": [TAG_BREAK_RETEST, TAG_EMA_CONFIRM], "setup": "break_retest", "tag": TAG_BREAK_RETEST}
    return {"tags": [], "setup": None}


def build_strategy(train_period: str, *, train_stats: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_rsi_h4_config({})
    stats = train_stats or {}
    return {
        "name": "rsi_h4_band",
        "train_period": train_period,
        "pipeline_flow": "RSI H4 band → EMA H1 → entry → TP theo vùng RSI",
        "rule_mode": "rsi_h4",
        "bands": cfg["bands"],
        "setups": cfg["setups"],
        "ema_tolerance_atr": cfg.get("ema_tolerance_atr", 0.35),
        "lookback_bars": cfg.get("lookback_bars", 120),
        "entry_cooldown_bars": cfg.get("entry_cooldown_bars", 24),
        "rsi_rise_min": cfg.get("rsi_rise_min", 0.3),
        "risk": cfg.get("risk", {}),
        "tags": {
            "primary": [TAG_BREAK_RETEST, TAG_EXTREME_BOUNCE],
            "confirm": [TAG_EMA_CONFIRM],
            "setup_labels": SETUP_META,
        },
        "train_stats": stats,
    }


def strategy_description() -> list[dict[str, str]]:
    return [
        {
            "id": "break_retest",
            "tag": TAG_BREAK_RETEST,
            "title": "Setup 1 — Break + retest vùng 50",
            "long": "RSI H4 vượt 52 → hồi 48–52 → bật tăng + EMA H1 hỗ trợ → TP vùng 68–72",
            "short": "RSI H4 thủng 48 → hồi 48–52 → bật giảm + EMA H1 kháng cự → TP vùng 28–32",
        },
        {
            "id": "extreme_bounce",
            "tag": TAG_EXTREME_BOUNCE,
            "title": "Setup 2 — Chạm 70/30, hồi 50, bật lại",
            "long": "Trên 50 → chạm 68–72 → hồi 48–52 (lần 1–2) → không thủng 48 → LONG → TP 68–72",
            "short": "Dưới 50 → chạm 28–32 → hồi 48–52 (lần 1–2) → không vượt 52 → SHORT → TP 28–32",
        },
    ]


def dist_ema_pips(row: pd.Series) -> dict[str, float]:
    close = float(row["close"])
    return {
        "dist_ema50_pips": round((close - float(row.get("ema50", close))) / PIP, 1),
        "dist_ema200_pips": round((close - float(row.get("ema200", close))) / PIP, 1),
    }
