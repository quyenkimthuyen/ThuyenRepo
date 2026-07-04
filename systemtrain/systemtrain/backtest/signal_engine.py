"""Generic backtest engine for TradeSignal-based strategies."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from systemtrain.backtest.engine import BacktestResult, Trade
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig, RiskManager
from systemtrain.strategy.signal import TradeSignal


class SignalEngine:
    def __init__(
        self,
        risk_config: RiskConfig,
        detect_fn: Callable,
        strategy_config,
        initial_equity: float = 10000.0,
        spread_pips: float = 0.5,
        slippage_pips: float = 0.3,
        pip_size: float = 0.0001,
        entry_delay: int = 0,
    ):
        self.risk_config = risk_config
        self.detect_fn = detect_fn
        self.strategy_config = strategy_config
        self.initial_equity = initial_equity
        self.spread = spread_pips * pip_size
        self.slippage = slippage_pips * pip_size
        self.rr = getattr(strategy_config, "rr", risk_config.min_rr)
        self.pip_size = pip_size
        self.entry_delay = entry_delay

    def run(self, df: pd.DataFrame) -> BacktestResult:
        cfg = self.strategy_config
        signals: list[TradeSignal] = self.detect_fn(df, cfg)
        if not signals:
            return BacktestResult()

        entry_map: dict[int, list[TradeSignal]] = {}
        for sig in signals:
            entry_map.setdefault(sig.entry_bar, []).append(sig)

        highs = df["high"].values
        lows = df["low"].values
        opens = df["open"].values
        closes = df["close"].values
        index = df.index
        n = len(df)
        delay = getattr(cfg, "entry_delay_bars", self.entry_delay)

        risk_mgr = RiskManager(self.risk_config, self.initial_equity)
        trades: list[Trade] = []
        open_trade: Trade | None = None
        equity = np.full(n, self.initial_equity, dtype=float)
        half_spread = self.spread / 2
        slip = self.slippage

        for i in range(1, n):
            if open_trade and not open_trade.is_closed:
                exit_price, result = self._check_exit(
                    open_trade.direction, open_trade.sl_price, open_trade.tp_price,
                    highs[i], lows[i],
                )
                if exit_price is not None:
                    open_trade.exit_time = index[i]
                    open_trade.exit_price = exit_price
                    open_trade.result = result
                    open_trade.pnl = self._calc_pnl(open_trade)
                    risk_mgr.update_equity(open_trade.pnl)
                    trades.append(open_trade)
                    open_trade = None

            equity[i] = risk_mgr.equity
            if risk_mgr.halted:
                continue

            if open_trade is None and i in entry_map and risk_mgr.can_open_trade(0):
                sig = entry_map[i][0]
                direction = sig.direction
                sl_price = sig.sl_price
                raw_entry = opens[i] if delay > 0 else closes[i]

                if direction == 1:
                    entry = raw_entry + half_spread + slip
                    sl_distance = entry - sl_price
                else:
                    entry = raw_entry - half_spread - slip
                    sl_distance = sl_price - entry

                if sl_distance <= self.pip_size:
                    continue

                risk_amount = risk_mgr.equity * self.risk_config.sl_pct
                size = risk_amount / sl_distance
                tp_distance = sl_distance * self.rr
                tp_price = entry + tp_distance if direction == 1 else entry - tp_distance

                open_trade = Trade(
                    direction=direction,
                    entry_time=index[i],
                    entry_price=entry,
                    sl_price=sl_price,
                    tp_price=tp_price,
                    size=size,
                )

        if open_trade and not open_trade.is_closed:
            open_trade.exit_time = index[-1]
            open_trade.exit_price = closes[-1]
            open_trade.result = "eod"
            open_trade.pnl = self._calc_pnl(open_trade)
            risk_mgr.update_equity(open_trade.pnl)
            trades.append(open_trade)
            equity[-1] = risk_mgr.equity

        result = BacktestResult(
            trades=trades,
            equity_curve=pd.Series(equity, index=index),
            halted=risk_mgr.halted,
            halt_reason=risk_mgr.halt_reason,
        )
        result.metrics = compute_metrics(result)
        return result

    def _check_exit(self, direction, sl_price, tp_price, high, low):
        slip = self.slippage
        if direction == 1:
            if low <= sl_price:
                return (sl_price - slip, "sl")
            if high >= tp_price:
                return (tp_price - slip, "tp")
        else:
            if high >= sl_price:
                return (sl_price + slip, "sl")
            if low <= tp_price:
                return (tp_price + slip, "tp")
        return None, ""

    def _calc_pnl(self, trade: Trade) -> float:
        if trade.exit_price is None:
            return 0.0
        if trade.direction == 1:
            return (trade.exit_price - trade.entry_price) * trade.size
        return (trade.entry_price - trade.exit_price) * trade.size
