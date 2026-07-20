"""Broker adapter boundary — live trading stays outside the research core."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class BrokerOrder:
  symbol: str
  side: Literal["BUY", "SELL"]
  volume: float
  sl: float | None = None
  tp: float | None = None
  comment: str = "forexforge"


@dataclass
class BrokerFill:
  order_id: str
  symbol: str
  side: str
  volume: float
  price: float
  status: str


class BrokerAdapter(ABC):
  """Bounded context for Phase 6 live — do not import into miner/WF."""

  @abstractmethod
  def place_market(self, order: BrokerOrder) -> BrokerFill:
    ...

  @abstractmethod
  def cancel(self, order_id: str) -> bool:
    ...

  @abstractmethod
  def positions(self) -> list[dict]:
    ...


class StubBroker(BrokerAdapter):
  """Local stub — records intents, never sends to a real venue."""

  def __init__(self):
    self._orders: list[BrokerFill] = []
    self._n = 0

  def place_market(self, order: BrokerOrder) -> BrokerFill:
    self._n += 1
    fill = BrokerFill(
      order_id=f"stub-{self._n}",
      symbol=order.symbol,
      side=order.side,
      volume=order.volume,
      price=0.0,
      status="ACCEPTED_STUB",
    )
    self._orders.append(fill)
    return fill

  def cancel(self, order_id: str) -> bool:
    return False

  def positions(self) -> list[dict]:
    return []


# Future: MT5Broker / OandaBroker implement BrokerAdapter in separate modules.
