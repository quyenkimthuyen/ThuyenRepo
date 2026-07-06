from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from systemtrain.backtest.signal_engine import SignalEngine
from systemtrain.backtest.wyckoff_engine import WyckoffEngine
from systemtrain.backtest.rsi_div_engine import RsiDivEngine
from systemtrain.config import Config
from systemtrain.live.data_feed import load_live_buffer
from systemtrain.live.paper_account import PaperSessionState, PaperTrade, StrategyPaperState, utc_now_iso
from systemtrain.live.store import append_journal, load_session, save_session, trade_event
from systemtrain.orchestrator.rolling_production import build_engines_from_state, load_state_for_year
from systemtrain.strategy.rsi_divergence import detect_rsi_divergence_signals
from systemtrain.strategy.wyckoff import detect_wyckoff_signals


def _timestamp_iso(value: Any) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat()


def _timestamp(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _signal_key(strategy: str, entry_time: pd.Timestamp, direction: int) -> str:
    return f"{strategy}|{_timestamp_iso(entry_time)}|{direction}"


def _detect_signals(engine: Any, df: pd.DataFrame) -> list:
    if isinstance(engine, SignalEngine):
        return engine.detect_fn(df, engine.strategy_config)
    if isinstance(engine, WyckoffEngine):
        return detect_wyckoff_signals(df, engine.wyckoff_config)
    if isinstance(engine, RsiDivEngine):
        return detect_rsi_divergence_signals(df, engine.div_config)
    return []


def _engine_rr(engine: Any) -> float:
    return float(getattr(engine, "rr", getattr(engine.risk_config, "min_rr", 2.0)))


def _entry_delay(engine: Any) -> int:
    if isinstance(engine, SignalEngine):
        return int(getattr(engine.strategy_config, "entry_delay_bars", engine.entry_delay))
    if isinstance(engine, WyckoffEngine):
        return int(getattr(engine.wyckoff_config, "entry_delay_bars", 0))
    if isinstance(engine, RsiDivEngine):
        return int(getattr(engine.div_config, "entry_delay_bars", 0))
    return 0


def _calc_pnl(trade: PaperTrade) -> float:
    if trade.exit_price is None:
        return 0.0
    if trade.direction == 1:
        return (trade.exit_price - trade.entry_price) * trade.size
    return (trade.entry_price - trade.exit_price) * trade.size


def _check_exit(engine: Any, trade: PaperTrade, high: float, low: float) -> tuple[float | None, str]:
    return engine._check_exit(trade.direction, trade.sl_price, trade.tp_price, high, low)


def _close_open_trade(
    strategy_state: StrategyPaperState,
    engine: Any,
    df: pd.DataFrame,
) -> dict[str, Any] | None:
    trade = strategy_state.open_trade
    if trade is None:
        return None

    last_processed = _timestamp(strategy_state.last_processed_bar)
    entry_time = _timestamp(trade.entry_time)
    start = last_processed or entry_time
    if start is None:
        return None

    for ts, row in df[df.index > start].iterrows():
        exit_price, result = _check_exit(engine, trade, float(row["high"]), float(row["low"]))
        if exit_price is None:
            continue
        trade.exit_time = _timestamp_iso(ts)
        trade.exit_price = float(exit_price)
        trade.result = result
        trade.pnl = _calc_pnl(trade)
        strategy_state.equity += trade.pnl
        strategy_state.closed_trades.append(trade)
        strategy_state.open_trade = None
        event = trade_event("close", trade, {"updated_at": utc_now_iso()})
        append_journal(event)
        return event
    return None


def _open_new_trade(
    strategy: str,
    strategy_state: StrategyPaperState,
    engine: Any,
    df: pd.DataFrame,
) -> dict[str, Any] | None:
    if strategy_state.open_trade is not None:
        return None

    last_processed = _timestamp(strategy_state.last_processed_bar)
    if last_processed is None:
        strategy_state.last_processed_bar = _timestamp_iso(df.index[-1])
        strategy_state.status = "initialized"
        return None

    signals = _detect_signals(engine, df)
    if not signals:
        strategy_state.latest_signal = None
        strategy_state.status = "no_signal"
        return None

    half_spread = float(getattr(engine, "spread", 0.0)) / 2.0
    slip = float(getattr(engine, "slippage", 0.0))
    pip_size = float(getattr(engine, "pip_size", 0.0001))
    delay = _entry_delay(engine)
    rr = _engine_rr(engine)

    for sig in signals:
        if sig.entry_bar >= len(df):
            continue
        entry_time = df.index[sig.entry_bar]
        if entry_time <= last_processed:
            continue
        key = _signal_key(strategy, entry_time, sig.direction)
        if key == strategy_state.last_signal_key:
            continue

        raw_entry = float(df.iloc[sig.entry_bar]["open" if delay > 0 else "close"])
        if sig.direction == 1:
            entry = raw_entry + half_spread + slip
            sl_distance = entry - float(sig.sl_price)
        else:
            entry = raw_entry - half_spread - slip
            sl_distance = float(sig.sl_price) - entry
        if sl_distance <= pip_size:
            strategy_state.status = "invalid_signal"
            continue

        risk_amount = strategy_state.equity * float(engine.risk_config.sl_pct)
        size = risk_amount / sl_distance
        tp_distance = sl_distance * rr
        tp_price = entry + tp_distance if sig.direction == 1 else entry - tp_distance
        trade = PaperTrade(
            strategy=strategy,
            direction=int(sig.direction),
            entry_time=_timestamp_iso(entry_time),
            entry_price=float(entry),
            sl_price=float(sig.sl_price),
            tp_price=float(tp_price),
            size=float(size),
            signal_key=key,
        )
        strategy_state.open_trade = trade
        strategy_state.last_signal_key = key
        strategy_state.latest_signal = {
            "time": trade.entry_time,
            "direction": "LONG" if trade.direction == 1 else "SHORT",
            "entry": trade.entry_price,
            "sl": trade.sl_price,
            "tp": trade.tp_price,
            "tag": getattr(sig, "tag", ""),
        }
        strategy_state.status = "open_trade"
        event = trade_event("open", trade, {"updated_at": utc_now_iso()})
        append_journal(event)
        return event

    strategy_state.status = "no_new_signal"
    return None


def run_paper_once(
    *,
    trade_year: int,
    strategies: list[str],
    equity: float = 1000.0,
    refresh_data: bool = False,
    warmup_days: int = 90,
) -> dict[str, Any]:
    config = Config.load()
    state = load_state_for_year(trade_year)
    if state is None:
        raise ValueError(f"Không tìm thấy optimized config cho năm {trade_year}")

    df = load_live_buffer(refresh=refresh_data, warmup_days=warmup_days, config=config)
    if df.empty:
        raise ValueError("Không có dữ liệu giá để chạy paper live")

    session = load_session()
    session.trade_year = trade_year
    session.updated_at = datetime.now(timezone.utc).isoformat()
    session.latest_bar = _timestamp_iso(df.index[-1])

    engine_map = dict(build_engines_from_state(state, config, equity))
    events: list[dict[str, Any]] = []
    for strategy in strategies:
        engine = engine_map[strategy]
        strategy_state = session.ensure_strategy(strategy, equity)
        close_event = _close_open_trade(strategy_state, engine, df)
        if close_event:
            events.append(close_event)
        open_event = _open_new_trade(strategy, strategy_state, engine, df)
        if open_event:
            events.append(open_event)
        strategy_state.last_processed_bar = session.latest_bar

    save_session(session)
    return {
        "session": session.to_dict(),
        "events": events,
        "latest_bar": session.latest_bar,
        "bars": len(df),
    }

