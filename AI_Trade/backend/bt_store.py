"""Persist backtest runs for review and comparison."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import DATA_DIR
from .data_service import load_splits

BT_RUNS_PATH = DATA_DIR / "backtests" / "runs.json"


def _ensure_file() -> None:
    BT_RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not BT_RUNS_PATH.exists():
        BT_RUNS_PATH.write_text(json.dumps({"runs": []}, indent=2), encoding="utf-8")


def _load_payload() -> dict[str, Any]:
    _ensure_file()
    return json.loads(BT_RUNS_PATH.read_text(encoding="utf-8"))


def _save_payload(payload: dict[str, Any]) -> None:
    _ensure_file()
    BT_RUNS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def period_label(period: str) -> str:
    splits = load_splits()["periods"]
    cfg = splits.get(period) or {}
    short = {"train": "2022", "validation": "2023", "test": "2024–26"}.get(period, period)
    return cfg.get("label") or short


def _slug(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return base[:40] or "run"


def run_summary(run: dict[str, Any]) -> dict[str, Any]:
    metrics = run.get("metrics") or {}
    return {
        "id": run["id"],
        "name": run.get("name"),
        "period": run.get("period"),
        "period_label": run.get("period_label"),
        "created_at": run.get("created_at"),
        "strategy_name": run.get("strategy_name"),
        "status": run.get("status"),
        "metrics": metrics,
        "trade_count": run.get("trade_count_total") or metrics.get("trades") or len(run.get("trades") or []),
        "pass": metrics.get("pass"),
    }


def list_runs(*, period: str | None = None) -> list[dict[str, Any]]:
    runs = _load_payload().get("runs", [])
    if period:
        runs = [r for r in runs if r.get("period") == period]
    runs = sorted(runs, key=lambda r: r.get("created_at", ""), reverse=True)
    return [run_summary(r) for r in runs]


def get_run(run_id: str) -> dict[str, Any] | None:
    for run in _load_payload().get("runs", []):
        if run.get("id") == run_id:
            return run
    return None


def save_run(
    result: dict[str, Any],
    *,
    name: str | None = None,
    period: str | None = None,
) -> dict[str, Any]:
    period = period or result.get("period") or "validation"
    splits = load_splits()["periods"]
    if period not in splits:
        raise ValueError(f"Unknown period: {period}")

    now = datetime.now(timezone.utc)
    default_name = f"{period_label(period)} · {now.strftime('%d/%m/%Y %H:%M')}"
    run_name = (name or "").strip() or default_name
    run_id = f"bt-{_slug(run_name)}-{uuid.uuid4().hex[:6]}"

    record = {
        **result,
        "id": run_id,
        "name": run_name,
        "period": period,
        "period_label": period_label(period),
        "created_at": now.isoformat(),
        "strategy_name": result.get("strategy"),
        "saved_at": now.isoformat(),
    }

    payload = _load_payload()
    runs = payload.get("runs", [])
    runs = [r for r in runs if r.get("id") != run_id]
    runs.append(record)
    payload["runs"] = runs
    _save_payload(payload)
    return record


def rename_run(run_id: str, name: str) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise ValueError("Tên không được trống")
    payload = _load_payload()
    for run in payload.get("runs", []):
        if run.get("id") == run_id:
            run["name"] = name
            _save_payload(payload)
            return run
    raise KeyError(run_id)


def delete_run(run_id: str) -> None:
    payload = _load_payload()
    runs = [r for r in payload.get("runs", []) if r.get("id") != run_id]
    payload["runs"] = runs
    _save_payload(payload)


def compare_runs(run_ids: list[str]) -> dict[str, Any]:
    runs = []
    for rid in run_ids:
        run = get_run(rid)
        if run:
            runs.append(run_summary(run))
    return {"runs": runs, "count": len(runs)}
