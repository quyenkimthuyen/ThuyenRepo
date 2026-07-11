from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .analyzer import load_strategy
from .config import PIP
from .data_service import load_candles, load_splits, slice_periods
from .periods import backtest_label, normalize_backtest_periods
from .indicators import add_indicators, h4_rsi_allows_direction
from .rsi_h4_strategy import detect_entry_at_bar, load_rsi_h4_config
from .strategy_registry import detect_entry as registry_detect_entry, simulate_trade as registry_simulate_trade
from .bar_importance import clear_detection_cache, match_entry_from_inspection
from .labels import load_setups


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


def _match_single_rule(row: pd.Series, rule: dict[str, Any]) -> bool:
    if not rule.get("enabled", True):
        return False

    rsi = float(row.get("rsi14", 50))
    rsi_min = rule.get("rsi_min")
    rsi_max = rule.get("rsi_max")
    if rsi_min is not None and rsi_max is not None:
        if not (float(rsi_min) <= rsi <= float(rsi_max)):
            return False

    h4_req = rule.get("h4_trend_up")
    if h4_req is not None:
        h4_up = bool(row.get("h4_trend_up", row.get("trend_up", False)))
        if h4_up != bool(h4_req):
            return False

    h4_rsi_above = rule.get("h4_rsi_above")
    if h4_rsi_above is not None:
        if not h4_rsi_allows_direction("long", row, threshold=float(h4_rsi_above)):
            return False
    h4_rsi_below = rule.get("h4_rsi_below")
    if h4_rsi_below is not None:
        if not h4_rsi_allows_direction("short", row, threshold=float(h4_rsi_below)):
            return False
    if rule.get("trend_up") is not None and bool(row["trend_up"]) != bool(rule["trend_up"]):
        return False
    if rule.get("close_above_ema50") is not None:
        if bool(row["close_above_ema50"]) != bool(rule["close_above_ema50"]):
            return False
    if rule.get("close_above_ema200") is not None:
        if bool(row["close_above_ema200"]) != bool(rule["close_above_ema200"]):
            return False

    max_dist = rule.get("max_dist_ema50_pips")
    if max_dist is not None:
        if abs(float(row.get("dist_ema50_pips", 0))) > float(max_dist):
            return False

    if not _passes_exclusions(row, rule.get("exclude", [])):
        return False
    return True


def _match_rule(row: pd.Series, direction: str, rules: dict[str, Any]) -> bool:
    return _match_single_rule(row, rules.get(direction, {}))


def _risk_from_reference_setup(setup: dict[str, Any]) -> tuple[float, float] | None:
    features = setup.get("features") or {}
    atr = float(features.get("atr14") or 0)
    if atr <= 0:
        return None
    entry = float(setup["entry_price"])
    sl = float(setup["stop_loss"])
    tp = float(setup["take_profit"])
    sl_mult = abs(entry - sl) / atr
    tp_mult = abs(tp - entry) / atr
    return sl_mult, tp_mult


def _uses_pipeline(strategy: dict[str, Any]) -> bool:
    mode = strategy.get("rule_mode")
    if mode in ("rsi_h4", "rsi_h4_zone", "ema_cross"):
        return False
    if mode == "similarity":
        return True
    return bool(strategy.get("tag_signatures")) or bool(strategy.get("setup_index"))


def _find_entry(
    df: pd.DataFrame,
    i: int,
    row: pd.Series,
    strategy: dict[str, Any],
) -> tuple[str | None, str | None, dict[str, Any] | None]:
    """Return (direction, primary_tag, match_meta) if entry signal found."""
    mode = strategy.get("rule_mode")
    if mode in ("rsi_h4", "rsi_h4_zone", "ema_cross"):
        direction, primary_tag, match_meta = registry_detect_entry(df, i, strategy)
        if not direction:
            return None, None, None
        return direction, primary_tag, match_meta

    if _uses_pipeline(strategy):
        direction, primary_tag, match_meta = match_entry_from_inspection(df, i, strategy)
        if not direction or not match_meta:
            return None, None, None
        return direction, primary_tag, match_meta

    rule_mode = strategy.get("rule_mode", "global")

    if rule_mode == "tag_driven":
        candidates: list[tuple[str, str, dict[str, Any], dict[str, Any]]] = []
        for tag, profile in strategy.get("tag_profiles", {}).items():
            if not profile.get("enabled"):
                continue
            for direction in ("long", "short"):
                dir_rule = profile.get("rules", {}).get(direction, {})
                if _match_single_rule(row, dir_rule):
                    candidates.append((direction, tag, profile, dir_rule))

        if not candidates:
            return None, None, None

        direction, tag, profile, _ = max(
            candidates, key=lambda item: item[2].get("win_rate", 0)
        )
        return direction, tag, profile

    rules = strategy.get("rules", {})
    if _match_single_rule(row, rules.get("long", {})):
        return "long", None, None
    if _match_single_rule(row, rules.get("short", {})):
        return "short", None, None
    return None, None, None


