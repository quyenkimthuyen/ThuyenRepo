"""Persist paper-trading session to disk."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from lookmoney.risk.manager import RiskState


@dataclass
class PaperTradeRecord:
    entry_time: str
    exit_time: str
    side: str
    entry: float
    exit: float
    lots: float
    pnl: float
    r_multiple: float
    exit_reason: str
    reason: str


@dataclass
class OpenTradeState:
    side: str
    entry: float
    stop_loss: float
    take_profit: float
    lots: float
    entry_time: str
    reason: str


@dataclass
class PaperSession:
    balance: float
    peak_balance: float
    daily_pnl: float = 0.0
    daily_date: Optional[str] = None
    consecutive_losses: int = 0
    open_positions: int = 0
    halted: bool = False
    halt_reason: str = ""
    halt_date: Optional[str] = None
    open_trade: Optional[OpenTradeState] = None
    last_processed_bar: Optional[str] = None
    last_run: Optional[str] = None
    trade_count: int = 0

    @classmethod
    def fresh(cls, initial_balance: float) -> PaperSession:
        return cls(balance=initial_balance, peak_balance=initial_balance)

    def to_risk_state(self) -> RiskState:
        daily = date.fromisoformat(self.daily_date) if self.daily_date else None
        halt = date.fromisoformat(self.halt_date) if self.halt_date else None
        return RiskState(
            balance=self.balance,
            peak_balance=self.peak_balance,
            daily_pnl=self.daily_pnl,
            daily_date=daily,
            consecutive_losses=self.consecutive_losses,
            open_positions=self.open_positions,
            halted=self.halted,
            halt_reason=self.halt_reason,
            halt_date=halt,
        )

    def sync_from_risk(self, rs: RiskState) -> None:
        self.balance = rs.balance
        self.peak_balance = rs.peak_balance
        self.daily_pnl = rs.daily_pnl
        self.daily_date = rs.daily_date.isoformat() if rs.daily_date else None
        self.consecutive_losses = rs.consecutive_losses
        self.open_positions = rs.open_positions
        self.halted = rs.halted
        self.halt_reason = rs.halt_reason
        self.halt_date = rs.halt_date.isoformat() if rs.halt_date else None


def load_session(path: Path, initial_balance: float) -> PaperSession:
    if not path.exists():
        return PaperSession.fresh(initial_balance)
    data = json.loads(path.read_text())
    return PaperSession(**data)


def save_session(path: Path, session: PaperSession) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    session.last_run = datetime.utcnow().isoformat() + "+00:00"
    path.write_text(json.dumps(asdict(session), indent=2))


def append_trade_log(path: Path, record: PaperTradeRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "entry_time,exit_time,side,entry,exit,lots,pnl,r_multiple,exit_reason,reason\n"
    )
    if not path.exists():
        path.write_text(header)
    row = (
        f"{record.entry_time},{record.exit_time},{record.side},"
        f"{record.entry},{record.exit},{record.lots},{record.pnl},"
        f"{record.r_multiple},{record.exit_reason},{record.reason}\n"
    )
    with path.open("a") as f:
        f.write(row)


def append_signal_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import csv

    exists = path.exists()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)
