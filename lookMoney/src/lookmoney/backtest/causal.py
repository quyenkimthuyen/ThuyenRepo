"""Causal (no-lookahead) signal generation for out-of-sample testing."""

from __future__ import annotations

from types import ModuleType

import pandas as pd

from lookmoney.sessions import SessionWindow, filter_session_bars, load_sessions
from lookmoney.strategies.eur_usd_h1 import Side, _pip_size
from lookmoney.strategies.registry import resolve_strategy


def generate_signals_causal(
    df: pd.DataFrame,
    config: dict,
    *,
    trade_start: pd.Timestamp,
    trade_end: pd.Timestamp,
    sessions: list[SessionWindow] | None = None,
    strategy_mod: ModuleType | None = None,
) -> pd.DataFrame:
    """
    Signals only inside [trade_start, trade_end], using causal indicators.

    Indicators depend only on past bars. Row i is identical whether computed on
    df[:i+1] or full df, so we precompute once on the truncated OOS window.
    """
    mod = strategy_mod or resolve_strategy(config)
    add_indicators = mod.add_indicators
    long_fn = mod._long
    short_fn = mod._short
    stop_target = mod._stop_target

    sessions = sessions or load_sessions(config)
    session_df = filter_session_bars(df, sessions)
    enriched = add_indicators(df, config)
    s = config["strategy"]
    spread_pips = config.get("backtest", {}).get("spread_pips", 1.2)
    cooldown = s.get("cooldown_days", 1)

    records: list[dict] = []
    last_trade_date = None
    tag = config.get("strategy", {}).get("name", "strategy")

    for i in range(2, len(enriched)):
        ts = enriched.index[i]
        if ts < trade_start or ts > trade_end:
            continue
        if ts not in session_df.index:
            continue

        row = enriched.iloc[i]
        prev = enriched.iloc[i - 1]
        day = row["date"]

        if last_trade_date is not None and (day - last_trade_date).days < cooldown:
            continue

        side = None
        if long_fn(row, prev, s):
            side = Side.BUY
        elif short_fn(row, prev, s):
            side = Side.SELL
        if side is None:
            continue

        levels = stop_target(side, row, s)
        if levels is None:
            continue
        stop, _ = levels

        pip = _pip_size(row["close"])
        half_spread = (spread_pips / 2) * pip
        entry_adj = row["close"] + half_spread if side == Side.BUY else row["close"] - half_spread
        risk = abs(entry_adj - stop)
        if risk <= 0:
            continue
        take_profit = (
            entry_adj + risk * s["min_risk_reward"]
            if side == Side.BUY
            else entry_adj - risk * s["min_risk_reward"]
        )

        records.append(
            {
                "timestamp": ts,
                "side": side.value,
                "entry": entry_adj,
                "stop_loss": stop,
                "take_profit": take_profit,
                "atr": row["atr"],
                "reason": f"{tag}_{side.value}",
            }
        )
        last_trade_date = day

    if not records:
        return pd.DataFrame(
            columns=["timestamp", "side", "entry", "stop_loss", "take_profit", "atr", "reason"]
        )
    return pd.DataFrame(records).set_index("timestamp")
