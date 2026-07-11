"""Chiến lược EMA 50/200 H1 — pullback và golden/death cross."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import PIP, ROOT

CONFIG_PATH = ROOT / "config" / "ema_cross_strategy.json"

TAG_PULLBACK_LONG = "ema_pullback_long"
TAG_PULLBACK_SHORT = "ema_pullback_short"
TAG_CROSS_LONG = "ema_cross_long"
TAG_CROSS_SHORT = "ema_cross_short"

SETUP_META = {
    "pullback_long": {"tag": TAG_PULLBACK_LONG, "label": "Pullback LONG — hồi EMA50 trong uptrend"},
    "pullback_short": {"tag": TAG_PULLBACK_SHORT, "label": "Pullback SHORT — hồi EMA50 trong downtrend"},
    "cross_long": {"tag": TAG_CROSS_LONG, "label": "Golden cross + hồi EMA50"},
    "cross_short": {"tag": TAG_CROSS_SHORT, "label": "Death cross + hồi EMA50"},
}


def load_config(strategy: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {}
    if CONFIG_PATH.exists():
        base = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if not strategy:
        return base
    for key in (
        "setups",
        "risk",
        "ema_tolerance_atr",
        "lookback_bars",
        "cross_lookback_bars",
        "entry_cooldown_bars",
        "min_trend_sep_atr",
    ):
        if key in strategy and strategy[key] is not None:
            if isinstance(base.get(key), dict) and isinstance(strategy[key], dict):
                base[key] = {**base[key], **strategy[key]}
            else:
                base[key] = strategy[key]
    return base


def _near_ema50(row: pd.Series, tol_atr: float) -> bool:
    close = float(row["close"])
    ema50 = float(row.get("ema50", close))
    atr = float(row.get("atr14", 0))
    if np.isnan(atr) or atr <= 0:
        return abs(close - ema50) / PIP <= 15
    return abs(close - ema50) <= atr * tol_atr


def _trend_sep_ok(row: pd.Series, min_sep_atr: float) -> bool:
    ema50 = float(row.get("ema50", 0))
    ema200 = float(row.get("ema200", 0))
    atr = float(row.get("atr14", 0))
    if np.isnan(atr) or atr <= 0:
        return True
    return abs(ema50 - ema200) >= atr * min_sep_atr


def _fresh_cross(df: pd.DataFrame, i: int, direction: str, lookback: int) -> bool:
    if i < 2:
        return False
    start = max(1, i - lookback)
    for j in range(start, i):
        prev50 = float(df.iloc[j - 1]["ema50"])
        prev200 = float(df.iloc[j - 1]["ema200"])
        cur50 = float(df.iloc[j]["ema50"])
        cur200 = float(df.iloc[j]["ema200"])
        if direction == "long" and prev50 <= prev200 and cur50 > cur200:
            return True
        if direction == "short" and prev50 >= prev200 and cur50 < cur200:
            return True
    return False


def _pullback_long(row: pd.Series, cfg: dict[str, Any]) -> bool:
    ema50 = float(row["ema50"])
    ema200 = float(row["ema200"])
    if ema50 <= ema200:
        return False
    if not _trend_sep_ok(row, float(cfg.get("min_trend_sep_atr", 0.12))):
        return False
    if not _near_ema50(row, float(cfg.get("ema_tolerance_atr", 0.4))):
        return False
    return float(row["close"]) >= float(row["open"])


def _pullback_short(row: pd.Series, cfg: dict[str, Any]) -> bool:
    ema50 = float(row["ema50"])
    ema200 = float(row["ema200"])
    if ema50 >= ema200:
        return False
    if not _trend_sep_ok(row, float(cfg.get("min_trend_sep_atr", 0.12))):
        return False
    if not _near_ema50(row, float(cfg.get("ema_tolerance_atr", 0.4))):
        return False
    return float(row["close"]) <= float(row["open"])


def detect_entry_at_bar(
    df: pd.DataFrame,
    i: int,
    strategy: dict[str, Any],
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    if i < 3:
        return None, None, None
    cfg = load_config(strategy)
    setups = cfg.get("setups") or {}
    row = df.iloc[i]
    cross_lb = int(cfg.get("cross_lookback_bars", 24))
    candidates: list[dict[str, Any]] = []

    if (setups.get("pullback_long") or {}).get("enabled", True) and _pullback_long(row, cfg):
        candidates.append(
            {"direction": "long", "setup": "pullback_long", "tag": TAG_PULLBACK_LONG, "tags": [TAG_PULLBACK_LONG]}
        )
    if (setups.get("pullback_short") or {}).get("enabled", True) and _pullback_short(row, cfg):
        candidates.append(
            {"direction": "short", "setup": "pullback_short", "tag": TAG_PULLBACK_SHORT, "tags": [TAG_PULLBACK_SHORT]}
        )
    if (setups.get("cross_long") or {}).get("enabled", True):
        if _fresh_cross(df, i, "long", cross_lb) and _pullback_long(row, cfg):
            candidates.append(
                {"direction": "long", "setup": "cross_long", "tag": TAG_CROSS_LONG, "tags": [TAG_CROSS_LONG]}
            )
    if (setups.get("cross_short") or {}).get("enabled", True):
        if _fresh_cross(df, i, "short", cross_lb) and _pullback_short(row, cfg):
            candidates.append(
                {"direction": "short", "setup": "cross_short", "tag": TAG_CROSS_SHORT, "tags": [TAG_CROSS_SHORT]}
            )

    if not candidates:
        return None, None, None
    candidates.sort(key=lambda c: (0 if "cross" in c["setup"] else 1))
    signal = candidates[0]
    meta = {
        "setup_type": signal["setup"],
        "tags": signal["tags"],
        "context": {
            "setup": signal["setup"],
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
    row = df.iloc[i]
    tags: list[str] = []
    setup = None
    if direction == "long":
        if _pullback_long(row, cfg):
            setup = "pullback_long"
            tags = [TAG_PULLBACK_LONG]
        elif _fresh_cross(df, i, "long", int(cfg.get("cross_lookback_bars", 24))):
            setup = "cross_long"
            tags = [TAG_CROSS_LONG]
    else:
        if _pullback_short(row, cfg):
            setup = "pullback_short"
            tags = [TAG_PULLBACK_SHORT]
        elif _fresh_cross(df, i, "short", int(cfg.get("cross_lookback_bars", 24))):
            setup = "cross_short"
            tags = [TAG_CROSS_SHORT]
    tag = tags[0] if tags else None
    return {"tags": tags, "setup": setup, "tag": tag}


def simulate_trade(
    df: pd.DataFrame,
    i: int,
    direction: str,
    strategy: dict[str, Any],
    cost: float,
) -> dict[str, Any] | None:
    from .backtest import _simulate_trade as _atr_sim

    cfg = load_config(strategy)
    risk = cfg.get("risk") or {}
    sl_mult = float(risk.get("sl_atr_mult", 1.2))
    target_rr = float(risk.get("target_rr", 2.0))
    return _atr_sim(df, i, direction, sl_mult, sl_mult * target_rr, cost)


def build_strategy(train_period: str, *, train_stats: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = load_config({})
    return {
        "strategy_id": "ema_cross",
        "name": "ema_cross",
        "train_period": train_period,
        "pipeline_flow": "EMA50/200 H1 → setup → entry → SL/TP ATR",
        "rule_mode": "ema_cross",
        "setups": cfg["setups"],
        "ema_tolerance_atr": cfg.get("ema_tolerance_atr", 0.4),
        "lookback_bars": cfg.get("lookback_bars", 80),
        "cross_lookback_bars": cfg.get("cross_lookback_bars", 24),
        "entry_cooldown_bars": cfg.get("entry_cooldown_bars", 24),
        "min_trend_sep_atr": cfg.get("min_trend_sep_atr", 0.12),
        "risk": cfg.get("risk", {}),
        "tags": {"primary": list(SETUP_META.keys()), "setup_labels": SETUP_META},
        "train_stats": train_stats or {},
    }


def strategy_description() -> list[dict[str, str]]:
    return [
        {
            "id": "pullback_long",
            "tag": TAG_PULLBACK_LONG,
            "title": "Pullback LONG",
            "long": "EMA50 > EMA200, giá hồi về EMA50, nến xanh → LONG",
            "short": "—",
        },
        {
            "id": "pullback_short",
            "tag": TAG_PULLBACK_SHORT,
            "title": "Pullback SHORT",
            "long": "—",
            "short": "EMA50 < EMA200, giá hồi về EMA50, nến đỏ → SHORT",
        },
        {
            "id": "cross_long",
            "tag": TAG_CROSS_LONG,
            "title": "Golden cross",
            "long": "EMA50 vừa cắt lên EMA200 + pullback EMA50 → LONG",
            "short": "—",
        },
        {
            "id": "cross_short",
            "tag": TAG_CROSS_SHORT,
            "title": "Death cross",
            "long": "—",
            "short": "EMA50 vừa cắt xuống EMA200 + pullback EMA50 → SHORT",
        },
    ]


def dist_ema_pips(row: pd.Series) -> dict[str, float]:
    close = float(row["close"])
    return {
        "dist_ema50_pips": round((close - float(row.get("ema50", close))) / PIP, 1),
        "dist_ema200_pips": round((close - float(row.get("ema200", close))) / PIP, 1),
    }
