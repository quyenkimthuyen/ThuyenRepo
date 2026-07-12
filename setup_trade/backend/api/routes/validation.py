from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from backend.research.validation import get_latest_validation, run_walk_forward_validation

router = APIRouter()


@router.post("/validation/{fold_id}")
def run_validation(
    fold_id: str,
    skip_optimize: bool = Query(False),
    save_strategy: bool = Query(True),
) -> dict:
    try:
        return run_walk_forward_validation(
            fold_id,
            skip_optimize=skip_optimize,
            save_strategy=save_strategy,
        )
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/validation/{fold_id}")
def get_validation(fold_id: str) -> dict:
    result = get_latest_validation(fold_id)
    if not result:
        raise HTTPException(404, f"Chưa có validation cho {fold_id}")
    return result


@router.get("/validation/{fold_id}/report")
def validation_report(fold_id: str) -> HTMLResponse:
    result = get_latest_validation(fold_id)
    if not result or not result.get("report_path"):
        raise HTTPException(404, f"Chưa có báo cáo validation cho {fold_id}")
    from pathlib import Path

    html = Path(result["report_path"]).read_text(encoding="utf-8")
    return HTMLResponse(html)