def _risk_for_direction(
    strategy: dict[str, Any],
    direction: str,
    tag: str | None = None,
    match_meta: dict[str, Any] | None = None,
) -> tuple[float, float]:
    if match_meta and match_meta.get("ref_setup"):
        computed = _risk_from_reference_setup(match_meta["ref_setup"])
        if computed:
            return computed

    if match_meta and match_meta.get("risk"):
        risk = match_meta.get("risk", {})
        block = risk.get(direction) or risk.get("default")
        if block:
            sl_mult = float(block.get("sl_atr_mult", 1.0))
            target_rr = float(block.get("target_rr", block.get("tp_atr_mult", 2.0) / max(sl_mult, 1e-9)))
            if "tp_atr_mult" in block and "target_rr" not in block:
                tp_mult = float(block["tp_atr_mult"])
            else:
                tp_mult = sl_mult * target_rr
            return sl_mult, tp_mult

    risk = strategy.get("risk", {})
    block = risk.get(direction) or risk.get("default") or {}
    sl_mult = float(block.get("sl_atr_mult", 1.0))
    target_rr = float(block.get("target_rr", block.get("tp_atr_mult", 2.0) / max(sl_mult, 1e-9)))
    if "tp_atr_mult" in block and "target_rr" not in block:
        tp_mult = float(block["tp_atr_mult"])
    else:
        tp_mult = sl_mult * target_rr
    return sl_mult, tp_mult


def _simulate_trade_rsi_h4(
    df: pd.DataFrame,
    i: int,
    direction: str,
    strategy: dict[str, Any],
    cost: float,
    *,
    setup_type: str | None = None,
    tag: str | None = None,
) -> dict[str, Any] | None:
    cfg = load_rsi_h4_config(strategy)
    bands = cfg["bands"]
    mid = (float(bands["mid"][0]), float(bands["mid"][1]))
    tp_band = (
        (float(bands["high"][0]), float(bands["high"][1]))
        if direction == "long"
        else (float(bands["low"][0]), float(bands["low"][1]))
    )
    risk_cfg = cfg.get("risk") or {}
    sl_atr = float(risk_cfg.get("sl_atr_mult", 1.0))
    sl_mid = bool(risk_cfg.get("sl_on_mid_break", True))
    sl_ema = bool(risk_cfg.get("sl_on_ema_break", True))

    row = df.iloc[i]
    atr = float(row["atr14"])
    if np.isnan(atr) or atr <= 0:
        return None

    entry = float(row["close"])
    if direction == "long":
        entry += cost / 2
        price_sl = entry - sl_atr * atr
    else:
        entry -= cost / 2
        price_sl = entry + sl_atr * atr

    future = df.iloc[i + 1 :]
    exit_price = None
    exit_ts = None
    exit_reason = None

    for ts, bar in future.iterrows():
        rsi_h4 = float(bar["rsi14_h4"])
        high, low = float(bar["high"]), float(bar["low"])
        close = float(bar["close"])

        if direction == "long":
            if rsi_h4 >= tp_band[0]:
                exit_price, exit_ts, exit_reason = close, ts, "rsi_tp"
                break
            if low <= price_sl:
                exit_price, exit_ts, exit_reason = price_sl, ts, "price_sl"
                break
            if sl_mid and rsi_h4 < mid[0]:
                exit_price, exit_ts, exit_reason = close, ts, "rsi_mid_break"
                break
            if sl_ema:
                ema50 = float(bar["ema50"])
                if close < ema50 - 0.5 * atr:
                    exit_price, exit_ts, exit_reason = close, ts, "ema_break"
                    break
        else:
            if rsi_h4 <= tp_band[1]:
                exit_price, exit_ts, exit_reason = close, ts, "rsi_tp"
                break
            if high >= price_sl:
                exit_price, exit_ts, exit_reason = price_sl, ts, "price_sl"
                break
            if sl_mid and rsi_h4 > mid[1]:
                exit_price, exit_ts, exit_reason = close, ts, "rsi_mid_break"
                break
            if sl_ema:
                ema50 = float(bar["ema50"])
                if close > ema50 + 0.5 * atr:
                    exit_price, exit_ts, exit_reason = close, ts, "ema_break"
                    break
    else:
        return None

    if exit_price is None or exit_ts is None:
        return None

    if direction == "long":
        pnl = (exit_price - entry) - cost
        risk = entry - price_sl
    else:
        pnl = (entry - exit_price) - cost
        risk = price_sl - entry

    result = "win" if pnl > 0 else "loss"
    rr = abs((exit_price - entry) / risk) if risk else 0
    trade = {
        "entry_time": df.index[i].isoformat(),
        "exit_time": exit_ts.isoformat(),
        "direction": direction,
        "entry": round(entry, 5),
        "exit": round(exit_price, 5),
        "sl": round(price_sl, 5),
        "tp_band": list(tp_band),
        "result": result,
        "pnl_pips": round(pnl / PIP, 1),
        "rr": round(rr, 2),
        "exit_reason": exit_reason or ("rsi_tp" if result == "win" else "sl"),
    }
    if tag:
        trade["tag"] = tag
    if setup_type:
        trade["setup_type"] = setup_type
    return trade


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


