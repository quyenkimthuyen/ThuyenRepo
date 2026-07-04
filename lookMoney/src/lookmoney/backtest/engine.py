"""Event-driven backtest with spread, slippage, and risk manager."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from lookmoney.strategies.registry import resolve_strategy


def _signals(df, config, *, causal=False, trade_start=None, trade_end=None):
    mod = resolve_strategy(config)
    if causal:
        from lookmoney.backtest.causal import generate_signals_causal

        return generate_signals_causal(
            df, config, trade_start=trade_start, trade_end=trade_end, strategy_mod=mod
        )
    return mod.generate_signals(df, config)


from lookmoney.backtest.metrics import BacktestMetrics, compute_metrics
from lookmoney.risk.manager import RiskConfig, RiskManager, RiskState


PIP_SIZE = 0.0001


@dataclass
class OpenTrade:
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    lots: float
    entry_time: pd.Timestamp
    risk_per_unit: float
    reason: str


def _apply_exit_price(raw: float, side: str, is_entry: bool, slippage_pips: float) -> float:
    slip = slippage_pips * PIP_SIZE
    if side == "buy":
        return raw + slip if is_entry else raw - slip
    return raw - slip if is_entry else raw + slip


def _bar_hits_trade(bar: pd.Series, trade: OpenTrade) -> tuple[Optional[str], float]:
    """Check SL/TP on bar; conservative: assume stop hits first if both touched."""
    high, low = bar["high"], bar["low"]
    if trade.side == "buy":
        hit_sl = low <= trade.stop_loss
        hit_tp = high >= trade.take_profit
        if hit_sl and hit_tp:
            return "stop_loss", trade.stop_loss
        if hit_sl:
            return "stop_loss", trade.stop_loss
        if hit_tp:
            return "take_profit", trade.take_profit
    else:
        hit_sl = high >= trade.stop_loss
        hit_tp = low <= trade.take_profit
        if hit_sl and hit_tp:
            return "stop_loss", trade.stop_loss
        if hit_sl:
            return "stop_loss", trade.stop_loss
        if hit_tp:
            return "take_profit", trade.take_profit
    return None, 0.0


def _pnl(trade: OpenTrade, exit_price: float, bt: dict) -> float:
    slip_exit = _apply_exit_price(exit_price, trade.side, is_entry=False, slippage_pips=bt["slippage_pips"])
    direction = 1 if trade.side == "buy" else -1
    points = (slip_exit - trade.entry) * direction
    pips = points / PIP_SIZE
    gross = pips * bt["pip_value_per_lot"] * trade.lots
    commission = bt["commission_per_lot"] * trade.lots
    return gross - commission


def run_backtest(
    df: pd.DataFrame,
    config: dict,
    *,
    trade_start: Optional[pd.Timestamp] = None,
    trade_end: Optional[pd.Timestamp] = None,
    causal: bool = False,
) -> tuple[pd.DataFrame, pd.Series, BacktestMetrics]:
    risk_cfg = RiskConfig.from_dict(config["risk"])
    bt = config["backtest"]
    initial = config["risk"]["initial_balance"]

    rm = RiskManager(
        config=risk_cfg,
        state=RiskState(balance=initial, peak_balance=initial),
    )

    if causal:
        if trade_start is None:
            trade_start = df.index[0]
        if trade_end is None:
            trade_end = df.index[-1]
        signals = _signals(
            df, config, causal=True, trade_start=trade_start, trade_end=trade_end
        )
    else:
        signals = _signals(df, config)
        if trade_start is not None or trade_end is not None:
            start = trade_start if trade_start is not None else df.index[0]
            end = trade_end if trade_end is not None else df.index[-1]
            if not signals.empty:
                signals = signals[(signals.index >= start) & (signals.index <= end)]
    trades_log: list[dict] = []
    equity_points: list[tuple[pd.Timestamp, float]] = [(df.index[0], initial)]
    open_trade: Optional[OpenTrade] = None

    for ts, bar in df.iterrows():
        day = ts.date() if hasattr(ts, "date") else date.fromisoformat(str(ts)[:10])
        rm.maybe_resume(day)

        if open_trade is not None:
            exit_reason, exit_raw = _bar_hits_trade(bar, open_trade)
            if exit_reason:
                pnl = _pnl(open_trade, exit_raw, bt)
                planned_risk_cash = rm.state.balance * risk_cfg.risk_per_trade
                r_mult = pnl / planned_risk_cash if planned_risk_cash else 0

                rm.register_close(pnl, day)
                trades_log.append(
                    {
                        "entry_time": open_trade.entry_time,
                        "exit_time": ts,
                        "side": open_trade.side,
                        "entry": open_trade.entry,
                        "exit": exit_raw,
                        "lots": open_trade.lots,
                        "pnl": pnl,
                        "r_multiple": r_mult,
                        "exit_reason": exit_reason,
                        "reason": open_trade.reason,
                    }
                )
                equity_points.append((ts, rm.state.balance))
                open_trade = None

        if trade_start is not None and ts < trade_start:
            continue
        if trade_end is not None and ts > trade_end:
            continue

        if open_trade is None and ts in signals.index and not rm.state.halted:
            sig = signals.loc[ts]
            ok, block = rm.can_open_trade(day, sig["entry"], sig["stop_loss"], sig["take_profit"], sig["side"])
            if not ok:
                continue

            lots = rm.position_size_lots(
                sig["entry"],
                sig["stop_loss"],
                pip_value_per_lot=bt["pip_value_per_lot"],
                pip_size=PIP_SIZE,
            )
            if lots <= 0:
                continue

            entry = _apply_exit_price(sig["entry"], sig["side"], is_entry=True, slippage_pips=bt["slippage_pips"])
            open_trade = OpenTrade(
                side=sig["side"],
                entry=entry,
                stop_loss=sig["stop_loss"],
                take_profit=sig["take_profit"],
                lots=lots,
                entry_time=ts,
                risk_per_unit=abs(entry - sig["stop_loss"]),
                reason=sig["reason"],
            )
            rm.register_open()

    if open_trade is not None:
        last = df.iloc[-1]
        exit_price = float(last["close"])
        pnl = _pnl(open_trade, exit_price, bt)
        planned_risk_cash = rm.state.balance * risk_cfg.risk_per_trade
        r_mult = pnl / planned_risk_cash if planned_risk_cash else 0
        day = df.index[-1].date()
        rm.register_close(pnl, day)
        trades_log.append(
            {
                "entry_time": open_trade.entry_time,
                "exit_time": df.index[-1],
                "side": open_trade.side,
                "entry": open_trade.entry,
                "exit": exit_price,
                "lots": open_trade.lots,
                "pnl": pnl,
                "r_multiple": r_mult,
                "exit_reason": "end_of_data",
                "reason": open_trade.reason,
            }
        )
        equity_points.append((df.index[-1], rm.state.balance))

    trades_df = pd.DataFrame(trades_log)
    equity = pd.Series(
        [e for _, e in equity_points],
        index=pd.DatetimeIndex([t for t, _ in equity_points]),
        name="equity",
    )
    metrics = compute_metrics(trades_df, equity, initial)
    return trades_df, equity, metrics
