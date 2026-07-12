from __future__ import annotations

from typing import Any

from backend.core.config import STRATEGY_PATH, save_json
from backend.strategy.rsi_ema_v1.config import load_strategy_config


def load_strategy_file() -> dict[str, Any]:
    return load_strategy_config()


def save_strategy_file(cfg: dict[str, Any]) -> dict[str, Any]:
    save_json(STRATEGY_PATH, cfg)
    return cfg


def apply_setup_recommendations(
    recommendations: list[dict[str, Any]],
    *,
    min_samples: int = 5,
    wr_threshold: float = 0.38,
) -> dict[str, Any]:
    """Tắt setup WR < threshold khi đủ mẫu — ghi vào strategy JSON."""
    cfg = load_strategy_file()
    setups = cfg.setdefault("setups", {})
    changes: list[dict[str, Any]] = []

    for rec in recommendations:
        if rec.get("action") != "disable":
            continue
        sid = rec.get("setup_id")
        if not sid or sid not in setups:
            continue
        if rec.get("samples", 0) < min_samples:
            continue
        if rec.get("win_rate", 1) >= wr_threshold:
            continue
        was_enabled = setups[sid].get("enabled", True)
        setups[sid]["enabled"] = False
        setups[sid]["disabled_reason"] = rec.get("reason", f"WR < {wr_threshold:.0%}")
        setups[sid]["disabled_at_samples"] = rec.get("samples")
        changes.append({"setup_id": sid, "was_enabled": was_enabled, "enabled": False})

    if changes:
        save_strategy_file(cfg)
    return {"applied": changes, "strategy": cfg}
