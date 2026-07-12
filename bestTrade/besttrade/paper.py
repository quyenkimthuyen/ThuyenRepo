"""Paper trading — Pin Bar Elite với params khóa từ BestTrade."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from besttrade.engine import STRATEGY_NAME, _systemtrain_cwd, systemtrain_config
from besttrade.params import active_params, load_forward_test, locked_risk
from besttrade.store import append_journal, load_paper_state, save_paper_state

from systemtrain.backtest.signal_engine import SignalEngine  # noqa: E402
from systemtrain.live.data_feed import load_live_buffer  # noqa: E402
from systemtrain.optimize.rolling_year import build_pin_engine  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts_iso(value: Any) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.isoformat()


def _ts(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _signal_key(entry_time: pd.Timestamp, direction: int) -> str:
    return f"{STRATEGY_NAME}|{_ts_iso(entry_time)}|{direction}"


def _build_engine(equity: float, params: dict[str, Any], sl_pct: float, min_rr: float) -> SignalEngine:
    with _systemtrain_cwd():
        config = systemtrain_config(sl_pct, min_rr)
        return build_pin_engine(params, config, equity)


def _calc_pnl(direction: int, entry: float, exit_price: float, size: float) -> float:
    if direction == 1:
        return (exit_price - entry) * size
    return (entry - exit_price) * size


def _paper_defaults(equity: float) -> dict[str, Any]:
    forward = load_forward_test()
    risk = locked_risk()
    if forward and forward.get("status") == "active":
        risk = forward.get("locked_risk", risk)
    return {
        "strategy": STRATEGY_NAME,
        "initial_equity": equity,
        "equity": equity,
        "open_trade": None,
        "closed_trades": [],
        "last_processed_bar": None,
        "last_signal_key": None,
        "latest_signal": None,
        "status": "idle",
        "updated_at": _utc_now(),
        "locked_params": active_params(sandbox=False),
        "forward_started_at": (forward or {}).get("started_at"),
    }


def run_paper_once(
    *,
    equity: float = 1000.0,
    refresh_data: bool = False,
    warmup_days: int = 120,
    sandbox: bool = False,
    sandbox_params: dict[str, Any] | None = None,
    sl_pct: float | None = None,
    min_rr: float | None = None,
) -> dict[str, Any]:
    """Đánh giá tín hiệu mới nhất trên dữ liệu đóng (giống live, không broker)."""
    risk = locked_risk()
    sl = sl_pct if sl_pct is not None else risk["sl_pct"]
    rr = min_rr if min_rr is not None else risk["min_rr"]
    params = active_params(sandbox, sandbox_params)

    with _systemtrain_cwd():
        config = systemtrain_config(sl, rr)
        df = load_live_buffer(refresh=refresh_data, warmup_days=warmup_days, config=config)

    if df.empty:
        raise ValueError("Không có dữ liệu giá để chạy paper")

    state = load_paper_state()
    if not state or abs(float(state.get("initial_equity", 0)) - equity) > 1e-6:
        state = _paper_defaults(equity)

    state["updated_at"] = _utc_now()
    state["latest_bar"] = _ts_iso(df.index[-1])
    state["locked_params"] = params

    engine = _build_engine(float(state["equity"]), params, sl, rr)
    events: list[dict[str, Any]] = []

    # Close open trade
    open_trade = state.get("open_trade")
    if open_trade:
        last_processed = _ts(state.get("last_processed_bar"))
        start = last_processed or _ts(open_trade["entry_time"])
        for ts, row in df[df.index > (start or df.index[0])].iterrows():
            exit_price, result = engine._check_exit(
                int(open_trade["direction"]),
                float(open_trade["sl_price"]),
                float(open_trade["tp_price"]),
                float(row["high"]),
                float(row["low"]),
            )
            if exit_price is None:
                continue
            pnl = _calc_pnl(
                int(open_trade["direction"]),
                float(open_trade["entry_price"]),
                float(exit_price),
                float(open_trade["size"]),
            )
            closed = {
                **open_trade,
                "exit_time": _ts_iso(ts),
                "exit_price": float(exit_price),
                "result": result,
                "pnl": pnl,
            }
            state["equity"] = float(state["equity"]) + pnl
            state["closed_trades"] = list(state.get("closed_trades", [])) + [closed]
            state["open_trade"] = None
            event = {"event": "close", "trade": closed, "updated_at": _utc_now()}
            append_journal(event)
            events.append(event)
            break

    # Open new trade
    if state.get("open_trade") is None:
        last_processed = _ts(state.get("last_processed_bar"))
        if last_processed is None:
            state["status"] = "initialized"
        else:
            signals = engine.detect_fn(df, engine.strategy_config)
            half_spread = float(engine.spread) / 2.0
            slip = float(engine.slippage)
            pip_size = float(engine.pip_size)
            delay = int(getattr(engine.strategy_config, "entry_delay_bars", engine.entry_delay))
            target_rr = float(engine.rr)

            for sig in signals:
                if sig.entry_bar >= len(df):
                    continue
                entry_time = df.index[sig.entry_bar]
                if entry_time <= last_processed:
                    continue
                key = _signal_key(entry_time, sig.direction)
                if key == state.get("last_signal_key"):
                    continue

                raw_entry = float(df.iloc[sig.entry_bar]["open" if delay > 0 else "close"])
                if sig.direction == 1:
                    entry = raw_entry + half_spread + slip
                    sl_distance = entry - float(sig.sl_price)
                else:
                    entry = raw_entry - half_spread - slip
                    sl_distance = float(sig.sl_price) - entry
                if sl_distance <= pip_size:
                    state["status"] = "invalid_signal"
                    continue

                risk_amount = float(state["equity"]) * sl
                size = risk_amount / sl_distance
                tp_distance = sl_distance * target_rr
                tp_price = entry + tp_distance if sig.direction == 1 else entry - tp_distance
                trade = {
                    "strategy": STRATEGY_NAME,
                    "direction": int(sig.direction),
                    "entry_time": _ts_iso(entry_time),
                    "entry_price": float(entry),
                    "sl_price": float(sig.sl_price),
                    "tp_price": float(tp_price),
                    "size": float(size),
                    "signal_key": key,
                    "tag": getattr(sig, "tag", ""),
                }
                state["open_trade"] = trade
                state["last_signal_key"] = key
                state["latest_signal"] = {
                    "time": trade["entry_time"],
                    "direction": "LONG" if trade["direction"] == 1 else "SHORT",
                    "entry": trade["entry_price"],
                    "sl": trade["sl_price"],
                    "tp": trade["tp_price"],
                    "tag": trade.get("tag", ""),
                }
                state["status"] = "open_trade"
                event = {"event": "open", "trade": trade, "updated_at": _utc_now()}
                append_journal(event)
                events.append(event)
                break
            else:
                if state.get("status") != "invalid_signal":
                    state["status"] = "no_new_signal"

    state["last_processed_bar"] = state["latest_bar"]
    save_paper_state(state)
    return {
        "state": state,
        "events": events,
        "latest_bar": state["latest_bar"],
        "bars": len(df),
        "params": params,
    }
