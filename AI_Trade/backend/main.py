from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analyzer import analyze_patterns, list_strategies, load_strategy, save_strategy
from .optimizer import analyze_and_optimize
from .strategy_registry import default_strategy_id, list_strategy_types
from .backtest import run_backtest
from .bt_store import compare_runs, delete_run, get_run, list_runs, rename_run, save_run
from .data_service import candles_to_records, load_candles, load_splits, slice_period, slice_month, months_for_period, filter_records_by_month, month_bounds
from .periods import (
    default_train_period,
    normalize_backtest_periods,
    normalize_setup_period,
    period_exists,
    periods_grouped_for_api,
    resolve_period,
)
from .indicators import add_indicators
from .labels import create_setup, delete_setup, enrich_setup, load_setups, setup_summary, update_setup
from .setup_quality import apply_curation, curate_train_setups, enrich_setup_quality, load_quality_config
from .bar_annotations import delete_annotation, load_bar_annotations, upsert_annotation, annotation_summary
from .bar_importance import inspect_bar_at_time, scan_important_bars
from .pipeline import pipeline_status
from .detection_config import load_bar_detection_config, save_bar_detection_config
from .tag_matcher import tag_definitions
from .workflow import workflow_status

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

app = FastAPI(title="AI Trade Lab", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_js_cache(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") and path.endswith((".js", ".css", ".mjs")):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


class SetupIn(BaseModel):
    direction: str
    entry_time: str
    entry_price: float
    stop_loss: float
    take_profit: float
    tags: list[str] = Field(default_factory=list)
    bar_tags: list[str] = Field(default_factory=list)
    sequence_tags: list[str] = Field(default_factory=list)
    annotation_id: str | None = None
    note: str = ""
    train_period: str | None = None
    strategy_id: str | None = None


class StrategyPatch(BaseModel):
    train_period: str
    strategy_id: str | None = None
    bands: dict[str, list[float]] | None = None
    lookback_bars: int | None = None
    entry_cooldown_bars: int | None = None
    exit_confirm_bars: int | None = None
    ema_tolerance_atr: float | None = None
    cross_lookback_bars: int | None = None
    min_trend_sep_atr: float | None = None
    setups: dict[str, Any] | None = None
    risk: dict[str, Any] | None = None


class SetupPatch(BaseModel):
    direction: str | None = None
    entry_time: str | None = None
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    tags: list[str] | None = None
    bar_tags: list[str] | None = None
    sequence_tags: list[str] | None = None
    annotation_id: str | None = None
    note: str | None = None


class TagSuggestIn(BaseModel):
    entry_time: str
    entry_price: float


class BarDetectionPatch(BaseModel):
    min_score: float | None = None
    backtest_min_score: float | None = None
    require_sequence_tag: bool | None = None
    max_bars: int | None = None
    sequence_window: int | None = None
    sequence_min_score: float | None = None
    bar_tag_threshold: float | None = None
    score_weights: dict[str, float | int] | None = None
    thresholds: dict[str, float] | None = None
    feature_weights: dict[str, float] | None = None


class BarAnnotationIn(BaseModel):
    bar_time: str
    close: float
    tags: list[str] = Field(default_factory=list)
    note: str = ""
    confirmed: bool = True
    auto_detected_tags: list[str] = Field(default_factory=list)
    score: float | None = None
    id: str | None = None
    train_period: str | None = None


class BacktestSaveIn(BaseModel):
    name: str | None = None
    period: str = "validation"
    result: dict[str, Any]


class BacktestRenameIn(BaseModel):
    name: str


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def get_config():
    cfg = load_splits()
    cfg["presets"] = load_presets()
    cfg["bar_detection"] = load_bar_detection_config()
    cfg["quality"] = load_quality_config()
    cfg["pipeline"] = pipeline_status()
    cfg["period_groups"] = periods_grouped_for_api()
    cfg["strategy_types"] = list_strategy_types()
    cfg["default_strategy_id"] = default_strategy_id()
    return cfg


@app.get("/api/bar-detection/config")
def get_bar_detection():
    return load_bar_detection_config()


@app.patch("/api/bar-detection/config")
def patch_bar_detection(body: BarDetectionPatch):
    patch = body.model_dump(exclude_none=True)
    if not patch:
        raise HTTPException(400, "Không có thay đổi")
    return save_bar_detection_config(patch)


@app.get("/api/presets")
def get_presets():
    return load_presets()


def _indicator_series_aligned(df: pd.DataFrame) -> dict[str, list[dict[str, float | int]]]:
    """Indicator points dùng cùng timestamp với nến — đồng bộ chart RSI."""
    digits = {"ema50": 5, "ema200": 5, "rsi14": 2, "rsi14_h4": 2}
    out: dict[str, list[dict[str, float | int]]] = {k: [] for k in digits}
    for ts, row in df.iterrows():
        t = int(ts.timestamp())
        for col, d in digits.items():
            val = row.get(col)
            if val is None or pd.isna(val):
                continue
            out[col].append({"time": t, "value": round(float(val), d)})
    return out


@app.get("/api/candles")
def get_candles(period: str = "train_2022", month: str | None = None, with_indicators: bool = True):
    period = resolve_period(period)
    try:
        df = slice_period(load_candles(), period)
        if month:
            df = slice_month(df, month)
    except KeyError:
        raise HTTPException(400, f"Unknown period: {period}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    if df.empty:
        return {"period": period, "month": month, "count": 0, "candles": [], "indicators": None}

    if with_indicators:
        df = add_indicators(df)

    records = candles_to_records(df)
    indicators = None
    if with_indicators:
        indicators = _indicator_series_aligned(df)
    return {"period": period, "month": month, "count": len(records), "candles": records, "indicators": indicators}


@app.get("/api/months")
def list_months(period: str = "train_2022"):
    period = resolve_period(period)
    if not period_exists(period):
        raise HTTPException(400, f"Unknown period: {period}")
    try:
        months = months_for_period(period)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    setups = load_setups()
    annotations = load_bar_annotations()
    bar_by_id = {a["id"]: a for a in annotations}
    payload = []
    for month in months:
        start, end = month_bounds(month)
        month_setups = [
            s for s in setups
            if normalize_setup_period(s.get("period")) == period
            and start <= pd.Timestamp(s["entry_time"]).tz_convert("UTC") <= end
        ]
        month_ann = filter_records_by_month(
            [a for a in annotations if normalize_setup_period(a.get("period")) == period and a.get("confirmed")],
            month,
            "bar_time",
        )
        payload.append({
            "month": month,
            "label": pd.Timestamp(f"{month}-01").strftime("%b %Y"),
            "setup_count": len(month_setups),
            "bar_tag_count": len(month_ann),
        })
    return {"period": period, "months": payload}


@app.get("/api/setups")
def list_setups(month: str | None = None, summary: bool = False, period: str | None = None):
    setups = load_setups()
    if period:
        period = resolve_period(period)
        setups = [s for s in setups if normalize_setup_period(s.get("period")) == period]
    if month:
        setups = filter_records_by_month(setups, month, "entry_time")
    if summary:
        bar_lookup = {a["id"]: a for a in load_bar_annotations()}
        return {
            "setups": [
                setup_summary(enrich_setup_quality(s, bar_lookup), bar_lookup=bar_lookup)
                for s in setups
            ],
            "month": month,
            "count": len(setups),
        }
    return {"setups": setups, "month": month, "count": len(setups)}


@app.post("/api/setups")
def add_setup(body: SetupIn):
    try:
        return create_setup(body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/setups/{setup_id}")
def patch_setup(setup_id: str, body: SetupPatch):
    try:
        return update_setup(setup_id, body.model_dump(exclude_none=True))
    except KeyError:
        raise HTTPException(404, "Setup not found")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/setups/{setup_id}")
def remove_setup(setup_id: str):
    delete_setup(setup_id)
    return {"deleted": setup_id}


@app.get("/api/tags/definitions")
def get_tag_definitions():
    return {"tags": tag_definitions()}


@app.get("/api/bar-annotations")
def list_bar_annotations(month: str | None = None, period: str | None = None, summary: bool = True):
    annotations = load_bar_annotations()
    if period:
        period = resolve_period(period)
        annotations = [a for a in annotations if normalize_setup_period(a.get("period")) == period]
    if month:
        annotations = filter_records_by_month(annotations, month, "bar_time")
    if summary:
        return {
            "annotations": [annotation_summary(a) for a in annotations],
            "month": month,
            "count": len(annotations),
        }
    return {"annotations": annotations, "month": month, "count": len(annotations)}


@app.post("/api/bar-annotations")
def save_bar_annotation(body: BarAnnotationIn):
    try:
        return upsert_annotation(body.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/bar-annotations/{annotation_id}")
def remove_bar_annotation(annotation_id: str):
    delete_annotation(annotation_id)
    return {"deleted": annotation_id}


@app.get("/api/bars/important")
def get_important_bars(
    period: str = "train_2022",
    month: str | None = None,
    min_score: float | None = None,
    with_tags: bool = True,
    max_bars: int | None = None,
):
    period = resolve_period(period)
    if not period_exists(period):
        raise HTTPException(400, f"Unknown period: {period}")
    try:
        return scan_important_bars(
            period,
            month=month,
            min_score=min_score,
            with_tags=with_tags,
            max_bars=max_bars,
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.get("/api/bars/inspect")
def inspect_bar(entry_time: str, entry_price: float | None = None):
    try:
        return inspect_bar_at_time(entry_time, entry_price=entry_price)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@app.post("/api/tags/suggest")
def suggest_tags(body: TagSuggestIn):
    try:
        detail = inspect_bar_at_time(body.entry_time, entry_price=body.entry_price)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    return {
        "features": detail.get("features"),
        "detected_tags": detail.get("detected_tags"),
        "suggested_tags": detail.get("suggested_tags"),
        "similar_setups": detail.get("similar_setups"),
        "suggested_direction": detail.get("suggested_direction"),
        "confidence": detail.get("confidence"),
        "cluster_win_rate": detail.get("cluster_win_rate"),
        "importance_score": (detail.get("importance") or {}).get("score"),
        "sequence_tags": detail.get("sequence_tags"),
        "context_bars": detail.get("sequence"),
        "bar_tags": detail.get("bar_tags"),
        "annotation": detail.get("annotation"),
    }


@app.post("/api/setups/curate")
def curate_setups(dry_run: bool = False):
    try:
        return apply_curation(dry_run=dry_run)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/setups/curate/preview")
def preview_curation():
    return curate_train_setups()


@app.post("/api/setups/refresh")
def refresh_setups():
    df = add_indicators(load_candles())
    setups = [enrich_setup(s, df) for s in load_setups()]
    from .labels import save_setups

    save_setups(setups)
    return {"setups": setups}


@app.get("/api/workflow")
def get_workflow(train_period: str | None = None, strategy_id: str | None = None):
    train_period = resolve_period(train_period) if train_period else None
    return workflow_status(train_period=train_period, strategy_id=strategy_id)


@app.get("/api/strategy-types")
def get_strategy_types():
    return {"strategies": list_strategy_types()}


@app.post("/api/analyze")
def analyze(
    optimize: bool = False,
    train_period: str | None = None,
    strategy_id: str | None = None,
    validation_period: str | None = None,
):
    train_period = resolve_period(train_period or default_train_period())
    if validation_period:
        validation_period = resolve_period(validation_period)
    if optimize:
        return analyze_and_optimize(
            train_period=train_period,
            strategy_id=strategy_id,
            validation_period=validation_period,
        )
    return analyze_patterns(train_period=train_period, strategy_id=strategy_id)


@app.post("/api/optimize")
def optimize(
    train_period: str | None = None,
    period: str | None = None,
    strategy_id: str | None = None,
):
    train_period = resolve_period(train_period) if train_period else None
    validation_period = resolve_period(period) if period else None
    return analyze_and_optimize(
        train_period=train_period,
        strategy_id=strategy_id,
        validation_period=validation_period,
    )


@app.get("/api/strategies")
def list_saved_strategies():
    items = list_strategies()
    return {"strategies": items, "count": len(items)}


@app.get("/api/strategy")
def strategy(train_period: str | None = None, strategy_id: str | None = None):
    train_period = resolve_period(train_period) if train_period else None
    s = load_strategy(train_period, strategy_id)
    if not s:
        raise HTTPException(404, "No strategy yet")
    return s


@app.patch("/api/strategy")
def patch_strategy(body: StrategyPatch):
    from .strategy_registry import resolve_strategy_id

    train_period = resolve_period(body.train_period)
    sid = resolve_strategy_id(body.strategy_id)
    current = load_strategy(train_period, sid)
    if not current:
        raise HTTPException(404, f"Chưa có chiến lược {sid} cho {train_period}. Chạy Analyze trước.")

    patch = body.model_dump(exclude_none=True, exclude={"train_period", "strategy_id"})
    for key, value in patch.items():
        if key == "bands" and isinstance(value, dict) and isinstance(current.get("bands"), dict):
            current["bands"] = {**current["bands"], **value}
        elif key == "risk" and isinstance(value, dict) and isinstance(current.get("risk"), dict):
            current["risk"] = {**current["risk"], **value}
        elif key == "setups" and isinstance(value, dict) and isinstance(current.get("setups"), dict):
            merged = dict(current["setups"])
            for setup_id, setup_patch in value.items():
                if isinstance(setup_patch, dict) and isinstance(merged.get(setup_id), dict):
                    merged[setup_id] = {**merged[setup_id], **setup_patch}
                else:
                    merged[setup_id] = setup_patch
            current["setups"] = merged
        else:
            current[key] = value

    path = save_strategy(current, train_period=train_period, strategy_id=sid)
    return {"status": "ok", "strategy": current, "path": str(path)}


@app.get("/api/backtests")
def get_backtests(period: str | None = None):
    return {"runs": list_runs(period=period)}


@app.get("/api/backtests/compare")
def get_backtest_compare(ids: str):
    run_ids = [x.strip() for x in ids.split(",") if x.strip()]
    if not run_ids:
        raise HTTPException(400, "Cần ít nhất 1 id")
    return compare_runs(run_ids)


@app.get("/api/backtests/{run_id}")
def get_backtest_run(run_id: str):
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, "Không tìm thấy backtest")
    return run


@app.post("/api/backtests")
def store_backtest(body: BacktestSaveIn):
    try:
        return save_run(body.result, name=body.name, period=body.period)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.patch("/api/backtests/{run_id}")
def patch_backtest_run(run_id: str, body: BacktestRenameIn):
    try:
        return rename_run(run_id, body.name)
    except KeyError:
        raise HTTPException(404, "Không tìm thấy backtest")
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/backtests/{run_id}")
def remove_backtest_run(run_id: str):
    delete_run(run_id)
    return {"deleted": run_id}


@app.post("/api/backtest")
def backtest(
    period: str | None = None,
    periods: str | None = None,
    train_period: str | None = None,
    strategy_id: str | None = None,
    name: str | None = None,
    save: bool = True,
):
    period_list = normalize_backtest_periods(periods or period)
    for pid in period_list:
        if not period_exists(pid):
            raise HTTPException(400, f"Unknown period: {pid}")
    strategy = None
    if train_period:
        train_period = resolve_period(train_period)
        strategy = load_strategy(train_period, strategy_id)
        if not strategy:
            sid_label = strategy_id or "mặc định"
            raise HTTPException(
                400,
                f"Chưa có chiến lược {sid_label} cho {train_period}. Chạy Analyze với năm train đó trước.",
            )
    result = run_backtest(periods=period_list, strategy=strategy)
    if strategy and result.get("status") == "ok" and result.get("metrics"):
        from datetime import datetime, timezone

        strategy["last_backtest"] = {
            **result["metrics"],
            "period": result.get("period"),
            "period_label": result.get("period_label"),
            "at": datetime.now(timezone.utc).isoformat(),
        }
        save_strategy(strategy, train_period=strategy.get("train_period"), strategy_id=strategy.get("strategy_id"))
    period_key = result.get("period") or ",".join(period_list)
    if save and result.get("status") == "ok":
        saved = save_run(result, name=name, period=period_key)
        return {**result, "saved_run": {"id": saved["id"], "name": saved["name"]}}
    return result


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
