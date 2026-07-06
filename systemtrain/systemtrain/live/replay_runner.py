"""Replay backtest — chạy từng nến 1H từ thời điểm quá khứ (giống live paper)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from systemtrain.config import Config
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.live.paper_account import PaperTrade, StrategyPaperState, utc_now_iso
from systemtrain.live.signal_runner import (
    _calc_pnl,
    _check_exit,
    _detect_signals,
    _engine_rr,
    _entry_delay,
    _signal_key,
    _timestamp_iso,
)
from systemtrain.optimize.rolling_year import year_bounds
from systemtrain.orchestrator.pipeline import TrainingPipeline
from systemtrain.orchestrator.rolling_production import build_engines_from_state, load_state_for_year


@dataclass
class ReplaySession:
    trade_year: int
    config_year: int
    equity: float
    warmup_days: int
    start_bar: str
    end_bar: str
    cursor_idx: int
    start_idx: int
    end_idx: int
    strategies: dict[str, StrategyPaperState] = field(default_factory=dict)
    journal: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str | None = None

    @property
    def cursor_bar(self) -> str | None:
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_year": self.trade_year,
            "config_year": self.config_year,
            "equity": self.equity,
            "warmup_days": self.warmup_days,
            "start_bar": self.start_bar,
            "end_bar": self.end_bar,
            "cursor_idx": self.cursor_idx,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "strategies": {k: v.to_dict() for k, v in self.strategies.items()},
            "journal": self.journal,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReplaySession":
        return cls(
            trade_year=int(data["trade_year"]),
            config_year=int(data["config_year"]),
            equity=float(data["equity"]),
            warmup_days=int(data.get("warmup_days", 60)),
            start_bar=data["start_bar"],
            end_bar=data["end_bar"],
            cursor_idx=int(data["cursor_idx"]),
            start_idx=int(data["start_idx"]),
            end_idx=int(data["end_idx"]),
            strategies={
                k: StrategyPaperState.from_dict(v)
                for k, v in data.get("strategies", {}).items()
            },
            journal=list(data.get("journal", [])),
            updated_at=data.get("updated_at"),
        )


def _journal_event(event: str, strategy: str, trade: PaperTrade, extra: dict | None = None) -> dict[str, Any]:
    payload = {
        "event": event,
        "strategy": strategy,
        "trade": trade.to_dict(),
        "at_bar": extra.get("at_bar") if extra else None,
        "updated_at": utc_now_iso(),
    }
    if extra:
        payload.update(extra)
    return payload


def load_replay_dataframe(
    trade_year: int,
    start_ts: pd.Timestamp,
    *,
    warmup_days: int = 60,
    end_ts: pd.Timestamp | None = None,
    config: Config | None = None,
) -> pd.DataFrame:
    config = config or Config.load()
    df_1h = to_entry_timeframe(TrainingPipeline(config).load_data(), "1h")
    year_start = pd.Timestamp(year_bounds(trade_year)[0], tz="UTC")
    year_end = pd.Timestamp(year_bounds(trade_year)[1], tz="UTC")
    if end_ts is None:
        end_ts = year_end
    start_ts = pd.Timestamp(start_ts)
    if start_ts.tzinfo is None:
        start_ts = start_ts.tz_localize("UTC")
    else:
        start_ts = start_ts.tz_convert("UTC")
    end_ts = pd.Timestamp(end_ts)
    if end_ts.tzinfo is None:
        end_ts = end_ts.tz_localize("UTC")
    else:
        end_ts = end_ts.tz_convert("UTC")
    buf_start = max(year_start - pd.Timedelta(days=warmup_days), df_1h.index.min())
    buf_end = min(end_ts, year_end, df_1h.index.max())
    return df_1h.loc[buf_start:buf_end].copy()


def _resolve_indices(df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> tuple[int, int]:
    start_ts = pd.Timestamp(start_ts).tz_convert("UTC")
    end_ts = pd.Timestamp(end_ts).tz_convert("UTC")
    start_idx = int(df.index.searchsorted(start_ts, side="left"))
    start_idx = min(max(start_idx, 0), len(df) - 1)
    end_idx = int(df.index.searchsorted(end_ts, side="right")) - 1
    end_idx = min(max(end_idx, start_idx), len(df) - 1)
    return start_idx, end_idx


def init_replay_session(
    *,
    trade_year: int,
    config_year: int,
    strategies: list[str],
    equity: float,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp | None = None,
    warmup_days: int = 60,
) -> tuple[ReplaySession, pd.DataFrame]:
    if load_state_for_year(config_year) is None:
        raise ValueError(f"Không có config optimize cho năm {config_year}")

    df = load_replay_dataframe(trade_year, start_ts, warmup_days=warmup_days, end_ts=end_ts)
    if df.empty:
        raise ValueError("Không có dữ liệu giá cho khoảng replay")

    if end_ts is None:
        end_ts = pd.Timestamp(year_bounds(trade_year)[1], tz="UTC")
    start_idx, end_idx = _resolve_indices(df, start_ts, end_ts)

    session = ReplaySession(
        trade_year=trade_year,
        config_year=config_year,
        equity=equity,
        warmup_days=warmup_days,
        start_bar=_timestamp_iso(df.index[start_idx]),
        end_bar=_timestamp_iso(df.index[end_idx]),
        cursor_idx=start_idx - 1,
        start_idx=start_idx,
        end_idx=end_idx,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    for name in strategies:
        st = StrategyPaperState(strategy=name, initial_equity=equity, equity=equity)
        if start_idx > 0:
            st.last_processed_bar = _timestamp_iso(df.index[start_idx - 1])
        st.status = "ready"
        session.strategies[name] = st
    return session, df


def _try_open_on_bar(
    strategy: str,
    strategy_state: StrategyPaperState,
    engine: Any,
    df: pd.DataFrame,
    bar_idx: int,
) -> dict[str, Any] | None:
    if strategy_state.open_trade is not None:
        return None

    ts = df.index[bar_idx]
    signals = _detect_signals(engine, df.iloc[: bar_idx + 1])
    if not signals:
        return None

    half_spread = float(getattr(engine, "spread", 0.0)) / 2.0
    slip = float(getattr(engine, "slippage", 0.0))
    pip_size = float(getattr(engine, "pip_size", 0.0001))
    delay = _entry_delay(engine)
    rr = _engine_rr(engine)

    for sig in signals:
        if sig.entry_bar != bar_idx:
            continue
        entry_time = df.index[sig.entry_bar]
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
        return _journal_event("open", strategy, trade, {"at_bar": _timestamp_iso(ts)})

    strategy_state.status = "no_new_signal"
    return None


def _try_close_on_bar(
    strategy_state: StrategyPaperState,
    engine: Any,
    df: pd.DataFrame,
    bar_idx: int,
) -> dict[str, Any] | None:
    trade = strategy_state.open_trade
    if trade is None:
        return None

    row = df.iloc[bar_idx]
    ts = df.index[bar_idx]
    exit_price, result = _check_exit(
        engine, trade, float(row["high"]), float(row["low"]),
    )
    if exit_price is None:
        return None

    trade.exit_time = _timestamp_iso(ts)
    trade.exit_price = float(exit_price)
    trade.result = result
    trade.pnl = _calc_pnl(trade)
    strategy_state.equity += trade.pnl
    strategy_state.closed_trades.append(trade)
    strategy_state.open_trade = None
    strategy_state.status = "closed_trade"
    return _journal_event("close", trade.strategy, trade, {"at_bar": _timestamp_iso(ts)})


def process_replay_bar(
    session: ReplaySession,
    engines: dict[str, Any],
    df: pd.DataFrame,
    bar_idx: int,
) -> list[dict[str, Any]]:
    if bar_idx < session.start_idx or bar_idx > session.end_idx:
        return []

    events: list[dict[str, Any]] = []
    ts = df.index[bar_idx]

    for strategy, strategy_state in session.strategies.items():
        engine = engines[strategy]
        close_ev = _try_close_on_bar(strategy_state, engine, df, bar_idx)
        if close_ev:
            events.append(close_ev)
            session.journal.append(close_ev)
        open_ev = _try_open_on_bar(strategy, strategy_state, engine, df, bar_idx)
        if open_ev:
            events.append(open_ev)
            session.journal.append(open_ev)
        strategy_state.last_processed_bar = _timestamp_iso(ts)

    session.cursor_idx = bar_idx
    session.updated_at = datetime.now(timezone.utc).isoformat()
    return events


def step_replay(
    session: ReplaySession,
    engines: dict[str, Any],
    df: pd.DataFrame,
    steps: int = 1,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for _ in range(steps):
        next_idx = session.cursor_idx + 1
        if next_idx > session.end_idx:
            break
        events.extend(process_replay_bar(session, engines, df, next_idx))
    return events


def replay_to_end(
    session: ReplaySession,
    engines: dict[str, Any],
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    remaining = session.end_idx - session.cursor_idx
    return step_replay(session, engines, df, steps=remaining)


def seek_replay(
    session: ReplaySession,
    config_year: int,
    strategies: list[str],
    equity: float,
    df: pd.DataFrame,
    target_idx: int,
    engines: dict[str, Any] | None = None,
) -> tuple[ReplaySession, list[dict[str, Any]]]:
    """Nhảy tới nến target — reset và chạy lại từ đầu (đơn giản, deterministic)."""
    start_ts = pd.Timestamp(session.start_bar)
    end_ts = pd.Timestamp(session.end_bar)
    fresh, _ = init_replay_session(
        trade_year=session.trade_year,
        config_year=config_year,
        strategies=strategies,
        equity=equity,
        start_ts=start_ts,
        end_ts=end_ts,
        warmup_days=session.warmup_days,
    )
    fresh.start_idx = session.start_idx
    fresh.end_idx = session.end_idx
    fresh.cursor_idx = session.start_idx - 1

    if engines is None:
        config = Config.load()
        state = load_state_for_year(config_year)
        engines = dict(build_engines_from_state(state, config, equity))

    target_idx = min(max(target_idx, session.start_idx), session.end_idx)
    steps = target_idx - fresh.cursor_idx
    events = step_replay(fresh, engines, df, steps=steps)
    return fresh, events


def build_replay_engines(session: ReplaySession, equity: float | None = None) -> dict[str, Any]:
    config = Config.load()
    state = load_state_for_year(session.config_year)
    if state is None:
        raise ValueError(f"Không có config cho năm {session.config_year}")
    eq = equity if equity is not None else session.equity
    return dict(build_engines_from_state(state, config, eq))


def cursor_bar_time(session: ReplaySession, df: pd.DataFrame) -> str | None:
    if session.cursor_idx < 0:
        return None
    if session.cursor_idx >= len(df):
        return _timestamp_iso(df.index[-1])
    return _timestamp_iso(df.index[session.cursor_idx])


def visible_replay_df(session: ReplaySession, df: pd.DataFrame) -> pd.DataFrame:
    if session.cursor_idx < 0:
        return df.iloc[: session.start_idx + 1]
    return df.iloc[: session.cursor_idx + 1]
