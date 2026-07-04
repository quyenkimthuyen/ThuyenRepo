"""Portfolio backtest — combine up to 3 uncorrelated strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from systemtrain.backtest.engine import BacktestEngine, BacktestResult, Trade
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.risk import RiskConfig, RiskManager
from systemtrain.data.prepared import indicator_column_key
from systemtrain.indicators.library import atr
from systemtrain.strategy.dsl import StrategyGene, generate_signals


@dataclass
class PortfolioResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)
    per_strategy: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    halted: bool = False


class PortfolioEngine:
    """
    Run multiple strategies on shared equity.
    One open position at a time; priority by strategy rank.
    """

    def __init__(self, base_engine: BacktestEngine):
        self.risk_config = base_engine.risk_config
        self.initial_equity = base_engine.initial_equity
        self.spread = base_engine.spread
        self.slippage = base_engine.slippage
        self.spread_pips = base_engine.spread / base_engine.pip_size
        self.slippage_pips = base_engine.slippage / base_engine.pip_size
        self.pip_size = base_engine.pip_size

    def run(self, df: pd.DataFrame, genes: list[StrategyGene]) -> PortfolioResult:
        if not genes:
            return PortfolioResult()

        signals = []
        for rank, gene in enumerate(genes):
            long_s, short_s = generate_signals(df, gene)
            atr_key = indicator_column_key({"name": "atr", "period": gene.atr_period})
            if atr_key in df.columns:
                atr_arr = df[atr_key].values
            else:
                atr_arr = atr(df["high"], df["low"], df["close"], gene.atr_period).values
            signals.append((rank, gene, long_s.values, short_s.values, atr_arr))

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        index = df.index
        n = len(df)

        risk_mgr = RiskManager(self.risk_config, self.initial_equity)
        open_trade: Trade | None = None
        open_rank: int | None = None
        equity = np.full(n, self.initial_equity, dtype=float)
        trades: list[Trade] = []
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
                    open_rank = None

            equity[i] = risk_mgr.equity
            if risk_mgr.halted:
                continue

            if open_trade is None and risk_mgr.can_open_trade(0):
                chosen = None
                for rank, gene, long_a, short_a, atr_a in signals:
                    direction = 0
                    if long_a[i]:
                        direction = 1
                    elif short_a[i]:
                        direction = -1
                    if direction == 0:
                        continue
                    atr_val = atr_a[i]
                    if np.isnan(atr_val) or atr_val <= 0:
                        continue
                    chosen = (rank, gene, direction, atr_val)
                    break  # highest priority strategy wins

                if chosen:
                    _, gene, direction, atr_val = chosen
                    sl_distance = atr_val * gene.sl_atr_mult
                    entry = (
                        closes[i] + half_spread + slip if direction == 1
                        else closes[i] - half_spread - slip
                    )
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
                        open_rank = chosen[0]

        if open_trade and not open_trade.is_closed:
            open_trade.exit_time = index[-1]
            open_trade.exit_price = closes[-1]
            open_trade.result = "eod"
            open_trade.pnl = self._calc_pnl(open_trade)
            risk_mgr.update_equity(open_trade.pnl)
            trades.append(open_trade)
            equity[-1] = risk_mgr.equity

        per_strategy = []
        single_engine = BacktestEngine(
            self.risk_config,
            self.initial_equity,
            spread_pips=self.spread_pips,
            slippage_pips=self.slippage_pips,
            pip_size=self.pip_size,
        )
        for gene in genes:
            r = single_engine.run(df, gene)
            per_strategy.append(compute_metrics(r))

        metrics = compute_metrics(
            BacktestResult(trades=trades, equity_curve=pd.Series(equity, index=index),
                           halted=risk_mgr.halted, halt_reason=risk_mgr.halt_reason)
        )

        return PortfolioResult(
            trades=trades,
            equity_curve=pd.Series(equity, index=index),
            per_strategy=per_strategy,
            metrics=metrics,
            halted=risk_mgr.halted,
        )

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


def select_uncorrelated_genes(
    candidates: list,
    df: pd.DataFrame,
    engine: BacktestEngine,
    n: int = 3,
) -> list:
    """Pick n strategies: low correlation + high walk-forward robustness."""
    if len(candidates) <= n:
        return [c.gene for c in candidates]

    def _pick_score(c) -> float:
        wf = getattr(c, "wf_summary", {}) or {}
        holdout = wf.get("holdout", {})
        s = (
            c.fitness
            + wf.get("avg_win_rate", 0) * 5
            + min(wf.get("avg_profit_factor", 0), 2) * 2
            - wf.get("avg_max_drawdown", 0) * 3
        )
        if holdout:
            s += holdout.get("win_rate", 0) * 4
            s += min(holdout.get("profit_factor", 0), 2) * 2
        return s

    daily_returns: list[pd.Series] = []
    for c in candidates:
        result = engine.run(df, c.gene)
        eq = result.equity_curve
        if len(eq) < 2:
            daily_returns.append(pd.Series(dtype=float))
        else:
            daily_returns.append(eq.resample("1D").last().pct_change().dropna())

    scored = sorted(candidates, key=_pick_score, reverse=True)
    selected_genes: list = [scored[0].gene]
    selected_idx: list[int] = [0]

    for _ in range(n - 1):
        best_j = None
        best_corr = 1.0
        for j, c in enumerate(scored[1:], 1):
            if j in selected_idx:
                continue
            if daily_returns[j].empty:
                continue
            max_corr = 0.0
            for si in selected_idx:
                if daily_returns[si].empty:
                    continue
                aligned = pd.concat([daily_returns[si], daily_returns[j]], axis=1).dropna()
                if len(aligned) < 5:
                    continue
                corr = abs(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
                max_corr = max(max_corr, corr if not np.isnan(corr) else 0)
            if max_corr < best_corr:
                best_corr = max_corr
                best_j = j
        if best_j is None:
            break
        selected_genes.append(scored[best_j].gene)
        selected_idx.append(best_j)

    while len(selected_genes) < n and len(selected_genes) < len(scored):
        for j, c in enumerate(scored):
            if j not in selected_idx:
                selected_genes.append(c.gene)
                selected_idx.append(j)
                break

    return selected_genes[:n]
