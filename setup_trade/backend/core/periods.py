from __future__ import annotations

from typing import Any

import pandas as pd

from .config import PERIODS_PATH, load_json


def load_periods_config() -> dict[str, Any]:
    return load_json(PERIODS_PATH)


def period_bounds(period: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    cfg = load_periods_config()["periods"][period]
    start = pd.Timestamp(cfg["from"], tz="UTC")
    end = pd.Timestamp(cfg["to"], tz="UTC") + pd.Timedelta(hours=23, minutes=59)
    return start, end


def validate_fold_rules(fold: dict[str, Any]) -> list[str]:
    """Return list of validation errors for walk-forward fold."""
    errors: list[str] = []
    rules = load_periods_config().get("rules") or {}
    label_year = fold.get("label_year")
    optimize_year = fold.get("optimize_year")
    final_year = fold.get("final_test_year")

    if rules.get("forbid_optimize_same_year_as_label") and label_year == optimize_year:
        errors.append(f"optimize_year ({optimize_year}) trùng label_year ({label_year})")
    if rules.get("forbid_backtest_on_label_year"):
        if final_year == label_year:
            errors.append(f"final_test_year ({final_year}) trùng label_year ({label_year})")
        if final_year == optimize_year:
            errors.append(f"final_test_year ({final_year}) trùng optimize_year ({optimize_year})")
    return errors


def validate_all_folds() -> dict[str, list[str]]:
    cfg = load_periods_config()
    return {fold["id"]: validate_fold_rules(fold) for fold in cfg.get("folds", [])}


def period_for_timestamp(ts: pd.Timestamp) -> str | None:
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    for name, meta in load_periods_config().get("periods", {}).items():
        start = pd.Timestamp(meta["from"], tz="UTC")
        end = pd.Timestamp(meta["to"], tz="UTC") + pd.Timedelta(hours=23, minutes=59)
        if start <= ts <= end:
            return name
    return None
