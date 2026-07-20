"""ForexForge v2 — research core (walk-forward + KB causal + cost model)."""

from .contracts import (
  CostModel,
  EpochSnapshot,
  InstrumentSpec,
  JobKind,
  KbProfile,
  LeakageCheck,
  MetricsPack,
  Report,
  RunSpec,
  SignalRecord,
  TradeRecord,
)
from .leakage import LeakageError, assert_no_leakage, check_kb_leakage
from .wf_runner import execute_run, run_backtest, run_learning

__version__ = "2.0.0"
__all__ = [
  "CostModel",
  "EpochSnapshot",
  "InstrumentSpec",
  "JobKind",
  "KbProfile",
  "LeakageCheck",
  "LeakageError",
  "MetricsPack",
  "Report",
  "RunSpec",
  "SignalRecord",
  "TradeRecord",
  "assert_no_leakage",
  "check_kb_leakage",
  "execute_run",
  "run_backtest",
  "run_learning",
]
