"""Locked validated params vs sandbox tuning."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

from besttrade.paths import BESTTRADE_ROOT


FORWARD_PATH = BESTTRADE_ROOT / "config" / "forward_test.json"


def load_strategy_config() -> dict[str, Any]:
    path = BESTTRADE_ROOT / "config" / "strategy.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def locked_params() -> dict[str, Any]:
    """Production profile — không chỉnh khi forward test."""
    return dict(load_strategy_config()["params"])


def locked_risk() -> dict[str, float]:
    risk = load_strategy_config().get("risk", {})
    return {
        "sl_pct": float(risk.get("sl_pct", 0.02)),
        "min_rr": float(risk.get("min_rr", 2.0)),
    }


def load_forward_test() -> dict[str, Any] | None:
    if not FORWARD_PATH.exists():
        return None
    try:
        return json.loads(FORWARD_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_forward_test(data: dict[str, Any]) -> Path:
    FORWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    FORWARD_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return FORWARD_PATH


def start_forward_test(equity: float) -> dict[str, Any]:
    from datetime import datetime, timezone

    data = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "locked_params": locked_params(),
        "locked_risk": locked_risk(),
        "initial_equity": float(equity),
        "status": "active",
    }
    save_forward_test(data)
    return data


def stop_forward_test() -> dict[str, Any] | None:
    data = load_forward_test()
    if not data:
        return None
    from datetime import datetime, timezone

    data["status"] = "stopped"
    data["stopped_at"] = datetime.now(timezone.utc).isoformat()
    save_forward_test(data)
    return data


def active_params(sandbox: bool, sandbox_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    if sandbox:
        base = locked_params()
        if sandbox_overrides:
            base.update(sandbox_overrides)
        return base
    forward = load_forward_test()
    if forward and forward.get("status") == "active":
        return dict(forward.get("locked_params", locked_params()))
    return locked_params()


def params_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    keys = set(a) | set(b)
    for k in keys:
        va, vb = a.get(k), b.get(k)
        if isinstance(va, float) or isinstance(vb, float):
            if abs(float(va or 0) - float(vb or 0)) > 1e-9:
                return False
        elif va != vb:
            return False
    return True
