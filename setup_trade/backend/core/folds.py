from __future__ import annotations

from typing import Any, Literal

from fastapi import HTTPException

from backend.core.periods import load_periods_config, validate_fold_rules

PeriodRole = Literal["label", "optimize", "final_test", "unknown"]


def list_folds() -> list[dict[str, Any]]:
    return load_periods_config().get("folds", [])


def get_fold(fold_id: str) -> dict[str, Any]:
    for fold in list_folds():
        if fold["id"] == fold_id:
            return fold
    raise KeyError(f"Unknown fold: {fold_id}")


def period_role(period: str) -> PeriodRole:
    for fold in list_folds():
        if fold.get("label_period") == period:
            return "label"
        if fold.get("optimize_period") == period:
            return "optimize"
        if fold.get("final_test_period") == period:
            return "final_test"
    return "unknown"


def fold_containing_period(period: str) -> dict[str, Any] | None:
    for fold in list_folds():
        if period in (
            fold.get("label_period"),
            fold.get("optimize_period"),
            fold.get("final_test_period"),
        ):
            return fold
    return None


def require_optimize_period(period: str) -> dict[str, Any]:
    fold = fold_containing_period(period)
    if not fold or fold.get("optimize_period") != period:
        raise HTTPException(400, f"{period} không phải optimize_period hợp lệ")
    errs = validate_fold_rules(fold)
    if errs:
        raise HTTPException(400, f"Fold invalid: {errs}")
    return fold


def require_final_test_period(period: str) -> dict[str, Any]:
    fold = fold_containing_period(period)
    if not fold or fold.get("final_test_period") != period:
        raise HTTPException(400, f"{period} không phải final_test_period — chỉ chạy final 1 lần")
    errs = validate_fold_rules(fold)
    if errs:
        raise HTTPException(400, f"Fold invalid: {errs}")
    return fold


def require_label_period(period: str) -> dict[str, Any]:
    fold = fold_containing_period(period)
    if not fold or fold.get("label_period") != period:
        raise HTTPException(400, f"{period} không phải label_period")
    return fold
