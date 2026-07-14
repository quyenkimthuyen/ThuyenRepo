"""Simulate SL/TP trades from RSI zone entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd


@dataclass
class TradeConfig:
    sl_mode: Literal["fixed", "atr"] = "fixed"
    stop_loss_pips: float = 20.0
    stop_loss_atr_mult: float = 1.0
    take_profit_mode: Literal["r", "rsi_zone"] = "rsi_zone"
    take_profit_r: float = 2.0
    max_bars: int = 48
    spread_pips: float = 1.0


def _sl_pips(df: pd.DataFrame, entry_i: int, cfg: TradeConfig) -> float:
    if cfg.sl_mode == "atr":
        atr = float(df.iloc[entry_i].get("atr14", np.nan))
        if np.isnan(atr) or atr <= 0:
            return cfg.stop_loss_pips
        return atr * 10_000 * cfg.stop_loss_atr_mult
    return cfg.stop_loss_pips


def _bar_unix(df: pd.DataFrame, i: int) -> int:
    row = df.iloc[i]
    if hasattr(row.name, "timestamp"):
        return int(row.name.timestamp())
    return int(row["timestamp"] // 1000)


def _rsi_zone_tp_hit(row: pd.Series, direction: Literal["long", "short"]) -> bool:
    rsi_value = float(row.get("rsi14_h4", np.nan))
    if np.isnan(rsi_value):
        return False
    if direction == "long":
        return rsi_value >= 68.0
    return rsi_value <= 32.0


def _pnl_pips(entry: float, exit_price: float, direction: Literal["long", "short"], spread: float) -> float:
    if direction == "long":
        return (exit_price - entry - spread) * 10_000
    return (entry - exit_price - spread) * 10_000


def simulate_trade(
    df: pd.DataFrame,
    entry_i: int,
    direction: Literal["long", "short"],
    cfg: TradeConfig,
) -> dict[str, Any]:
    """Bar-by-bar SL/TP simulation from entry close."""
    if entry_i >= len(df) - 1:
        return {
            "result": "skip", "r_multiple": 0.0, "pnl_pips": 0.0, "bars_held": 0,
            "exit_reason": "skip", "sl_pips": 0.0, "direction": direction,
            "entry_time": _bar_unix(df, entry_i), "exit_time": _bar_unix(df, entry_i),
            "entry_price": 0.0, "exit_price": 0.0, "sl_price": 0.0, "tp_price": 0.0,
        }

    entry = float(df.iloc[entry_i]["close"])
    sl_pips = _sl_pips(df, entry_i, cfg)
    sl_dist = sl_pips / 10_000
    tp_dist = sl_dist * cfg.take_profit_r
    spread = cfg.spread_pips / 10_000

    if direction == "long":
        sl = entry - sl_dist
        tp = entry + tp_dist
    else:
        sl = entry + sl_dist
        tp = entry - tp_dist

    end = min(len(df), entry_i + 1 + cfg.max_bars)
    for j in range(entry_i + 1, end):
        row = df.iloc[j]
        high, low = float(row["high"]), float(row["low"])
        if direction == "long":
            hit_sl = low <= sl
            hit_price_tp = high >= tp
        else:
            hit_sl = high >= sl
            hit_price_tp = low <= tp

        hit_tp = _rsi_zone_tp_hit(row, direction) if cfg.take_profit_mode == "rsi_zone" else hit_price_tp

        if hit_sl and hit_tp:
            return _trade_result(
                "loss", -1.0, -sl_pips, sl_pips, j - entry_i, "both_same_bar",
                df, entry_i, j, entry, sl, tp, direction,
            )
        if hit_sl:
            return _trade_result(
                "loss", -1.0, -sl_pips, sl_pips, j - entry_i, "sl",
                df, entry_i, j, entry, sl, tp, direction, exit_price=sl,
            )
        if hit_tp:
            exit_price = float(row["close"]) if cfg.take_profit_mode == "rsi_zone" else tp
            win_pips = _pnl_pips(entry, exit_price, direction, spread)
            r_mult = win_pips / sl_pips if sl_pips else 0.0
            outcome = "win" if win_pips > 0 else "loss" if win_pips < 0 else "breakeven"
            return _trade_result(
                outcome, round(r_mult, 2), round(win_pips, 1), sl_pips, j - entry_i,
                "rsi_tp" if cfg.take_profit_mode == "rsi_zone" else "tp",
                df, entry_i, j, entry, sl, exit_price, direction, exit_price=exit_price,
            )

    exit_i = end - 1
    exit_close = float(df.iloc[exit_i]["close"])
    pnl = _pnl_pips(entry, exit_close, direction, spread)
    r_mult = pnl / sl_pips if sl_pips else 0.0
    outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven"
    return _trade_result(
        outcome, round(r_mult, 2), round(pnl, 1), sl_pips, exit_i - entry_i, "timeout",
        df, entry_i, exit_i, entry, sl, tp, direction, exit_price=exit_close,
    )


def _trade_result(
    outcome: str,
    r_mult: float,
    pnl_pips: float,
    sl_pips: float,
    bars: int,
    exit_reason: str,
    df: pd.DataFrame,
    entry_i: int,
    exit_i: int,
    entry: float,
    sl: float,
    tp: float,
    direction: str,
    exit_price: float | None = None,
) -> dict[str, Any]:
    ep = exit_price if exit_price is not None else float(df.iloc[exit_i]["close"])
    return {
        "result": outcome,
        "r_multiple": round(r_mult, 2),
        "pnl_pips": round(pnl_pips, 1),
        "bars_held": bars,
        "exit_reason": exit_reason,
        "sl_pips": round(sl_pips, 1),
        "direction": direction,
        "entry_time": _bar_unix(df, entry_i),
        "exit_time": _bar_unix(df, exit_i),
        "entry_price": round(entry, 5),
        "exit_price": round(ep, 5),
        "sl_price": round(sl, 5),
        "tp_price": round(tp, 5),
    }


def build_trade_history(
    df: pd.DataFrame,
    events: list[dict[str, Any]],
    cfg: TradeConfig,
    *,
    zone: Literal["low", "high", "both"] = "low",
    entry_mode: Literal["touch", "exit"] = "touch",
) -> list[dict[str, Any]]:
    """Detailed trade list for chart overlay."""
    trades: list[dict[str, Any]] = []
    trade_id = 0

    for ev in events:
        if zone != "both" and ev["zone"] != zone:
            continue
        if entry_mode == "exit" and not ev.get("exit_signal"):
            continue

        if entry_mode == "exit":
            entry_i = _find_bar_index(df, ev.get("exit_time"))
        else:
            entry_i = _find_bar_index(df, ev.get("time"))
        if entry_i is None:
            continue

        direction = "long" if ev["zone"] == "low" else "short"
        sim = simulate_trade(df, entry_i, direction, cfg)
        if sim["result"] == "skip":
            continue
        trade_id += 1
        sim["id"] = trade_id
        sim["rsi"] = ev.get("rsi")
        sim["zone"] = ev["zone"]
        trades.append(sim)

    trades.sort(key=lambda t: t["entry_time"])
    for i, t in enumerate(trades, start=1):
        t["id"] = i
    return trades


def backtest_entries(
    df: pd.DataFrame,
    events: list[dict[str, Any]],
    cfg: TradeConfig,
    entry_mode: Literal["touch", "exit"] = "exit",
) -> dict[str, Any]:
    """Run SL/TP backtest on zone events."""
    trades: list[dict[str, Any]] = []

    for ev in events:
        if ev["zone"] not in ("low", "high"):
            continue
        if entry_mode == "exit" and not ev.get("exit_signal"):
            continue

        if entry_mode == "exit":
            entry_i = _find_bar_index(df, ev.get("exit_time"))
        else:
            entry_i = _find_bar_index(df, ev.get("time"))
        if entry_i is None:
            continue

        direction = "long" if ev["zone"] == "low" else "short"
        sim = simulate_trade(df, entry_i, direction, cfg)
        sim["zone"] = ev["zone"]
        sim["entry_mode"] = entry_mode
        sim["time"] = ev.get("exit_time") if entry_mode == "exit" else ev.get("time")
        trades.append(sim)

    return _summarize_trades(trades, cfg)


def _find_bar_index(df: pd.DataFrame, unix_sec: int | None) -> int | None:
    if unix_sec is None:
        return None
    ts = pd.Timestamp(unix_sec, unit="s", tz="UTC")
    loc = df.index.get_indexer([ts], method="nearest")[0]
    if loc < 0:
        return None
    return int(loc)


def _summarize_trades(trades: list[dict[str, Any]], cfg: TradeConfig) -> dict[str, Any]:
    if not trades:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_r": 0.0,
            "expectancy_r": 0.0,
            "total_pips": 0.0,
            "avg_pips": 0.0,
            "config": {
                "sl_mode": cfg.sl_mode,
                "stop_loss_pips": cfg.stop_loss_pips,
                "stop_loss_atr_mult": cfg.stop_loss_atr_mult,
                "take_profit_mode": cfg.take_profit_mode,
                "take_profit_r": cfg.take_profit_r,
                "max_bars": cfg.max_bars,
                "spread_pips": cfg.spread_pips,
            },
        }

    wins = [t for t in trades if t["result"] == "win"]
    losses = [t for t in trades if t["result"] == "loss"]
    r_vals = [t["r_multiple"] for t in trades]
    pnl_vals = [t["pnl_pips"] for t in trades]

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_r": round(float(np.mean(r_vals)), 2),
        "expectancy_r": round(float(np.mean(r_vals)), 2),
        "total_pips": round(float(np.sum(pnl_vals)), 1),
        "avg_pips": round(float(np.mean(pnl_vals)), 1),
        "profit_factor": round(
            abs(sum(t["pnl_pips"] for t in wins)) / abs(sum(t["pnl_pips"] for t in losses))
            if losses and sum(t["pnl_pips"] for t in losses) != 0
            else 0.0,
            2,
        ),
        "config": {
            "sl_mode": cfg.sl_mode,
            "stop_loss_pips": cfg.stop_loss_pips,
            "stop_loss_atr_mult": cfg.stop_loss_atr_mult,
            "take_profit_mode": cfg.take_profit_mode,
            "take_profit_r": cfg.take_profit_r,
            "max_bars": cfg.max_bars,
            "spread_pips": cfg.spread_pips,
        },
    }
