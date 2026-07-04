from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.backtest.metrics import compute_metrics
from systemtrain.backtest.portfolio import PortfolioEngine
from systemtrain.experiments.benchmark import (
    _filter_candidates,
    _select_genes,
    _sort_candidates,
)
from systemtrain.backtest.risk import RiskConfig
from systemtrain.config import Config
from systemtrain.data.ingest import ensure_data, load_csv
from systemtrain.data.prepared import prepare_dataframe
from systemtrain.data.quality import check_quality
from systemtrain.data.split import split_train_oos
from systemtrain.data.timeframes import to_entry_timeframe
from systemtrain.optimize.backtest_mine import BacktestMiner
from systemtrain.optimize.models import CandidateResult
from systemtrain.optimize.quarterly_mine import quarterly_rolling_mine
from systemtrain.optimize.refine import rank_validated
from systemtrain.validate.monte_carlo import run_monte_carlo
from systemtrain.validate.oos_gate import OOSVerdict, evaluate_oos_gate
from systemtrain.validate.registry import StrategyRegistry


@dataclass
class PipelineResult:
    train_df: pd.DataFrame
    oos_df: pd.DataFrame
    quality: dict[str, Any]
    ga_result: Any = None
    validated_strategies: list[dict[str, Any]] = field(default_factory=list)
    portfolio_oos: dict[str, Any] = field(default_factory=dict)
    output_dir: Path = field(default_factory=Path)


