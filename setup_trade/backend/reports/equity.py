from __future__ import annotations

from typing import Any

import numpy as np


def equity_curve(trades: list[dict[str, Any]]) -> list[dict[str, float | str]]:
    if not trades:
        return []
    sorted_trades = sorted(trades, key=lambda t: t.get("entry_time", ""))
    cum = 0.0
    curve: list[dict[str, float | str]] = []
    for t in sorted_trades:
        cum += float(t.get("pnl_pips", 0))
        curve.append({"time": t.get("entry_time", ""), "equity_pips": round(cum, 1)})
    return curve


def drawdown_curve(trades: list[dict[str, Any]]) -> list[dict[str, float | str]]:
    eq = equity_curve(trades)
    if not eq:
        return []
    values = np.array([float(p["equity_pips"]) for p in eq])
    peak = np.maximum.accumulate(values)
    dd = peak - values
    return [
        {"time": eq[i]["time"], "drawdown_pips": round(float(dd[i]), 1)}
        for i in range(len(eq))
    ]


def r_multiples(trades: list[dict[str, Any]]) -> list[float]:
    return [float(t.get("r_multiple", 0)) for t in trades if t.get("r_multiple") is not None]
