from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    sl_pct: float = 0.02
    min_rr: float = 2.0
    max_drawdown: float = 0.25
    max_consecutive_losses: int = 8
    max_concurrent_positions: int = 1


class RiskManager:
    """Enforces fixed fractional risk — strategies cannot override SL% or min RR."""

    def __init__(self, config: RiskConfig, initial_equity: float):
        self.config = config
        self.initial_equity = initial_equity
        self.equity = initial_equity
        self.peak_equity = initial_equity
        self.consecutive_losses = 0
        self.halted = False
        self.halt_reason = ""

    def update_equity(self, pnl: float) -> None:
        self.equity += pnl
        self.peak_equity = max(self.peak_equity, self.equity)
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        self._check_halt()

    def _check_halt(self) -> None:
        dd = self.current_drawdown()
        if dd >= self.config.max_drawdown:
            self.halted = True
            self.halt_reason = f"max_drawdown {dd:.2%}"
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            self.halted = True
            self.halt_reason = f"consecutive_losses {self.consecutive_losses}"
        if self.equity <= self.initial_equity * 0.5:
            self.halted = True
            self.halt_reason = "account_below_50pct"

    def current_drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 1.0
        return (self.peak_equity - self.equity) / self.peak_equity

    def can_open_trade(self, open_positions: int) -> bool:
        if self.halted:
            return False
        if open_positions >= self.config.max_concurrent_positions:
            return False
        return True

    def compute_levels(
        self,
        direction: int,
        entry_price: float,
        sl_distance: float,
    ) -> tuple[float, float, float]:
        """Return (position_size_lots_units, sl_price, tp_price). Risk = sl_pct * equity."""
        if sl_distance <= 0:
            return 0.0, 0.0, 0.0
        risk_amount = self.equity * self.config.sl_pct
        position_size = risk_amount / sl_distance
        tp_distance = sl_distance * self.config.min_rr
        if direction == 1:
            sl_price = entry_price - sl_distance
            tp_price = entry_price + tp_distance
        else:
            sl_price = entry_price + sl_distance
            tp_price = entry_price - tp_distance
        return position_size, sl_price, tp_price