class TrainingPipeline:
    def __init__(self, config: Config | None = None):
        self.config = config or Config.load()
        self._setup_dirs()

    def _setup_dirs(self) -> None:
        data_dir = Path(self.config.data.get("data_dir", "data/store"))
        self.data_dir = data_dir
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

    def _build_engine(self) -> BacktestEngine:
        risk = RiskConfig(
            sl_pct=self.config.risk.get("sl_pct", 0.02),
            min_rr=self.config.risk.get("min_rr", 2.0),
            max_drawdown=self.config.risk.get("max_drawdown", 0.30),
            max_consecutive_losses=self.config.risk.get("max_consecutive_losses", 10),
            max_concurrent_positions=self.config.risk.get("max_concurrent_positions", 1),
        )
        bt = self.config.backtest
        return BacktestEngine(
            risk_config=risk,
            initial_equity=bt.get("initial_equity", 10000.0),
            spread_pips=bt.get("spread_pips", 0.5),
            slippage_pips=bt.get("slippage_pips", 0.3),
            pip_size=self.config.pip_size,
        )

    def load_data(self, csv_path: str | Path | None = None, force_regenerate: bool = False) -> pd.DataFrame:
        if csv_path:
            df = load_csv(csv_path)
        else:
            years = self.config.data.get("years_total", 3)
            df = ensure_data(self.data_dir, years=years, force_regenerate=force_regenerate)

        entry_tf = getattr(self.config, "entry_timeframe", None) or self.config.data.get("entry_timeframe", "1h")
        if entry_tf != self.config.data.get("source_timeframe", "15m"):
            df = to_entry_timeframe(df, entry_tf)
        return df

    def run(
        self,
        csv_path: str | Path | None = None,
        force_regenerate: bool = False,
        quick: bool = False,
    ) -> PipelineResult:
        df = self.load_data(csv_path, force_regenerate)
        quality = check_quality(df)

        train_years = self.config.data.get("train_years", 1)
        oos_years = self.config.data.get("oos_years", 2)
        train_df, oos_df = split_train_oos(df, train_years, oos_years)

        if quick:
            train_end = train_df.index.min() + pd.DateOffset(months=6)
            train_df = train_df.loc[:train_end].copy()

        htf_rule = getattr(self.config, "htf_timeframe", None) or "4h"
        train_df = prepare_dataframe(train_df, htf_rule=htf_rule)
        oos_df = prepare_dataframe(oos_df, htf_rule=htf_rule)

        engine = self._build_engine()
        opt = self.config.optimize
        trials = 80 if quick else opt.get("expert_trials", 300)
        top_k = opt.get("top_k", 3)

        print(f"  Entry TF: {self.config.timeframe} | HTF filter: {htf_rule}")
        print(f"  Spread: {self.config.backtest.get('spread_pips', 0.5)} pip ECN")

        filter_mode = opt.get("filter_mode", "robust")
        select_mode = opt.get("select_mode", "uncorrelated")

        if opt.get("quarterly_remine", True) and not quick:
            print(f"  Mode: quarterly rolling re-mine | filter={filter_mode} select={select_mode}")
            ga_result = quarterly_rolling_mine(
                train_df, engine, self.config.fitness,
                self.config.walk_forward, random_trials=trials, top_per_window=5,
            )
        else:
            print(f"  Mode: single backtest mine | filter={filter_mode} select={select_mode}")
            ga_result = BacktestMiner(
                engine=engine, train_df=train_df, fitness_cfg=self.config.fitness,
                wf_cfg=self.config.walk_forward, top_k=top_k * 4,
                random_trials=trials, seed=42,
            ).run()

        pool = _filter_candidates(engine, train_df, ga_result.best_candidates, filter_mode)

        if opt.get("portfolio_mode", True) and top_k > 1 and pool:
            genes = _select_genes(engine, train_df, pool, top_k, select_mode)
            gene_set = {id(g) for g in genes}
            selected = [c for c in pool if id(c.gene) in gene_set]
            if len(selected) < top_k:
                selected = _sort_candidates(engine, train_df, pool, select_mode)[:top_k]
        else:
            selected = _sort_candidates(engine, train_df, pool, select_mode)[:top_k]

        enforce_gate = opt.get("enforce_gate", False)
        validated: list[dict[str, Any]] = []
        portfolio_genes = [c.gene for c in selected[:top_k]]

        for candidate in selected[:top_k]:
            validated.append(
                self._validate_candidate(engine, candidate, train_df, oos_df, enforce_gate)
            )

        # Portfolio combined OOS
        portfolio_oos: dict[str, Any] = {}
        if portfolio_genes:
            pf_engine = PortfolioEngine(engine)
            pf_train = pf_engine.run(train_df, portfolio_genes)
            pf_oos = pf_engine.run(oos_df, portfolio_genes)
            portfolio_oos = {
                "train_metrics": pf_train.metrics,
                "oos_metrics": pf_oos.metrics,
                "per_strategy_train": pf_train.per_strategy,
                "per_strategy_oos": pf_oos.per_strategy,
                "strategy_count": len(portfolio_genes),
            }
            print(
                f"\n  Portfolio OOS: WR={pf_oos.metrics.get('win_rate', 0):.1%} "
                f"PF={pf_oos.metrics.get('profit_factor', 0):.2f} "
                f"trades={pf_oos.metrics.get('trade_count', 0)} "
                f"return={pf_oos.metrics.get('total_return', 0):.1%}"
            )

        registry = StrategyRegistry(self.output_dir / "strategies.db")
        registry_records = []
        for i, v in enumerate(validated, 1):
            v["rank_order"] = i
            v["rank_score"] = rank_validated(v)
            registry_records.append({
                "gene": v["_gene"],
                "symbol": self.config.symbol,
                "timeframe": self.config.timeframe,
                "train_metrics": v["train_metrics"],
                "oos_metrics": v["oos_metrics"],
                "wf_summary": v.get("wf_summary", {}),
                "monte_carlo": v.get("monte_carlo", {}),
                "verdict": v["_verdict"],
                "rank_score": v["rank_score"],
            })
            v.pop("_verdict", None)
            v.pop("_gene", None)
        registry.replace_top_strategies(registry_records)

        self._write_run_report(ga_result, validated, quality, train_df, oos_df, portfolio_oos)

        return PipelineResult(
            train_df=train_df,
            oos_df=oos_df,
            quality=quality,
            ga_result=ga_result,
            validated_strategies=validated,
            portfolio_oos=portfolio_oos,
            output_dir=self.output_dir,
        )

    def _validate_candidate(
        self,
        engine: BacktestEngine,
        candidate: CandidateResult,
        train_df: pd.DataFrame,
        oos_df: pd.DataFrame,
        enforce_gate: bool,
    ) -> dict[str, Any]:
        train_result = engine.run(train_df, candidate.gene)
        train_metrics = compute_metrics(train_result)
        oos_result = engine.run(oos_df, candidate.gene)
        oos_metrics = compute_metrics(oos_result)
        verdict = evaluate_oos_gate(oos_metrics, train_metrics, self.config.oos_gate)

        mc_cfg = self.config.monte_carlo
        monte_carlo = run_monte_carlo(
            oos_result.trades,
            self.config.backtest.get("initial_equity", 10000.0),
            simulations=mc_cfg.get("simulations", 300),
        )

        if not enforce_gate:
            verdict = OOSVerdict(
                passed=True,
                reasons=["gate_disabled — informational only"] + verdict.reasons[:3],
                metrics=verdict.metrics,
                train_metrics=verdict.train_metrics,
            )
            final_passed = True
        else:
            mc_passed = monte_carlo["positive_pct"] >= mc_cfg.get("min_positive_pct", 0.50)
            final_passed = verdict.passed and mc_passed and not oos_metrics.get("halted")
            if not mc_passed:
                verdict = OOSVerdict(
                    passed=False,
                    reasons=verdict.reasons + [f"monte_carlo={monte_carlo['positive_pct']:.2f}"],
                    metrics=verdict.metrics,
                    train_metrics=verdict.train_metrics,
                )

        return {
            "passed": final_passed,
            "fitness": candidate.fitness,
            "train_metrics": train_metrics,
            "oos_metrics": oos_metrics,
            "wf_summary": candidate.wf_summary,
            "monte_carlo": monte_carlo,
            "verdict_reasons": verdict.reasons,
            "gene": candidate.gene.to_dict(),
            "_verdict": verdict,
            "_gene": candidate.gene,
        }

    def _write_run_report(
        self,
        ga_result,
        validated: list[dict],
        quality: dict,
        train_df: pd.DataFrame,
        oos_df: pd.DataFrame,
        portfolio_oos: dict,
    ) -> None:
        report = {
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "htf_filter": getattr(self.config, "htf_timeframe", "4h"),
            "spread_pips": self.config.backtest.get("spread_pips", 0.5),
            "data_quality": quality,
            "train_period": {"start": str(train_df.index.min()), "end": str(train_df.index.max())},
            "oos_period": {"start": str(oos_df.index.min()), "end": str(oos_df.index.max())},
            "strategies_kept": len(validated),
            "portfolio": portfolio_oos,
            "quarterly_log": ga_result.generation_log,
            "validated_strategies": validated,
        }
        with (self.output_dir / "run_report.json").open("w") as f:
            json.dump(report, f, indent=2, default=str)
