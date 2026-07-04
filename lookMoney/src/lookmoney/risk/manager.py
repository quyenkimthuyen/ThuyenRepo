"""Hard risk rules — cannot be bypassed by strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class RiskState:
    balance: float
    peak_balance: float
    daily_pnl: float = 0.0
    daily_date: Optional[date] = None
    consecutive_losses: int = 0
    open_positions: int = 0
    halted: bool = False
    halt_reason: str = ""
    halt_date: Optional[date] = None


@dataclass
class RiskConfig:
    risk_per_trade: float = 0.01
    max_daily_loss: float = 0.03
    max_drawdown: float = 0.15
    max_open_positions: int = 1
    max_consecutive_losses: int = 5
    min_risk_reward: float = 1.5
    halt_cooldown_days: int = 10

    @classmethod
    def from_dict(cls, d: dict) -> "RiskConfig":
        return cls(
            risk_per_trade=d.get("risk_per_trade", 0.01),
            max_daily_loss=d.get("max_daily_loss", 0.03),
            max_drawdown=d.get("max_drawdown", 0.15),
            max_open_positions=d.get("max_open_positions", 1),
            max_consecutive_losses=d.get("max_consecutive_losses", 5),
            min_risk_reward=d.get("min_risk_reward", 1.5),
            halt_cooldown_days=d.get("halt_cooldown_days", 10),
        )


@dataclass
class RiskManager:
    config: RiskConfig
    state: RiskState

    def reset_day(self, day: date) -> None:
        if self.state.daily_date != day:
            self.state.daily_date = day
            self.state.daily_pnl = 0.0

    def current_drawdown(self) -> float:
        if self.state.peak_balance <= 0:
            return 0.0
        return (self.state.peak_balance - self.state.balance) / self.state.peak_balance

    def maybe_resume(self, day: date) -> None:
        if not self.state.halted or self.state.halt_date is None:
            return
        if self.state.halt_reason == "max_drawdown":
            return
        elapsed = (day - self.state.halt_date).days
        if elapsed >= self.config.halt_cooldown_days:
            self.state.halted = False
            self.state.halt_reason = ""
            self.state.halt_date = None
            self.state.consecutive_losses = 0

    def can_open_trade(
        self,
        day: date,
        entry: float,
        stop_loss: float,
        take_profit: float,
        side: str,
    ) -> tuple[bool, str]:
        if self.state.halted:
            return False, self.state.halt_reason or "trading_halted"

        self.reset_day(day)

        if self.state.open_positions >= self.config.max_open_positions:
            return False, "max_open_positions"

        if self.state.daily_pnl <= -self.config.max_daily_loss * self.state.balance:
            self._halt("daily_loss_limit")
            return False, "daily_loss_limit"

        if self.current_drawdown() >= self.config.max_drawdown:
            self._halt("max_drawdown")
            return False, "max_drawdown"

        if self.state.consecutive_losses >= self.config.max_consecutive_losses:
            self._halt("consecutive_losses")
            return False, "consecutive_losses"

        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        if risk <= 0:
            return False, "invalid_stop"
        if reward / risk < self.config.min_risk_reward:
            return False, "risk_reward_too_low"

        return True, "ok"

    def position_size_lots(
        self,
        entry: float,
        stop_loss: float,
        pip_value_per_lot: float = 10.0,
        pip_size: float = 0.0001,
    ) -> float:
        risk_amount = self.state.balance * self.config.risk_per_trade
        sl_pips = abs(entry - stop_loss) / pip_size
        if sl_pips <= 0:
            return 0.0
        lots = risk_amount / (sl_pips * pip_value_per_lot)
        return max(0.01, round(lots, 2))

    def register_open(self) -> None:
        self.state.open_positions += 1

    def register_close(self, pnl: float, day: date) -> None:
        self.reset_day(day)
        self.state.open_positions = max(0, self.state.open_positions - 1)
        self.state.balance += pnl
        self.state.daily_pnl += pnl
        self.state.peak_balance = max(self.state.peak_balance, self.state.balance)

        if pnl < 0:
            self.state.consecutive_losses += 1
        else:
            self.state.consecutive_losses = 0

        if self.current_drawdown() >= self.config.max_drawdown:
            self._halt("max_drawdown")

    def _halt(self, reason: str) -> None:
        self.state.halted = True
        self.state.halt_reason = reason
        self.state.halt_date = self.state.daily_date