def run_backtest(
    periods: str | list[str] | None = None,
    *,
    period: str | None = None,
    strategy: dict[str, Any] | None = None,
    bar_stride: int = 1,
) -> dict[str, Any]:
    strategy = strategy or load_strategy()
    if not strategy:
        return {"status": "no_strategy", "message": "Chạy Analyze trước để sinh chiến lược."}

    clear_detection_cache()

    period_list = normalize_backtest_periods(periods or period)
    df = add_indicators(slice_periods(load_candles(), period_list))
    # dist_ema50 for rule matching
    df["dist_ema50_pips"] = (df["close"] - df["ema50"]) / PIP

    cost = _cost_price()

    trades: list[dict[str, Any]] = []
    cooldown_until = 0
    entry_cooldown = int(strategy.get("entry_cooldown_bars", 24))
    stride = max(1, int(bar_stride or 1))
    for i in range(200, len(df) - 1, stride):
        if i < cooldown_until:
            continue
        row = df.iloc[i]
        if np.isnan(row["rsi14"]) or np.isnan(row["atr14"]):
            continue

        direction = None
        matched_tag = None
        match_meta = None
        direction, matched_tag, match_meta = _find_entry(df, i, row, strategy)
        if not direction:
            continue

        if strategy.get("rule_mode") in ("rsi_h4", "rsi_h4_zone", "ema_cross"):
            trade = registry_simulate_trade(
                df,
                i,
                direction,
                strategy,
                cost,
                match_meta=match_meta,
            )
        else:
            sl_mult, tp_mult = _risk_for_direction(strategy, direction, matched_tag, match_meta)
            trade = _simulate_trade(df, i, direction, sl_mult, tp_mult, cost)
        if trade:
            if matched_tag and "tag" not in trade:
                trade["tag"] = matched_tag
            if (match_meta or {}).get("setup_type"):
                trade["setup_type"] = match_meta["setup_type"]
            ctx = (match_meta or {}).get("context") or {}
            imp = (match_meta or {}).get("importance") or {}
            if imp.get("score") is not None:
                trade["importance_score"] = imp["score"]
            if ctx.get("detected_tags"):
                trade["detected_tags"] = [item["tag"] for item in ctx["detected_tags"]]
            seq_tags = (match_meta or {}).get("sequence_tags") or ctx.get("sequence_tags") or []
            if seq_tags:
                trade["sequence_tags"] = [item["tag"] for item in seq_tags]
            if ctx.get("similar_setups"):
                best = ctx["similar_setups"][0]
                trade["similarity"] = best.get("similarity")
                trade["ref_setup_id"] = best.get("setup_id")
            trades.append(trade)
            cooldown_until = i + entry_cooldown

    metrics = _equity_metrics(trades)
    period_key = ",".join(period_list) if len(period_list) > 1 else period_list[0]
    return {
        "status": "ok",
        "period": period_key,
        "periods": period_list,
        "period_label": backtest_label(period_list),
        "strategy": strategy.get("name"),
        "train_period": strategy.get("train_period"),
        "train_year": strategy.get("train_year"),
        "rule_mode": strategy.get("rule_mode", "global"),
        "risk": strategy.get("risk"),
        "metrics": metrics,
        "trades": trades,
        "trade_count_total": len(trades),
    }
