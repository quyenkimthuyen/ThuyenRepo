from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from systemtrain.config import WalkForwardConfig


@dataclass
class WalkForwardFold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def generate_walk_forward_folds(
    df: pd.DataFrame,
    wf_cfg: WalkForwardConfig,
) -> list[WalkForwardFold]:
    folds: list[WalkForwardFold] = []
    start = df.index.min()
    end = df.index.max()

    cursor = start
    while True:
        train_end = cursor + pd.DateOffset(months=wf_cfg.train_months)
        test_end = train_end + pd.DateOffset(months=wf_cfg.test_months)
        if test_end > end:
            break
        folds.append(
            WalkForwardFold(
                train_start=cursor,
                train_end=train_end,
                test_start=train_end,
                test_end=test_end,
            )
        )
        cursor = cursor + pd.DateOffset(months=wf_cfg.step_months)

    return folds


def slice_fold(df: pd.DataFrame, fold: WalkForwardFold, part: str) -> pd.DataFrame:
    if part == "train":
        return df.loc[fold.train_start:fold.train_end].copy()
    return df.loc[fold.test_start:fold.test_end].iloc[1:].copy()


def aggregate_walk_forward_results(fold_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not fold_metrics:
        return {"folds_passed": 0, "folds_total": 0, "avg_win_rate": 0.0}

    win_rates = [m.get("win_rate", 0) for m in fold_metrics]
    pfs = [m.get("profit_factor", 0) for m in fold_metrics]
    dds = [m.get("max_drawdown", 0) for m in fold_metrics]
    passed = sum(1 for m in fold_metrics if m.get("passed", False))

    return {
        "folds_passed": passed,
        "folds_total": len(fold_metrics),
        "avg_win_rate": sum(win_rates) / len(win_rates),
        "avg_profit_factor": sum(pfs) / len(pfs),
        "avg_max_drawdown": sum(dds) / len(dds),
        "fold_details": fold_metrics,
    }
