"""Forward test — so sánh paper vs backtest trên cùng khoảng thời gian."""

from __future__ import annotations

from typing import Any

import pandas as pd

from besttrade.engine import STRATEGY_NAME, run_period_backtest
from besttrade.params import load_forward_test


def _ts(value: str) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def forward_trades_from_paper(paper_state: dict[str, Any]) -> list[dict[str, Any]]:
    forward = load_forward_test()
    if not forward or forward.get("status") != "active":
        return list(paper_state.get("closed_trades", []))

    started = _ts(forward["started_at"])
    out = []
    for trade in paper_state.get("closed_trades", []):
        entry = _ts(trade["entry_time"])
        if entry >= started:
            out.append(trade)
    open_trade = paper_state.get("open_trade")
    if open_trade and _ts(open_trade["entry_time"]) >= started:
        out.append({**open_trade, "result": "open", "pnl": 0.0})
    return out


def forward_paper_metrics(paper_state: dict[str, Any]) -> dict[str, Any]:
    forward = load_forward_test()
    if not forward:
        return {"active": False}

    trades = forward_trades_from_paper(paper_state)
    closed = [t for t in trades if t.get("result") != "open"]
    initial = float(forward.get("initial_equity", paper_state.get("initial_equity", 1000.0)))

    if not closed:
        return {
            "active": forward.get("status") == "active",
            "started_at": forward.get("started_at"),
            "trade_count": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "equity": float(paper_state.get("equity", initial)),
        }

    pnls = [float(t.get("pnl", 0)) for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    bal = initial + sum(pnls)

    return {
        "active": forward.get("status") == "active",
        "started_at": forward.get("started_at"),
        "trade_count": len(closed),
        "win_rate": len(wins) / len(closed),
        "profit_factor": gp / gl if gl else 0.0,
        "total_return": (bal - initial) / initial,
        "equity": bal,
        "gross_profit": gp,
        "gross_loss": gl,
    }


def compare_forward_backtest(
    equity: float,
    sl_pct: float,
    min_rr: float,
    paper_state: dict[str, Any],
) -> dict[str, Any]:
    forward = load_forward_test()
    if not forward:
        return {"error": "Chưa bắt đầu forward test"}

    started = _ts(forward["started_at"])
    now = pd.Timestamp.now(tz="UTC")
    params = forward.get("locked_params", {})
    bt = run_period_backtest(started, now, params, equity, sl_pct, min_rr)

    paper_m = forward_paper_metrics(paper_state)
    bt_m = bt.metrics

    return {
        "period": {"start": started.isoformat(), "end": now.isoformat()},
        "locked_params": params,
        "paper": paper_m,
        "backtest": {
            "trade_count": bt_m.get("trade_count", 0),
            "win_rate": bt_m.get("win_rate", 0),
            "profit_factor": bt_m.get("profit_factor", 0),
            "total_return": bt_m.get("total_return", 0),
        },
        "delta_return": paper_m.get("total_return", 0) - bt_m.get("total_return", 0),
        "delta_trades": paper_m.get("trade_count", 0) - bt_m.get("trade_count", 0),
        "strategy": STRATEGY_NAME,
    }
