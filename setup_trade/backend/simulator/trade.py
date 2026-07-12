"""Một engine duy nhất cho label outcome, backtest và paper trade."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from backend.simulator.costs import round_trip_cost_price
from backend.strategy.rsi_ema_v1.config import band, load_strategy_config


def simulate_trade(
    df: pd.DataFrame,
    i: int,
    direction: str,
    *,
    strategy_config: dict[str, Any] | None = None,
    setup_id: str | None = None,
) -> dict[str, Any] | None:
    if i >= len(df) - 1:
        return None

    cfg = load_strategy_config(strategy_config)
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
    sl_ema = bool(risk_cfg.get("sl_on_ema_break", False))
    cost = round_trip_cost_price()

    row = df.iloc[i]
    atr_val = float(row["atr14"])
    if np.isnan(atr_val) or atr_val <= 0:
        return None

    entry = float(row["close"])
    if direction == "long":
        entry += cost / 2
        price_sl = entry - sl_atr * atr_val
    else:
        entry -= cost / 2
        price_sl = entry + sl_atr * atr_val

    future = df.iloc[i + 1 :]
    exit_price: float | None = None
    exit_ts: pd.Timestamp | None = None
    exit_reason: str | None = None
    bars_held = 0

    for ts, bar in future.iterrows():
        bars_held += 1
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
                if close < ema50 - 0.5 * atr_val:
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
                if close > ema50 + 0.5 * atr_val:
                    exit_price, exit_ts, exit_reason = close, ts, "ema_break"
                    break
    else:
        return None

    if exit_price is None or exit_ts is None:
        return None

    pnl = (exit_price - entry) if direction == "long" else (entry - exit_price)
    pnl -= cost / 2
    pips = pnl / 0.0001

    return {
        "direction": direction,
        "setup_id": setup_id,
        "entry_time": df.index[i].isoformat(),
        "entry_price": round(entry, 5),
        "exit_time": exit_ts.isoformat(),
        "exit_price": round(exit_price, 5),
        "exit_reason": exit_reason,
        "pnl_pips": round(pips, 1),
        "win": pips > 0,
        "bars_held": bars_held,
        "r_multiple": round(pips / (sl_atr * atr_val / 0.0001), 2) if sl_atr * atr_val > 0 else 0,
    }
