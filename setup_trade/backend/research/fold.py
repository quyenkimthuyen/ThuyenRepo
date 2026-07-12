from __future__ import annotations

from typing import Any

from backend.core.config import DATA_DIR, save_json
from backend.core.folds import get_fold
from backend.data.labels import auto_label_period, label_status
from backend.data.loader import load_candles, slice_period
from backend.indicators import add_indicators
from backend.research.analyze import analyze_period
from backend.research.optimize import optimize_period
from backend.reports.html_report import render_backtest_html
from backend.simulator.backtest import run_backtest

RUNS_PATH = DATA_DIR / "runs" / "fold_runs.json"


def _load_runs() -> dict[str, Any]:
    if RUNS_PATH.exists():
        import json

        return json.loads(RUNS_PATH.read_text(encoding="utf-8"))
    return {"runs": []}


def _save_run(record: dict[str, Any]) -> None:
    store = _load_runs()
    store.setdefault("runs", []).append(record)
    save_json(RUNS_PATH, store)


def run_fold_step(fold_id: str, step: str, **kwargs: Any) -> dict[str, Any]:
    fold = get_fold(fold_id)
    label_period = fold["label_period"]
    optimize_period_name = fold["optimize_period"]
    final_period = fold["final_test_period"]

    if step == "label_status":
        return {"step": step, "fold_id": fold_id, **label_status(label_period)}

    if step == "auto_label":
        max_add = int(kwargs.get("max_add", 50))
        return {
            "step": step,
            "fold_id": fold_id,
            **auto_label_period(label_period, max_add=max_add),
        }

    if step == "analyze":
        apply_disable = bool(kwargs.get("apply_disable", False))
        return {
            "step": step,
            "fold_id": fold_id,
            **analyze_period(label_period, apply_disable=apply_disable),
        }

    if step == "optimize":
        method = str(kwargs.get("method", "greedy"))
        save_best = bool(kwargs.get("save_best", True))
        return {
            "step": step,
            "fold_id": fold_id,
            **optimize_period(optimize_period_name, method=method, save_best=save_best),
        }

    if step == "final_backtest":
        df = add_indicators(slice_period(load_candles(), final_period))
        result = run_backtest(df, final_period)
        html = render_backtest_html(result, title=f"Final test — {fold_id} — {final_period}")
        report_path = DATA_DIR / "runs" / f"{fold_id}_final_{final_period}.html"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(html, encoding="utf-8")
        record = {
            "fold_id": fold_id,
            "step": step,
            "period": final_period,
            "pass": result["pass"],
            "metrics": result["metrics"],
            "report": str(report_path),
        }
        _save_run(record)
        return {"step": step, "fold_id": fold_id, **result, "report_path": str(report_path)}

    if step == "full_pipeline":
        out: dict[str, Any] = {"fold_id": fold_id, "steps": {}}
        out["steps"]["label_status"] = label_status(label_period)
        if out["steps"]["label_status"]["count"] < out["steps"]["label_status"]["target"]:
            out["steps"]["auto_label"] = auto_label_period(label_period)
        out["steps"]["analyze"] = analyze_period(label_period, apply_disable=True)
        out["steps"]["optimize"] = optimize_period(optimize_period_name, save_best=True)
        out["steps"]["final_backtest"] = run_fold_step(fold_id, "final_backtest")
        return out

    raise ValueError(f"Unknown step: {step}")
