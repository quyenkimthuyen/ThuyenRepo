from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PaperTrade:
    strategy: str
    direction: int
    entry_time: str
    entry_price: float
    sl_price: float
    tp_price: float
    size: float
    signal_key: str
    exit_time: str | None = None
    exit_price: float | None = None
    pnl: float = 0.0
    result: str = "open"

    @property
    def is_open(self) -> bool:
        return self.exit_time is None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperTrade":
        return cls(**data)


@dataclass
class StrategyPaperState:
    strategy: str
    initial_equity: float
    equity: float
    last_processed_bar: str | None = None
    last_signal_key: str | None = None
    open_trade: PaperTrade | None = None
    closed_trades: list[PaperTrade] = field(default_factory=list)
    setup_signals: list[dict[str, Any]] = field(default_factory=list)
    latest_signal: dict[str, Any] | None = None
    status: str = "idle"

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "initial_equity": self.initial_equity,
            "equity": self.equity,
            "last_processed_bar": self.last_processed_bar,
            "last_signal_key": self.last_signal_key,
            "open_trade": self.open_trade.to_dict() if self.open_trade else None,
            "closed_trades": [trade.to_dict() for trade in self.closed_trades],
            "setup_signals": self.setup_signals,
            "latest_signal": self.latest_signal,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyPaperState":
        open_trade = data.get("open_trade")
        closed = data.get("closed_trades", [])
        return cls(
            strategy=data["strategy"],
            initial_equity=float(data.get("initial_equity", 1000.0)),
            equity=float(data.get("equity", data.get("initial_equity", 1000.0))),
            last_processed_bar=data.get("last_processed_bar"),
            last_signal_key=data.get("last_signal_key"),
            open_trade=PaperTrade.from_dict(open_trade) if open_trade else None,
            closed_trades=[PaperTrade.from_dict(trade) for trade in closed],
            setup_signals=list(data.get("setup_signals", [])),
            latest_signal=data.get("latest_signal"),
            status=data.get("status", "idle"),
        )


@dataclass
class PaperSessionState:
    symbol: str = "EURUSD"
    trade_year: int | None = None
    source: str = "dukascopy-cache"
    updated_at: str | None = None
    latest_bar: str | None = None
    strategies: dict[str, StrategyPaperState] = field(default_factory=dict)

    def ensure_strategy(self, strategy: str, equity: float) -> StrategyPaperState:
        existing = self.strategies.get(strategy)
        if existing is None or abs(existing.initial_equity - equity) > 1e-9:
            existing = StrategyPaperState(strategy=strategy, initial_equity=equity, equity=equity)
            self.strategies[strategy] = existing
        return existing

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "trade_year": self.trade_year,
            "source": self.source,
            "updated_at": self.updated_at,
            "latest_bar": self.latest_bar,
            "strategies": {name: state.to_dict() for name, state in self.strategies.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperSessionState":
        return cls(
            symbol=data.get("symbol", "EURUSD"),
            trade_year=data.get("trade_year"),
            source=data.get("source", "dukascopy-cache"),
            updated_at=data.get("updated_at"),
            latest_bar=data.get("latest_bar"),
            strategies={
                name: StrategyPaperState.from_dict(state)
                for name, state in data.get("strategies", {}).items()
            },
        )

