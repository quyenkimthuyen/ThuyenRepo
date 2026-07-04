from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OOSVerdict:
    passed: bool
    reasons: list[str]
    metrics: dict[str, Any]
    train_metrics: dict[str, Any]


def evaluate_oos_gate(
    oos_metrics: dict[str, Any],
    train_metrics: dict[str, Any],
    gate_cfg: dict,
) -> OOSVerdict:
    reasons: list[str] = []
    passed = True

    checks = [
        ("win_rate", oos_metrics.get("win_rate", 0), gate_cfg.get("min_win_rate", 0.55), ">="),
        ("profit_factor", oos_metrics.get("profit_factor", 0), gate_cfg.get("min_profit_factor", 1.15), ">="),
        ("monthly_stability", oos_metrics.get("monthly_stability", 0), gate_cfg.get("min_monthly_stability", 0.50), ">="),
        ("trade_count", oos_metrics.get("trade_count", 0), gate_cfg.get("min_trades", 150), ">="),
        ("realized_rr", oos_metrics.get("realized_rr", 0), 1.5, ">="),
    ]

    for name, value, threshold, op in checks:
        if op == ">=" and value < threshold:
            passed = False
            reasons.append(f"{name}={value:.4f} < {threshold}")

    max_dd = gate_cfg.get("max_drawdown", 0.30)
    if oos_metrics.get("max_drawdown", 1) > max_dd:
        passed = False
        reasons.append(f"max_drawdown={oos_metrics.get('max_drawdown', 0):.4f} > {max_dd}")

    if oos_metrics.get("halted"):
        passed = False
        reasons.append(f"halted: {oos_metrics.get('halt_reason', '')}")

    train_wr = train_metrics.get("win_rate", 0)
    oos_wr = oos_metrics.get("win_rate", 0)
    max_deg = gate_cfg.get("max_win_rate_degradation", 0.12)
    if train_wr > 0 and train_wr - oos_wr > max_deg:
        passed = False
        reasons.append(f"win_rate_degradation={train_wr - oos_wr:.4f} > {max_deg}")

    if passed:
        reasons.append("all_checks_passed")

    return OOSVerdict(
        passed=passed,
        reasons=reasons,
        metrics=oos_metrics,
        train_metrics=train_metrics,
    )
