"""Backtest Wyckoff failed break — SL at wick extreme, fixed RR."""

from __future__ import annotations

import numpy as np
import pandas as pd

from systemtrain.backtest.engine import BacktestResult, Trade
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig, RiskManager
from systemtrain.strategy.wyckoff import WyckoffConfig, detect_wyckoff_signals


class WyckoffEngine:
    """SL = wick extreme + buffer; entry at signal close or next bar open."""

    def __init__(
        self,
        risk_config: RiskConfig,
        wyckoff_config: WyckoffConfig | None = None,
        initial_equity: float = 10000.0,
        spread_pips: float = 0.5,
        slippage_pips: float = 0.3,
        pip_size: float = 0.0001,
    ):
        self.risk_config = risk_config
        self.wyckoff_config = wyckoff_config or WyckoffConfig()
        self.initial_equity = initial_equity
        self.spread = spread_pips * pip_size
        self.slippage = slippage_pips * pip_size
        self.rr = self.wyckoff_config.rr
        self.pip_size = pip_size

    def run(self, df: pd.DataFrame) -> BacktestResult:
        cfg = self.wyckoff_config
        signals = detect_wyckoff_signals(df, cfg)
        if not signals:
            return BacktestResult()

        entry_map: dict[int, list] = {}
        for sig in signals:
            entry_map.setdefault(sig.entry_bar, []).append(sig)

        highs = df["high"].values
        lows = df["low"].values
        opens = df["open"].values
        closes = df["close"].values
        index = df.index
        n = len(df)

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

                if cfg.entry_delay_bars > 0:
                    raw_entry = opens[i]
                else:
                    raw_entry = closes[i]

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
            if low <= sl_price and high >= tp_price:
                return sl_price, "sl"
            if low <= sl_price:
                return sl_price - slip, "sl"
            if high >= tp_price:
                return tp_price - slip, "tp"
        else:
            if high >= sl_price and low <= tp_price:
                return sl_price, "sl"
            if high >= sl_price:
                return sl_price + slip, "sl"
            if low <= tp_price:
                return tp_price + slip, "tp"
        return None, ""

    def _calc_pnl(self, trade: Trade) -> float:
        if trade.exit_price is None:
            return 0.0
        if trade.direction == 1:
            return (trade.exit_price - trade.entry_price) * trade.size
        return (trade.entry_price - trade.exit_price) * trade.size
