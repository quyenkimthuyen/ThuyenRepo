"""Quarterly rolling re-mine on 1-year windows."""

from __future__ import annotations

from typing import Any

import pandas as pd

from systemtrain.backtest.engine import BacktestEngine
from systemtrain.optimize.backtest_mine import BacktestMiner
from systemtrain.optimize.models import CandidateResult, GAResult


def quarterly_rolling_mine(
    train_df: pd.DataFrame,
    engine: BacktestEngine,
    fitness_cfg: dict,
    wf_cfg,
    random_trials: int = 80,
    top_per_window: int = 5,
    seed: int = 42,
) -> GAResult:
    """
    Re-mine every quarter on rolling 1-year window within train data.
    Adapts to regime shifts instead of fitting one static year.
    """
    end = train_df.index.max()
    all_candidates: list[CandidateResult] = []
    log: list[dict[str, Any]] = []

    for q in range(4):
        window_end = end - pd.DateOffset(months=3 * q)
        window_start = window_end - pd.DateOffset(months=12)
        chunk = train_df.loc[window_start:window_end].copy()
        if len(chunk) < 500:
            continue

        miner = BacktestMiner(
            engine=engine,
            train_df=chunk,
            fitness_cfg=fitness_cfg,
            wf_cfg=wf_cfg,
            top_k=top_per_window,
            random_trials=max(random_trials // 4, 40),
            seed=seed + q,
        )
        result = miner.run()
        all_candidates.extend(result.best_candidates)
        log.append({
            "quarter": q,
            "window": f"{window_start.date()} -> {window_end.date()}",
            "bars": len(chunk),
            "found": len(result.best_candidates),
        })

    # Deduplicate by learned setup
    seen: set[str] = set()
    unique: list[CandidateResult] = []
    for c in sorted(all_candidates, key=lambda x: x.fitness, reverse=True):
        key = str(c.gene.learned_setup)
        if key in seen:
            continue
        wf = c.wf_summary or {}
        holdout = wf.get("holdout", {})
        # Drop thin or failed holdout setups
        if wf.get("folds_total", 0) < 2 and c.train_metrics.get("trade_count", 0) < 50:
            continue
        if holdout and holdout.get("trade_count", 0) >= 8:
            if holdout.get("profit_factor", 0) < 0.75:
                continue
            if holdout.get("win_rate", 0) < 0.25:
                continue
        seen.add(key)
        unique.append(c)

    return GAResult(best_candidates=unique, generation_log=log)
