from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .analyzer import load_strategy
from .config import PIP
from .data_service import load_candles, load_splits, slice_period
from .indicators import add_indicators


def _cost_price() -> float:
    cfg = load_splits()["backtest"]
    return (cfg["spread_pips"] + cfg["slippage_pips"]) * PIP


def _row_feature(row: pd.Series, feature: str) -> float:
    if feature == "dist_ema50_abs":
        return abs(float(row.get("dist_ema50_pips", 0)))
    if feature == "dist_ema50_pips":
        return float(row.get("dist_ema50_pips", 0))
    return float(row.get(feature, 0))


def _passes_exclusions(row: pd.Series, exclusions: list[dict[str, Any]]) -> bool:
    for ex in exclusions:
        val = _row_feature(row, ex["feature"])
        op = ex.get("op", ">")
        limit = float(ex["value"])
        if op == ">" and val > limit:
            return False
        if op == ">=" and val >= limit:
            return False
        if op == "<" and val < limit:
            return False
        if op == "<=" and val <= limit:
            return False
    return True


def _match_rule(row: pd.Series, direction: str, rules: dict[str, Any]) -> bool:
    r = rules.get(direction, {})
    if not r.get("enabled", True):
        return False

    rsi = float(row["rsi14"])
    if not (r.get("rsi_min", 0) <= rsi <= r.get("rsi_max", 100)):
        return False
    if r.get("trend_up") is not None and bool(row["trend_up"]) != bool(r["trend_up"]):
        return False
    if r.get("close_above_ema50") is not None:
        if bool(row["close_above_ema50"]) != bool(r["close_above_ema50"]):
            return False
    if r.get("close_above_ema200") is not None:
        if bool(row["close_above_ema200"]) != bool(r["close_above_ema200"]):
            return False

    max_dist = r.get("max_dist_ema50_pips")
    if max_dist is not None:
        if abs(float(row.get("dist_ema50_pips", 0))) > float(max_dist):
            return False

    if not _passes_exclusions(row, r.get("exclude", [])):
        return False
    return True


def _risk_for_direction(strategy: dict[str, Any], direction: str) -> tuple[float, float]:
    risk = strategy.get("risk", {})
    block = risk.get(direction) or risk.get("default") or {}
    sl_mult = float(block.get("sl_atr_mult", 1.0))
    target_rr = float(block.get("target_rr", block.get("tp_atr_mult", 2.0) / max(sl_mult, 1e-9)))
    if "tp_atr_mult" in block and "target_rr" not in block:
        tp_mult = float(block["tp_atr_mult"])
    else:
        tp_mult = sl_mult * target_rr
    return sl_mult, tp_mult


def _simulate_trade(
    df: pd.DataFrame,
    i: int,
    direction: str,
    sl_mult: float,
    tp_mult: float,
    cost: float,
) -> dict[str, Any] | None:
    row = df.iloc[i]
    atr = float(row["atr14"])
    if np.isnan(atr) or atr <= 0:
        return None

    entry = float(row["close"])
    if direction == "long":
        entry += cost / 2
        sl = entry - sl_mult * atr
        tp = entry + tp_mult * atr
    else:
        entry -= cost / 2
        sl = entry + sl_mult * atr
        tp = entry - tp_mult * atr

    future = df.iloc[i + 1 :]
    for ts, bar in future.iterrows():
        high, low = float(bar["high"]), float(bar["low"])
        if direction == "long":
            hit_sl = low <= sl
            hit_tp = high >= tp
        else:
            hit_sl = high >= sl
            hit_tp = low <= tp

        if hit_sl and hit_tp:
            result = "loss"
            exit_price = sl
            break
        if hit_sl:
            result = "loss"
            exit_price = sl
            break
        if hit_tp:
            result = "win"
            exit_price = tp
            break
    else:
        return None

    if direction == "long":
        pnl = (exit_price - entry) - cost
        risk = entry - sl
    else:
        pnl = (entry - exit_price) - cost
        risk = sl - entry

    rr = abs((exit_price - entry) / risk) if risk else 0
    return {
        "entry_time": df.index[i].isoformat(),
        "exit_time": ts.isoformat(),
        "direction": direction,
        "entry": round(entry, 5),
        "exit": round(exit_price, 5),
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "result": result,
        "pnl_pips": round(pnl / PIP, 1),
        "rr": round(rr, 2),
    }


def _equity_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades:
        return {
            "trades": 0,
            "win_rate": 0,
            "profit_factor": 0,
            "expectancy_pips": 0,
            "max_drawdown_pips": 0,
            "avg_rr": 0,
            "pass": False,
        }

    pnls = np.array([t["pnl_pips"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    gross_profit = wins.sum() if len(wins) else 0
    gross_loss = abs(losses.sum()) if len(losses) else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    max_dd = float(dd.max()) if len(dd) else 0

    criteria = load_splits()["backtest"]["pass_criteria"]
    max_dd_limit = criteria.get("max_drawdown_pips", 250)
    passed = (
        len(trades) >= criteria["min_trades"]
        and pf >= criteria["min_profit_factor"]
        and max_dd <= max_dd_limit
    )

    return {
        "trades": len(trades),
        "win_rate": round(float((pnls > 0).mean()), 3),
        "profit_factor": round(float(pf), 2) if np.isfinite(pf) else 999.0,
        "expectancy_pips": round(float(pnls.mean()), 2),
        "max_drawdown_pips": round(max_dd, 1),
        "avg_rr": round(float(np.mean([t["rr"] for t in trades])), 2),
        "pass": bool(passed),
    }


def run_backtest(period: str = "validation") -> dict[str, Any]:
    strategy = load_strategy()
    if not strategy:
        return {"status": "no_strategy", "message": "Chạy Analyze trước để sinh chiến lược."}

    df = add_indicators(slice_period(load_candles(), period))
    # dist_ema50 for rule matching
    df["dist_ema50_pips"] = (df["close"] - df["ema50"]) / PIP

    rules = strategy["rules"]
    cost = _cost_price()

    trades: list[dict[str, Any]] = []
    cooldown = 0
    for i in range(200, len(df) - 1):
        if i < cooldown:
            continue
        row = df.iloc[i]
        if np.isnan(row["rsi14"]) or np.isnan(row["atr14"]):
            continue

        direction = None
        if _match_rule(row, "long", rules):
            direction = "long"
        elif _match_rule(row, "short", rules):
            direction = "short"
        if not direction:
            continue

        sl_mult, tp_mult = _risk_for_direction(strategy, direction)
        trade = _simulate_trade(df, i, direction, sl_mult, tp_mult, cost)
        if trade:
            trades.append(trade)
            cooldown = i + 5

    metrics = _equity_metrics(trades)
    return {
        "status": "ok",
        "period": period,
        "strategy": strategy.get("name"),
        "risk": strategy.get("risk"),
        "metrics": metrics,
        "trades": trades,
        "trade_count_total": len(trades),
    }
