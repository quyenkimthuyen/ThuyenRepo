"""Typed internal API — RunSpec, Report, KB, trades, signals."""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class JobKind(str, Enum):
  BACKTEST = "backtest"
  LEARN = "learn"
  PAPER = "paper"


class CostModel(BaseModel):
  spread_pips: float = 1.0
  slippage_pips: float = 0.3


class InstrumentSpec(BaseModel):
  pair: str = "EUR/USD"
  timeframe: str = "H1"


class RunSpec(BaseModel):
  """Immutable run request shared by backtest / learn / paper."""

  kind: JobKind = JobKind.BACKTEST
  instrument: InstrumentSpec = Field(default_factory=InstrumentSpec)
  cost: CostModel = Field(default_factory=CostModel)
  train_months: int = 3
  use_kb: bool = False
  kb_profile: Optional[str] = None
  kb_epoch: Optional[int | Literal["latest"]] = None
  oos_from: Optional[date] = None
  oos_to: Optional[date] = None
  data_from: Optional[date] = None
  data_to: Optional[date] = None
  holdout_months: int = 0
  risk_pct_per_trade: float = 1.0
  epochs: int = 1
  seed: Optional[int] = 42
  label: Optional[str] = None

  @field_validator("oos_from", "oos_to", "data_from", "data_to", mode="before")
  @classmethod
  def _parse_date(cls, v):
    if v is None or v == "":
      return None
    if isinstance(v, date) and not isinstance(v, datetime):
      return v
    return date.fromisoformat(str(v)[:10])

  def oos_from_str(self) -> str | None:
    return self.oos_from.isoformat() if self.oos_from else None

  def oos_to_str(self) -> str | None:
    return self.oos_to.isoformat() if self.oos_to else None


class TradeRecord(BaseModel):
  entry: str
  exit: str | None = None
  direction: Literal["LONG", "SHORT"]
  entry_px: float | None = None
  exit_px: float | None = None
  sl: float | None = None
  tp: float | None = None
  pnl_pips: float | None = None
  r: float | None = None
  reason: str | None = None


class SignalRecord(BaseModel):
  bar_time: str
  direction: Literal["LONG", "SHORT"]
  entry_px: float | None = None
  sl: float | None = None
  tp: float | None = None
  strategy: str | None = None
  pair: str = "EUR/USD"
  timeframe: str = "H1"


class MetricsPack(BaseModel):
  n_trades: int = 0
  trades_per_week: float = 0.0
  win_rate_pct: float = 0.0
  avg_rr: float = 0.0
  profit_factor: float = 0.0
  total_pips: float = 0.0
  total_r: float = 0.0
  max_drawdown_r: float = 0.0
  max_win_streak: int = 0
  max_loss_streak: int = 0
  risk_of_ruin_pct: float = 0.0


class KbProfile(BaseModel):
  id: str
  name: str | None = None
  trained_from: Optional[date] = None
  trained_to: Optional[date] = None
  epochs: int = 0
  note: str | None = None

  @field_validator("trained_from", "trained_to", mode="before")
  @classmethod
  def _parse_date(cls, v):
    if v is None or v == "":
      return None
    if isinstance(v, date) and not isinstance(v, datetime):
      return v
    return date.fromisoformat(str(v)[:10])


class EpochSnapshot(BaseModel):
  profile_id: str
  epoch: int
  created_at: Optional[datetime] = None
  metrics: dict[str, Any] = Field(default_factory=dict)


class LeakageCheck(BaseModel):
  ok: bool
  message: str
  profile_id: str | None = None
  trained_to: Optional[date] = None
  oos_from: Optional[date] = None


class Report(BaseModel):
  id: str | None = None
  created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  spec: RunSpec
  leakage: LeakageCheck | None = None
  data_range: dict[str, Any] = Field(default_factory=dict)
  oos_start: str | None = None
  overall_oos: MetricsPack | None = None
  last_1_year: MetricsPack | None = None
  constraints_met: dict[str, bool] = Field(default_factory=dict)
  weekly_log: list[dict[str, Any]] = Field(default_factory=list)
  trades: list[TradeRecord] = Field(default_factory=list)
  holdout_forward: dict[str, Any] | None = None
  last_strategy: dict[str, Any] | None = None
  epoch_history: list[dict[str, Any]] = Field(default_factory=list)
  raw: dict[str, Any] = Field(default_factory=dict)

  @model_validator(mode="before")
  @classmethod
  def _coerce_metrics(cls, data: Any):
    if not isinstance(data, dict):
      return data
    for key in ("overall_oos", "last_1_year"):
      if isinstance(data.get(key), dict):
        data[key] = MetricsPack(**data[key])
    return data


class JobEvent(BaseModel):
  job_id: str
  status: Literal["queued", "running", "progress", "done", "failed", "cancelled"]
  current: int = 0
  total: int = 0
  message: str = ""
  payload: dict[str, Any] = Field(default_factory=dict)
