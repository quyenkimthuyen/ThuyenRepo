from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np


def compute_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy_pips": 0.0,
            "total_pips": 0.0,
            "max_drawdown_pips": 0.0,
            "avg_bars_held": 0.0,
            "by_setup": {},
            "by_month": {},
        }

    pnls = [float(t["pnl_pips"]) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    max_dd = float(dd.max()) if len(dd) else 0.0

    by_setup: dict[str, dict[str, Any]] = defaultdict(lambda: {"trades": 0, "wins": 0, "pnl": 0.0})
    by_month: dict[str, dict[str, Any]] = defaultdict(lambda: {"trades": 0, "pnl": 0.0})
    for t in trades:
        sid = t.get("setup_id") or "unknown"
        by_setup[sid]["trades"] += 1
        by_setup[sid]["pnl"] += float(t["pnl_pips"])
        if t.get("win"):
            by_setup[sid]["wins"] += 1
        month = str(t.get("entry_time", ""))[:7]
        by_month[month]["trades"] += 1
        by_month[month]["pnl"] += float(t["pnl_pips"])

    setup_stats = {}
    for sid, s in by_setup.items():
        setup_stats[sid] = {
            "trades": s["trades"],
            "win_rate": round(s["wins"] / s["trades"], 3) if s["trades"] else 0,
            "total_pips": round(s["pnl"], 1),
            "expectancy_pips": round(s["pnl"] / s["trades"], 2) if s["trades"] else 0,
        }

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades), 3),
        "profit_factor": round(pf, 2),
        "expectancy_pips": round(float(np.mean(pnls)), 2),
        "total_pips": round(float(np.sum(pnls)), 1),
        "max_drawdown_pips": round(max_dd, 1),
        "avg_bars_held": round(float(np.mean([t.get("bars_held", 0) for t in trades])), 1),
        "by_setup": setup_stats,
        "by_month": {k: {"trades": v["trades"], "pnl": round(v["pnl"], 1)} for k, v in sorted(by_month.items())},
    }


def monte_carlo_pf(trades: list[dict[str, Any]], *, iterations: int = 1000) -> dict[str, float]:
    if len(trades) < 2:
        return {"pf_p5": 0.0, "pf_p50": 0.0, "pf_p95": 0.0, "dd_p95": 0.0}

    pnls = np.array([float(t["pnl_pips"]) for t in trades])
    rng = np.random.default_rng(42)
    pfs: list[float] = []
    dds: list[float] = []
    for _ in range(iterations):
        sample = rng.choice(pnls, size=len(pnls), replace=True)
        wins = sample[sample > 0]
        losses = sample[sample <= 0]
        gp = wins.sum() if len(wins) else 0
        gl = abs(losses.sum()) if len(losses) else 0
        pfs.append(gp / gl if gl > 0 else (999.0 if gp > 0 else 0))
        eq = np.cumsum(sample)
        peak = np.maximum.accumulate(eq)
        dds.append(float((peak - eq).max()))

    return {
        "pf_p5": round(float(np.percentile(pfs, 5)), 2),
        "pf_p50": round(float(np.percentile(pfs, 50)), 2),
        "pf_p95": round(float(np.percentile(pfs, 95)), 2),
        "dd_p95": round(float(np.percentile(dds, 95)), 1),
    }
