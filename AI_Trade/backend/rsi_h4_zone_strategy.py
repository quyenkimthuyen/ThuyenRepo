"""RSI H4 zone exit — rời vùng 70 SHORT (TP 30), rời vùng 30 LONG (TP 70)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import PIP, ROOT
from .rsi_h4_strategy import _band, in_band

CONFIG_PATH = ROOT / "config" / "rsi_h4_zone_strategy.json"

TAG_EXIT_HIGH_SHORT = "rsi_exit_high_short"
TAG_EXIT_LOW_LONG = "rsi_exit_low_long"

SETUP_META = {
    "exit_high_short": {
        "tag": TAG_EXIT_HIGH_SHORT,
        "label": "Rời vùng 70 → SHORT · TP RSI 30",
    },
    "exit_low_long": {
        "tag": TAG_EXIT_LOW_LONG,
        "label": "Rời vùng 30 → LONG · TP RSI 70",
    },
}


def load_config(strategy: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not strategy:
        return base
    for key in ("bands", "setups", "risk", "lookback_bars", "entry_cooldown_bars", "exit_confirm_bars"):
        if key in strategy and strategy[key] is not None:
            if isinstance(base.get(key), dict) and isinstance(strategy[key], dict):
                base[key] = {**base[key], **strategy[key]}
            else:
                base[key] = strategy[key]
    return base


def _touched_band(rsi_arr: np.ndarray, end: int, lookback: int, band: tuple[float, float]) -> bool:
    start = max(0, end - lookback)
    for j in range(start, end + 1):
        val = rsi_arr[j]
        if not np.isnan(val) and in_band(float(val), band):
            return True
    return False


def _exit_high_short(rsi_arr: np.ndarray, i: int, high: tuple[float, float], lookback: int) -> bool:
    if i < 1:
        return False
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev):
        return False
    hi_lo, hi_hi = high
    was_high = in_band(prev, high) or prev >= hi_lo
    if not was_high:
        was_high = _touched_band(rsi_arr, i - 1, lookback, high)
    return was_high and rsi < hi_lo


def _exit_low_long(rsi_arr: np.ndarray, i: int, low: tuple[float, float], lookback: int) -> bool:
    if i < 1:
        return False
    rsi = float(rsi_arr[i])
    prev = float(rsi_arr[i - 1])
    if np.isnan(rsi) or np.isnan(prev):
        return False
    lo_lo, lo_hi = low
    was_low = in_band(prev, low) or prev <= lo_hi
    if not was_low:
        was_low = _touched_band(rsi_arr, i - 1, lookback, low)
    return was_low and rsi > lo_hi


def detect_entry_at_bar(
    df: pd.DataFrame,
    i: int,
    strategy: dict[str, Any],
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    if i < 2:
        return None, None, None
    cfg = load_config(strategy)
    setups = cfg.get("setups") or {}
    lookback = int(cfg.get("lookback_bars", 80))
    rsi_arr = df["rsi14_h4"].to_numpy(dtype=float)
    high = _band(cfg, "high")
    low = _band(cfg, "low")
    rsi = float(rsi_arr[i])
    if np.isnan(rsi):
        return None, None, None

    candidates: list[dict[str, Any]] = []
    if (setups.get("exit_low_long") or {}).get("enabled", True) and _exit_low_long(rsi_arr, i, low, lookback):
        candidates.append(
            {
                "direction": "long",
                "setup": "exit_low_long",
                "tag": TAG_EXIT_LOW_LONG,
                "tags": [TAG_EXIT_LOW_LONG],
            }
        )
    if (setups.get("exit_high_short") or {}).get("enabled", True) and _exit_high_short(rsi_arr, i, high, lookback):
        candidates.append(
            {
                "direction": "short",
                "setup": "exit_high_short",
                "tag": TAG_EXIT_HIGH_SHORT,
                "tags": [TAG_EXIT_HIGH_SHORT],
            }
        )

    if not candidates:
        return None, None, None
    signal = candidates[0]
    meta = {
        "setup_type": signal["setup"],
        "tags": signal["tags"],
        "rsi14_h4": round(rsi, 1),
        "context": {
            "setup": signal["setup"],
            "rsi14_h4": round(rsi, 1),
            "detected_tags": [{"tag": signal["tag"], "score": 1.0}],
            "suggested_tags": signal["tags"],
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
    cfg = load_config(strategy)
    lookback = int(cfg.get("lookback_bars", 80))
    rsi_arr = df["rsi14_h4"].to_numpy(dtype=float)
    high = _band(cfg, "high")
    low = _band(cfg, "low")
    setup = None
    tags: list[str] = []
    if direction == "long" and _exit_low_long(rsi_arr, i, low, lookback):
        setup = "exit_low_long"
        tags = [TAG_EXIT_LOW_LONG]
    elif direction == "short" and _exit_high_short(rsi_arr, i, high, lookback):
        setup = "exit_high_short"
        tags = [TAG_EXIT_HIGH_SHORT]
    return {"tags": tags, "setup": setup, "tag": tags[0] if tags else None}


def simulate_trade(
    df: pd.DataFrame,
    i: int,
    direction: str,
    strategy: dict[str, Any],
    cost: float,
) -> dict[str, Any] | None:
    from .backtest import _simulate_trade_rsi_h4

    return _simulate_trade_rsi_h4(df, i, direction, strategy, cost)


def build_strategy(train_period: str, *, train_stats: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config({})
    return {
        "strategy_id": "rsi_h4_zone",
        "name": "rsi_h4_zone",
        "train_period": train_period,
        "pipeline_flow": "RSI H4 rời vùng 70/30 → entry → TP vùng đối diện",
        "rule_mode": "rsi_h4_zone",
        "bands": cfg["bands"],
        "setups": cfg["setups"],
        "lookback_bars": cfg.get("lookback_bars", 80),
        "entry_cooldown_bars": cfg.get("entry_cooldown_bars", 24),
        "risk": cfg.get("risk", {}),
        "tags": {"primary": [TAG_EXIT_LOW_LONG, TAG_EXIT_HIGH_SHORT], "setup_labels": SETUP_META},
        "train_stats": train_stats or {},
    }


def strategy_description() -> list[dict[str, str]]:
    return [
        {
            "id": "exit_low_long",
            "tag": TAG_EXIT_LOW_LONG,
            "title": "Rời vùng 30 → LONG",
            "long": "RSI H4 trong vùng 28–32 rồi thoát lên trên 32 → LONG → TP vùng 68–72",
            "short": "—",
        },
        {
            "id": "exit_high_short",
            "tag": TAG_EXIT_HIGH_SHORT,
            "title": "Rời vùng 70 → SHORT",
            "long": "—",
            "short": "RSI H4 trong vùng 68–72 rồi thoát xuống dưới 68 → SHORT → TP vùng 28–32",
        },
    ]


def dist_ema_pips(row: pd.Series) -> dict[str, float]:
    close = float(row["close"])
    return {
        "dist_ema50_pips": round((close - float(row.get("ema50", close))) / PIP, 1),
        "dist_ema200_pips": round((close - float(row.get("ema200", close))) / PIP, 1),
    }
