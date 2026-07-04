from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from systemtrain.strategy.dsl import StrategyGene


@dataclass
class CandidateResult:
    gene: StrategyGene
    fitness: float
    train_metrics: dict[str, Any]
    wf_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class GAResult:
    best_candidates: list[CandidateResult]
    generation_log: list[dict[str, Any]]
