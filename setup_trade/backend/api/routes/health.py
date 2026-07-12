from __future__ import annotations

from fastapi import APIRouter

from backend.core.config import ROOT
from backend.core.periods import load_periods_config, validate_all_folds

router = APIRouter()


@router.get("/health")
def health() -> dict:
    fold_errors = validate_all_folds()
    ok = all(not errs for errs in fold_errors.values())
    return {
        "status": "ok" if ok else "degraded",
        "app": "setup_trade",
        "version": "0.1.0",
        "walk_forward_valid": ok,
        "fold_errors": {k: v for k, v in fold_errors.items() if v},
    }


@router.get("/config/periods")
def get_periods() -> dict:
    return load_periods_config()
