"""EUR/USD H4 trend pullback with D1 alignment (London + New York)."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import ta

from lookmoney.sessions import SessionWindow, filter_session_bars, load_sessions
from lookmoney.strategies.eur_usd_h1 import (
    Side,
    _entry_filters,
    _pip_size,
    _stop_target,
)


def _d1_trend(df: pd.DataFrame, cfg: dict) -> pd.Series:
    d1 = (
        df.resample("1D")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )
    ema = ta.trend.ema_indicator(d1["close"], window=cfg["strategy"]["d1_ema"])
    trend = pd.Series(0, index=d1.index, dtype=int)
    trend[d1["close"] > ema] = 1
    trend[d1["close"] < ema] = -1
    return trend.reindex(df.index, method="ffill")


def add_indicators(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    s = cfg["strategy"]
    out = df.copy()
    out["ema_entry"] = ta.trend.ema_indicator(out["close"], window=s["ema_entry"])
    out["ema_slow"] = ta.trend.ema_indicator(out["close"], window=s["ema_slow"])
    out["ema_trend"] = ta.trend.ema_indicator(out["close"], window=s["ema_trend"])
    out["adx"] = ta.trend.adx(out["high"], out["low"], out["close"], window=s["adx_period"])
    out["plus_di"] = ta.trend.adx_pos(out["high"], out["low"], out["close"], window=s["adx_period"])
    out["minus_di"] = ta.trend.adx_neg(out["high"], out["low"], out["close"], window=s["adx_period"])
    out["rsi"] = ta.momentum.rsi(out["close"], window=s["rsi_period"])
    out["atr"] = ta.volatility.average_true_range(
        out["high"], out["low"], out["close"], window=s["atr_period"]
    )
    stoch = ta.momentum.StochRSIIndicator(out["close"], window=s["rsi_period"])
    out["stoch_k"] = stoch.stochrsi_k()
    out["stoch_d"] = stoch.stochrsi_d()
    out["swing_low"] = out["low"].rolling(s["swing_lookback"]).min().shift(1)
    out["swing_high"] = out["high"].rolling(s["swing_lookback"]).max().shift(1)
    out["d1_trend"] = _d1_trend(out, cfg)
    out["date"] = out.index.date
    out["di_spread"] = (out["plus_di"] - out["minus_di"]).abs()
    out["body"] = (out["close"] - out["open"]).abs()
    out["ema_entry_slope"] = out["ema_entry"].diff()
    return out


def _long(row: pd.Series, prev: pd.Series, s: dict) -> bool:
    adx_ok = s["adx_min"] <= row["adx"] <= s["adx_max"]
    if s.get("require_stoch_cross", True):
        stoch_ok = (
            prev["stoch_k"] < prev["stoch_d"]
            and row["stoch_k"] > row["stoch_d"]
            and row["stoch_k"] < s["stoch_max_long"]
        )
    else:
        stoch_ok = row["stoch_k"] < s["stoch_max_long"]
    if not (
        row["d1_trend"] == 1
        and row["close"] > row["ema_trend"]
        and row["ema_entry"] > row["ema_slow"]
        and adx_ok
        and row["plus_di"] > row["minus_di"]
        and prev["close"] > prev["ema_entry"]
        and row["low"] <= row["ema_entry"]
        and row["close"] > row["ema_entry"]
        and row["close"] > row["open"]
        and s["rsi_long_min"] <= row["rsi"] <= s["rsi_long_max"]
        and stoch_ok
    ):
        return False
    return _entry_filters(row, prev, Side.BUY, s)


def _short(row: pd.Series, prev: pd.Series, s: dict) -> bool:
    adx_ok = s["adx_min"] <= row["adx"] <= s["adx_max"]
    if s.get("require_stoch_cross", True):
        stoch_ok = (
            prev["stoch_k"] > prev["stoch_d"]
            and row["stoch_k"] < row["stoch_d"]
            and row["stoch_k"] > s["stoch_min_short"]
        )
    else:
        stoch_ok = row["stoch_k"] > s["stoch_min_short"]
    if not (
        row["d1_trend"] == -1
        and row["close"] < row["ema_trend"]
        and row["ema_entry"] < row["ema_slow"]
        and adx_ok
        and row["minus_di"] > row["plus_di"]
        and prev["close"] < prev["ema_entry"]
        and row["high"] >= row["ema_entry"]
        and row["close"] < row["ema_entry"]
        and row["close"] < row["open"]
        and s["rsi_short_min"] <= row["rsi"] <= s["rsi_short_max"]
        and stoch_ok
    ):
        return False
    return _entry_filters(row, prev, Side.SELL, s)


def generate_signals(
    df: pd.DataFrame,
    config: dict,
    *,
    sessions: Optional[list[SessionWindow]] = None,
) -> pd.DataFrame:
    sessions = sessions or load_sessions(config)
    session_df = filter_session_bars(df, sessions)
    enriched = add_indicators(df, config)
    s = config["strategy"]
    records = []
    last_trade_date = None
    cooldown = s.get("cooldown_days", 1)

    for i in range(2, len(enriched)):
        ts = enriched.index[i]
        if ts not in session_df.index:
            continue

        row = enriched.iloc[i]
        prev = enriched.iloc[i - 1]
        day = row["date"]
        if last_trade_date is not None and (day - last_trade_date).days < cooldown:
            continue

        side = None
        if _long(row, prev, s):
            side = Side.BUY
        elif _short(row, prev, s):
            side = Side.SELL
        if side is None:
            continue

        levels = _stop_target(side, row, s)
        if levels is None:
            continue
        stop, take_profit = levels

        spread_pips = config.get("backtest", {}).get("spread_pips", 1.2)
        pip = _pip_size(row["close"])
        half_spread = (spread_pips / 2) * pip
        entry_adj = row["close"] + half_spread if side == Side.BUY else row["close"] - half_spread
        risk = abs(entry_adj - stop)
        if risk <= 0:
            continue
        take_profit = (
            entry_adj + risk * s["min_risk_reward"] if side == Side.BUY else entry_adj - risk * s["min_risk_reward"]
        )

        records.append(
            {
                "timestamp": ts,
                "side": side.value,
                "entry": entry_adj,
                "stop_loss": stop,
                "take_profit": take_profit,
                "atr": row["atr"],
                "reason": f"h4_native_{side.value}",
            }
        )
        last_trade_date = day

    if not records:
        return pd.DataFrame(
            columns=["timestamp", "side", "entry", "stop_loss", "take_profit", "atr", "reason"]
        )
    return pd.DataFrame(records).set_index("timestamp")
