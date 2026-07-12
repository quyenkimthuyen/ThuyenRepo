from __future__ import annotations

from typing import Any

from backend.core.config import PERIODS_PATH, load_json
from backend.core.folds import require_label_period
from backend.data.labels import create_setup, list_setups
from backend.indicators import add_indicators
from backend.data.loader import load_candles, slice_period
from backend.strategy.rsi_ema_v1.engine import RsiEmaV1Strategy


def label_status(label_period: str) -> dict[str, Any]:
    require_label_period(label_period)
    cfg = load_json(PERIODS_PATH)
    target = int((cfg.get("rules") or {}).get("target_setups_per_label_year", 50))
    setups = list_setups(period=label_period)
    return {
        "label_period": label_period,
        "count": len(setups),
        "target": target,
        "remaining": max(0, target - len(setups)),
        "complete": len(setups) >= target,
    }


def auto_label_period(label_period: str, *, max_add: int | None = None) -> dict[str, Any]:
    """Quét signal gate-pass trên label period và lưu setup (Phase 4)."""
    status = label_status(label_period)
    remaining = status["remaining"]
    if remaining <= 0:
        return {"status": "complete", "added": 0, **status}

    limit = min(remaining, max_add) if max_add is not None else remaining
    df = add_indicators(slice_period(load_candles(), label_period))
    strategy = RsiEmaV1Strategy()

    existing_times = {s["entry_time"] for s in list_setups(period=label_period)}
    signals = strategy.scan_period(df)

    # Ưu tiên đa dạng theo tháng
    by_month: dict[str, list[dict[str, Any]]] = {}
    for sig in signals:
        et = sig["entry_time"]
        if et in existing_times:
            continue
        month = et[:7]
        by_month.setdefault(month, []).append(sig)

    picked: list[dict[str, Any]] = []
    months = sorted(by_month.keys())
    idx = 0
    while len(picked) < limit and months:
        month = months[idx % len(months)]
        bucket = by_month.get(month) or []
        if bucket:
            picked.append(bucket.pop(0))
            if not bucket:
                by_month.pop(month, None)
                months = sorted(by_month.keys())
        idx += 1
        if idx > limit * 24:
            break

    added: list[dict[str, Any]] = []
    errors: list[str] = []
    for sig in picked[:limit]:
        try:
            setup = create_setup(
                direction=sig["direction"],
                entry_time=sig["entry_time"],
                label_period=label_period,
                setup_id=sig["setup_id"],
                note="auto_label gate-pass",
            )
            added.append(setup)
            existing_times.add(sig["entry_time"])
        except ValueError as exc:
            errors.append(f"{sig['entry_time']}: {exc}")

    return {
        "status": "ok",
        "label_period": label_period,
        "added": len(added),
        "errors": errors,
        "signals_available": len(signals),
        "new_count": len(list_setups(period=label_period)),
        "target": status["target"],
    }
