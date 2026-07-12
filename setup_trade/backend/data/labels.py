from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from backend.core.config import SETUPS_PATH, load_json, save_json
from backend.indicators import add_indicators
from backend.data.loader import load_candles, slice_period
from backend.strategy.rsi_ema_v1.engine import RsiEmaV1Strategy
from backend.simulator.trade import simulate_trade


def _load_store() -> dict[str, Any]:
    if SETUPS_PATH.exists():
        return load_json(SETUPS_PATH)
    return {"setups": []}


def _save_store(data: dict[str, Any]) -> None:
    save_json(SETUPS_PATH, data)


def list_setups(*, period: str | None = None) -> list[dict[str, Any]]:
    setups = _load_store().get("setups", [])
    if period:
        setups = [s for s in setups if s.get("label_period") == period]
    return setups


def create_setup(
    *,
    direction: str,
    entry_time: str,
    label_period: str,
    setup_id: str | None = None,
    note: str = "",
    discretionary_override: bool = False,
) -> dict[str, Any]:
    df = add_indicators(slice_period(load_candles(), label_period))
    ts = pd.Timestamp(entry_time)
    strategy = RsiEmaV1Strategy()

    if not discretionary_override:
        gate = strategy.validate_label(df, ts, direction, setup_id)
        if not gate["valid"]:
            raise ValueError(gate["reason"])

    detected = strategy.detect_at_time(df, ts)
    i = int(df.index.get_loc(ts)) if ts in df.index else int(df.index.get_indexer([ts], method="nearest")[0])
    outcome = simulate_trade(df, i, direction, setup_id=(detected or {}).get("setup_id"))

    setup = {
        "id": str(uuid.uuid4())[:8],
        "direction": direction,
        "entry_time": entry_time,
        "entry_price": round(float(df.iloc[i]["close"]), 5),
        "setup_id": (detected or {}).get("setup_id") or setup_id,
        "label_period": label_period,
        "state_snapshot": (detected or {}).get("state_snapshot"),
        "note": note,
        "discretionary_override": discretionary_override,
        "outcome": outcome,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store = _load_store()
    store.setdefault("setups", []).append(setup)
    _save_store(store)
    return setup


def delete_setup(setup_id: str) -> bool:
    store = _load_store()
    before = len(store.get("setups", []))
    store["setups"] = [s for s in store.get("setups", []) if s.get("id") != setup_id]
    _save_store(store)
    return len(store["setups"]) < before


def label_status(label_period: str) -> dict:
    from backend.research.label_scan import label_status as _status

    return _status(label_period)


def auto_label_period(label_period: str, *, max_add: int | None = None) -> dict:
    from backend.research.label_scan import auto_label_period as _scan

    return _scan(label_period, max_add=max_add)
