"""Benchmark all mining/selection modes — pick winner by blind OOS."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.portfolio import PortfolioEngine, select_uncorrelated_genes
from systemtrain.config import Config
from systemtrain.optimize.backtest_mine import BacktestMiner
from systemtrain.optimize.models import CandidateResult
from systemtrain.optimize.quarterly_mine import quarterly_rolling_mine
from systemtrain.optimize.scoring import holdout_metrics
from systemtrain.strategy.dsl import StrategyGene


FilterMode = Literal["none", "robust", "holdout"]
SelectMode = Literal["fitness", "holdout", "wf", "uncorrelated"]


@dataclass
class ExperimentSpec:
    name: str
    mine_mode: Literal["quarterly", "single"] = "quarterly"
    portfolio_n: int = 1  # 0 = best single only
    filter_mode: FilterMode = "none"
    select_mode: SelectMode = "fitness"
    seed: int = 42


@dataclass
class ExperimentResult:
    spec: ExperimentSpec
    oos_metrics: dict[str, Any] = field(default_factory=dict)
    train_metrics: dict[str, Any] = field(default_factory=dict)
    strategy_count: int = 0
    candidate_pool_size: int = 0
    score: float = 0.0


def _candidate_holdout(engine, train_df, c: CandidateResult) -> dict:
    wf = c.wf_summary or {}
    h = wf.get("holdout") or {}
    if h.get("trade_count", 0) >= 8:
        return h
    return holdout_metrics(engine, train_df, c.gene)


def _filter_candidates(
    engine, train_df, candidates: list[CandidateResult], mode: FilterMode
) -> list[CandidateResult]:
    if mode == "none":
        return candidates
    out: list[CandidateResult] = []
    for c in candidates:
        wf = c.wf_summary or {}
        h = _candidate_holdout(engine, train_df, c)
        if mode == "robust":
            if h and h.get("trade_count", 0) >= 8:
                if h.get("profit_factor", 0) < 0.9 or h.get("win_rate", 0) < 0.28:
                    continue
            if wf.get("folds_total", 0) >= 2 and wf.get("avg_profit_factor", 0) < 0.8:
                continue
        elif mode == "holdout":
            if not h or h.get("trade_count", 0) < 8:
                continue
            if h.get("profit_factor", 0) < 1.0 or h.get("win_rate", 0) < 0.30:
                continue
        out.append(c)
    return out if out else candidates


def _sort_candidates(
    engine, train_df, candidates: list[CandidateResult], mode: SelectMode
) -> list[CandidateResult]:
    if mode == "fitness":
        return sorted(candidates, key=lambda c: c.fitness, reverse=True)
    if mode == "holdout":
        def key(c):
            h = _candidate_holdout(engine, train_df, c)
            return h.get("profit_factor", 0) * 2 + h.get("win_rate", 0) * 3
        return sorted(candidates, key=key, reverse=True)
    if mode == "wf":
        def key(c):
            wf = c.wf_summary or {}
            return wf.get("avg_win_rate", 0) * 3 + min(wf.get("avg_profit_factor", 0), 3) * 2
        return sorted(candidates, key=key, reverse=True)
    return candidates


def _select_genes(
    engine,
    train_df,
    candidates: list[CandidateResult],
    n: int,
    select_mode: SelectMode,
) -> list[StrategyGene]:
    if not candidates:
        return []
    if select_mode == "uncorrelated" and n > 1:
        return select_uncorrelated_genes(candidates[: n * 4], train_df, engine, n=n)
    sorted_c = _sort_candidates(engine, train_df, candidates, select_mode)
    return [c.gene for c in sorted_c[:n]]


def oos_score(metrics: dict[str, Any]) -> float:
    """Composite blind-OOS score for ranking experiments."""
    ret = metrics.get("total_return", -1)
    pf = metrics.get("profit_factor", 0)
    wr = metrics.get("win_rate", 0)
    dd = metrics.get("max_drawdown", 1)
    trades = metrics.get("trade_count", 0)
    if trades < 15:
        return -10.0 + trades * 0.1
    score = ret * 100 + min(pf, 3) * 8 + wr * 5 - dd * 15
    if pf >= 1.0 and ret > 0:
        score += 10
    if metrics.get("halted"):
        score -= 8
    return float(score)


def mine_candidates(
    engine: BacktestEngine,
    train_df: pd.DataFrame,
    config: Config,
    mode: Literal["quarterly", "single"],
    trials: int = 100,
    seed: int = 42,
) -> list[CandidateResult]:
    top_k = config.optimize.get("top_k", 3)
    if mode == "quarterly":
        result = quarterly_rolling_mine(
            train_df, engine, config.fitness, config.walk_forward,
            random_trials=trials, top_per_window=8, seed=seed,
        )
    else:
        result = BacktestMiner(
            engine=engine, train_df=train_df, fitness_cfg=config.fitness,
            wf_cfg=config.walk_forward, top_k=top_k * 4,
            random_trials=trials, seed=seed,
        ).run()
    return result.best_candidates


def run_experiment(
    spec: ExperimentSpec,
    engine: BacktestEngine,
    train_df: pd.DataFrame,
    oos_df: pd.DataFrame,
    config: Config,
    candidates: list[CandidateResult] | None = None,
    trials: int = 100,
) -> ExperimentResult:
    pool = candidates if candidates is not None else mine_candidates(
        engine, train_df, config, spec.mine_mode, trials=trials, seed=spec.seed
    )
    filtered = _filter_candidates(engine, train_df, pool, spec.filter_mode)
    n = max(1, spec.portfolio_n)

    if spec.select_mode == "uncorrelated" and n > 1:
        genes = _select_genes(engine, train_df, filtered, n, "uncorrelated")
    else:
        sorted_c = _sort_candidates(engine, train_df, filtered, spec.select_mode)
        genes = [c.gene for c in sorted_c[:n]]

    if not genes:
        return ExperimentResult(spec=spec, candidate_pool_size=len(pool))

    if len(genes) == 1:
        r = engine.run(oos_df, genes[0])
        oos_m = compute_metrics(r)
        tr = engine.run(train_df, genes[0])
        train_m = compute_metrics(tr)
    else:
        pf = PortfolioEngine(engine)
        oos_m = pf.run(oos_df, genes).metrics
        train_m = pf.run(train_df, genes).metrics

    return ExperimentResult(
        spec=spec,
        oos_metrics=oos_m,
        train_metrics=train_m,
        strategy_count=len(genes),
        candidate_pool_size=len(pool),
        score=oos_score(oos_m),
    )


def all_experiment_specs() -> list[ExperimentSpec]:
    """Matrix of configurations to benchmark."""
    specs: list[ExperimentSpec] = []
    for mine in ("quarterly", "single"):
        for n in (1, 2, 3):
            for filt in ("none", "robust", "holdout"):
                for sel in ("fitness", "holdout", "wf", "uncorrelated"):
                    if n == 1 and sel == "uncorrelated":
                        continue
                    name = f"{mine}_p{n}_{filt}_{sel}"
                    specs.append(ExperimentSpec(
                        name=name, mine_mode=mine, portfolio_n=n,
                        filter_mode=filt, select_mode=sel,
                    ))
    return specs


def run_all_experiments(
    config: Config | None = None,
    trials: int = 100,
    quick_specs: bool = False,
) -> tuple[list[ExperimentResult], ExperimentResult | None]:
    """
    Run benchmark. Mines once per mine_mode, reuses pools for all selection variants.
    Returns (all_results, winner).
    """
    config = config or Config.load()
    from systemtrain.data.ingest import ensure_data
    from systemtrain.data.prepared import prepare_dataframe
    from systemtrain.data.split import split_train_oos
    from systemtrain.data.timeframes import to_entry_timeframe
    from systemtrain.backtest.risk import RiskConfig

    data_dir = Path(config.data.get("data_dir", "data/store"))
    df = ensure_data(data_dir, years=config.data.get("years_total", 3))
    entry_tf = config.data.get("entry_timeframe", "1h")
    if entry_tf != config.data.get("source_timeframe", "15m"):
        df = to_entry_timeframe(df, entry_tf)
    train_df, oos_df = split_train_oos(df, config.data.get("train_years", 1), config.data.get("oos_years", 2))
    htf = getattr(config, "htf_timeframe", "4h")
    train_df = prepare_dataframe(train_df, htf_rule=htf)
    oos_df = prepare_dataframe(oos_df, htf_rule=htf)

    risk = RiskConfig(
        sl_pct=config.risk.get("sl_pct", 0.02),
        min_rr=config.risk.get("min_rr", 2.0),
        max_drawdown=config.risk.get("max_drawdown", 0.30),
        max_consecutive_losses=config.risk.get("max_consecutive_losses", 10),
    )
    bt = config.backtest
    engine = BacktestEngine(
        risk_config=risk,
        initial_equity=bt.get("initial_equity", 10000.0),
        spread_pips=bt.get("spread_pips", 0.5),
        slippage_pips=bt.get("slippage_pips", 0.3),
        pip_size=config.pip_size,
    )

    specs = all_experiment_specs() if not quick_specs else _quick_specs()
    pools: dict[str, list[CandidateResult]] = {}
    results: list[ExperimentResult] = []

    print(f"Benchmark: {len(specs)} configs | trials={trials}")
    print(f"Train: {train_df.index.min().date()} -> {train_df.index.max().date()}")
    print(f"OOS:   {oos_df.index.min().date()} -> {oos_df.index.max().date()}\n")

    for mine_mode in ("quarterly", "single"):
        print(f"Mining [{mine_mode}]...")
        pools[mine_mode] = mine_candidates(engine, train_df, config, mine_mode, trials=trials)
        print(f"  -> {len(pools[mine_mode])} candidates\n")

    for i, spec in enumerate(specs, 1):
        r = run_experiment(spec, engine, train_df, oos_df, config, candidates=pools[spec.mine_mode])
        results.append(r)
        o = r.oos_metrics
        print(
            f"[{i:2d}/{len(specs)}] {spec.name:35s} "
            f"OOS ret={o.get('total_return', 0):+6.1%} PF={o.get('profit_factor', 0):.2f} "
            f"WR={o.get('win_rate', 0):.1%} trades={o.get('trade_count', 0):3d} score={r.score:6.1f}"
        )

    winner = max(results, key=lambda r: r.score) if results else None
    return results, winner


def _quick_specs() -> list[ExperimentSpec]:
    """Smaller matrix for fast iteration."""
    combos = [
        ("quarterly", 1, "none", "fitness"),
        ("quarterly", 1, "robust", "holdout"),
        ("quarterly", 1, "holdout", "holdout"),
        ("quarterly", 2, "robust", "uncorrelated"),
        ("quarterly", 2, "holdout", "holdout"),
        ("quarterly", 3, "none", "uncorrelated"),
        ("quarterly", 3, "robust", "uncorrelated"),
        ("single", 1, "none", "fitness"),
        ("single", 1, "robust", "wf"),
        ("single", 1, "holdout", "holdout"),
        ("single", 2, "robust", "uncorrelated"),
        ("single", 3, "none", "uncorrelated"),
    ]
    return [
        ExperimentSpec(
            name=f"{m}_p{n}_{f}_{s}",
            mine_mode=m, portfolio_n=n, filter_mode=f, select_mode=s,
        )
        for m, n, f, s in combos
    ]
