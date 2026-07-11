"""Workflow status — Chiến lược → Label → Analyze → Backtest."""

from __future__ import annotations

from typing import Any

from .analyzer import load_strategy
from .bar_annotations import load_bar_annotations
from .labels import load_setups
from .periods import filter_setups_for_train, is_train_period, normalize_setup_period, period_config, resolve_period
from .setup_quality import load_quality_config
from .strategy_registry import default_strategy_id, list_strategy_types, resolve_strategy_id


def workflow_status(
    *,
    train_period: str | None = None,
    strategy_id: str | None = None,
) -> dict[str, Any]:
    from .periods import default_train_period

    train_period = resolve_period(train_period or default_train_period())
    sid = resolve_strategy_id(strategy_id or default_strategy_id())
    year = period_config(train_period).get("year")

    strat = load_strategy(train_period, sid)
    setups = filter_setups_for_train(load_setups(), train_period)
    labeled = [s for s in setups if s.get("result") in ("win", "loss")]
    target = int(load_quality_config().get("target_setups_per_year", 50))
    min_analyze = 5

    strat_type = next((t for t in list_strategy_types() if t["id"] == sid), {})
    enabled_setups = []
    if strat:
        for setup_id, cfg in (strat.get("setups") or {}).items():
            if cfg.get("enabled", True):
                enabled_setups.append(cfg.get("label") or setup_id)

    alignment = (strat or {}).get("alignment") or {}
    last_bt = (strat or {}).get("last_backtest") or {}

    steps = [
        {
            "id": "strategy",
            "label": "Chiến lược",
            "done": bool(strat),
            "detail": strat_type.get("label") or sid if strat else "Chọn loại & lưu cấu hình",
        },
        {
            "id": "label",
            "label": "Label",
            "done": len(labeled) >= min_analyze,
            "progress": len(labeled),
            "target": target,
            "detail": f"{len(labeled)}/{target} setup · {len([a for a in load_bar_annotations() if normalize_setup_period(a.get('period')) == train_period])} nến",
        },
        {
            "id": "analyze",
            "label": "Analyze",
            "done": bool(strat and strat.get("analyzed_at")),
            "detail": (
                f"WR train {round((strat or {}).get('win_rate_train', 0) * 100)}%"
                if strat and strat.get("win_rate_train") is not None
                else "Chưa phân tích"
            ),
        },
        {
            "id": "backtest",
            "label": "Backtest",
            "done": bool(last_bt.get("profit_factor")),
            "detail": (
                f"PF {last_bt.get('profit_factor')} · {'PASS' if last_bt.get('pass') else 'chưa pass'}"
                if last_bt.get("profit_factor") is not None
                else "Chưa chạy"
            ),
        },
    ]

    return {
        "train_period": train_period,
        "train_year": year,
        "strategy_id": sid,
        "strategy_label": strat_type.get("label") or sid,
        "strategy_ready": bool(strat),
        "enabled_setups": enabled_setups,
        "setup_count": len(setups),
        "labeled_count": len(labeled),
        "target_setups": target,
        "alignment_ratio": alignment.get("ratio"),
        "steps": steps,
        "can_analyze": len(labeled) >= min_analyze,
        "can_backtest": bool(strat),
    }
