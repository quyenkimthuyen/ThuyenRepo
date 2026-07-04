from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.backtest.risk import RiskConfig, RiskManager
from systemtrain.data.prepared import indicator_column_key
from systemtrain.strategy.dsl import StrategyGene, generate_signals


@dataclass
class Trade:
    direction: int
    entry_time: pd.Timestamp
    entry_price: float
    sl_price: float
    tp_price: float
    size: float
    exit_time: pd.Timestamp | None = None
    exit_price: float | None = None
    pnl: float = 0.0
    result: str = ""

    @property
    def is_closed(self) -> bool:
        return self.exit_time is not None


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    metrics: dict[str, Any] = field(default_factory=dict)
    halted: bool = False
    halt_reason: str = ""


class BacktestEngine:
    def __init__(
        self,
        risk_config: RiskConfig,
        initial_equity: float = 10000.0,
        spread_pips: float = 1.5,
        slippage_pips: float = 0.5,
        pip_size: float = 0.0001,
    ):
        self.risk_config = risk_config
        self.initial_equity = initial_equity
        self.spread = spread_pips * pip_size
        self.slippage = slippage_pips * pip_size
        self.pip_size = pip_size

    def run(self, df: pd.DataFrame, gene: StrategyGene) -> BacktestResult:
        if len(df) < 50:
            return BacktestResult(metrics={"error": "insufficient_data"})

        long_sig, short_sig = generate_signals(df, gene)
        atr_key = indicator_column_key({"name": "atr", "period": gene.atr_period})
        if atr_key in df.columns:
            atr_arr = df[atr_key].values
        else:
            from systemtrain.indicators.library import atr
            atr_arr = atr(df["high"], df["low"], df["close"], gene.atr_period).values

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        index = df.index
        long_arr = long_sig.values
        short_arr = short_sig.values
        n = len(df)

        risk_mgr = RiskManager(self.risk_config, self.initial_equity)
        trades: list[Trade] = []
        open_trade: Trade | None = None
        equity = np.full(n, self.initial_equity, dtype=float)

        half_spread = self.spread / 2
        slip = self.slippage

        for i in range(1, n):
            if open_trade and not open_trade.is_closed:
                exit_price, result = self._check_exit_np(
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

            if open_trade is None and risk_mgr.can_open_trade(0):
                direction = 0
                if long_arr[i]:
                    direction = 1
                elif short_arr[i]:
                    direction = -1

                if direction != 0:
                    atr_val = atr_arr[i]
                    if np.isnan(atr_val) or atr_val <= 0:
                        continue

                    sl_distance = atr_val * gene.sl_atr_mult
                    entry = closes[i] + half_spread + slip if direction == 1 else closes[i] - half_spread - slip
                    size, sl_price, tp_price = risk_mgr.compute_levels(direction, entry, sl_distance)
                    if size > 0:
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

        equity_curve = pd.Series(equity, index=index)

        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            halted=risk_mgr.halted,
            halt_reason=risk_mgr.halt_reason,
        )

    def _check_exit_np(
        self, direction: int, sl_price: float, tp_price: float, high: float, low: float
    ) -> tuple[float | None, str]:
        slip = self.slippage
        if direction == 1:
            sl_hit = low <= sl_price
            tp_hit = high >= tp_price
            if sl_hit and tp_hit:
                return sl_price, "sl"
            if sl_hit:
                return sl_price - slip, "sl"
            if tp_hit:
                return tp_price - slip, "tp"
        else:
            sl_hit = high >= sl_price
            tp_hit = low <= tp_price
            if sl_hit and tp_hit:
                return sl_price, "sl"
            if sl_hit:
                return sl_price + slip, "sl"
            if tp_hit:
                return tp_price + slip, "tp"
        return None, ""

    def _calc_pnl(self, trade: Trade) -> float:
        if trade.exit_price is None:
            return 0.0
        if trade.direction == 1:
            return (trade.exit_price - trade.entry_price) * trade.size
        return (trade.entry_price - trade.exit_price) * trade.size
