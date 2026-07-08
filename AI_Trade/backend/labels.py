from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import LABELS_PATH, PIP
from .data_service import load_candles, period_for_timestamp
from .indicators import add_indicators
from .tags import infer_tags, normalize_tags


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
            # conservative: SL first on same bar
            return "loss", ts
        if hit_sl:
            return "loss", ts
        if hit_tp:
            return "win", ts
    return "open", None


def enrich_setup(setup: dict[str, Any], df: pd.DataFrame | None = None) -> dict[str, Any]:
    df = df if df is not None else add_indicators(load_candles())
    entry_time = pd.Timestamp(setup["entry_time"])
    if entry_time.tz is None:
        entry_time = entry_time.tz_localize("UTC")
    else:
        entry_time = entry_time.tz_convert("UTC")

    nearest_idx = df.index.get_indexer([entry_time], method="nearest")[0]
    bar_time = df.index[nearest_idx]
    row = df.iloc[nearest_idx]

    direction = setup["direction"]
    entry = float(setup["entry_price"])
    sl = float(setup["stop_loss"])
    tp = float(setup["take_profit"])

    result, exit_time = resolve_outcome(df, bar_time, direction, sl, tp)

    enriched = {
        **setup,
        "entry_time": bar_time.isoformat(),
        "planned_rr": planned_rr(direction, entry, sl, tp),
        "result": result,
        "exit_time": exit_time.isoformat() if exit_time is not None else None,
        "period": period_for_timestamp(bar_time),
        "tags": infer_tags(setup),
        "features": {
            "rsi14": round(float(row.get("rsi14", 0)), 2),
            "ema50": round(float(row.get("ema50", 0)), 5),
            "ema200": round(float(row.get("ema200", 0)), 5),
            "atr14": round(float(row.get("atr14", 0)), 5),
            "trend_up": bool(row.get("trend_up", False)),
            "close_above_ema50": bool(row.get("close_above_ema50", False)),
            "close_above_ema200": bool(row.get("close_above_ema200", False)),
            "dist_ema50_pips": round((entry - float(row.get("ema50", entry))) / PIP, 1),
        },
    }
    return enriched


def create_setup(payload: dict[str, Any]) -> dict[str, Any]:
    entry_time = pd.Timestamp(payload["entry_time"])
    period = period_for_timestamp(entry_time)
    if period != "train":
        raise ValueError("Chỉ được đánh dấu setup trong năm Train (2022).")

    df = add_indicators(load_candles())
    setup = {
        "id": payload.get("id") or str(uuid.uuid4())[:8],
        "symbol": payload.get("symbol", "EURUSD"),
        "timeframe": payload.get("timeframe", "1H"),
        "direction": payload["direction"],
        "entry_time": payload["entry_time"],
        "entry_price": float(payload["entry_price"]),
        "stop_loss": float(payload["stop_loss"]),
        "take_profit": float(payload["take_profit"]),
        "tags": normalize_tags(payload.get("tags")),
        "note": payload.get("note", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    enriched = enrich_setup(setup, df)
    setups = load_setups()
    setups = [s for s in setups if s["id"] != enriched["id"]]
    setups.append(enriched)
    save_setups(setups)
    return enriched


def update_setup(setup_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    setups = load_setups()
    idx = next((i for i, s in enumerate(setups) if s["id"] == setup_id), None)
    if idx is None:
        raise KeyError(setup_id)

    merged = {**setups[idx], **payload, "id": setup_id}
    if any(k in payload for k in ("entry_time", "entry_price", "stop_loss", "take_profit", "direction")):
        entry_time = pd.Timestamp(merged["entry_time"])
        if period_for_timestamp(entry_time) != "train":
            raise ValueError("Chỉ được sửa setup trong năm Train (2022).")
        merged["tags"] = normalize_tags(merged.get("tags"))
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()

    enriched = enrich_setup(merged)
    setups[idx] = enriched
    save_setups(setups)
    return enriched


def delete_setup(setup_id: str) -> None:
    setups = [s for s in load_setups() if s["id"] != setup_id]
    save_setups(setups)
