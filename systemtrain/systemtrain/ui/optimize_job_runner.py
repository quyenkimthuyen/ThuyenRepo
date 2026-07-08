from __future__ import annotations

import argparse
from typing import Any

from systemtrain.ui.optimize_jobs import _now, read_job, write_job
from systemtrain.ui.services import optimize_train_year_candidate, run_all_strategies_backtest, save_params_for_train_year


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    avg = _avg(values)
    return (sum((value - avg) ** 2 for value in values) / len(values)) ** 0.5


def _combined_return(results: dict[str, dict[str, Any]]) -> float:
    return sum(float(item.get("metrics", {}).get("total_return", 0)) for item in results.values())


def _score(avg_ret: float, worst_ret: float, volatility: float, negative_years: int, avg_pf: float, avg_wr: float) -> float:
    raw = (
        50
        + avg_ret * 120
        + worst_ret * 80
        - volatility * 70
        - negative_years * 8
        + min(avg_pf, 2.5) * 7
        + avg_wr * 10
    )
    return max(0.0, min(100.0, raw))


def _score_candidate(results_by_year: dict[int, dict[str, dict[str, Any]]]) -> dict[str, float]:
    returns = [_combined_return(results) for results in results_by_year.values()]
    strategy_metrics = [
        payload.get("metrics", {})
        for results in results_by_year.values()
        for payload in results.values()
    ]
    avg_pf = _avg([float(m.get("profit_factor", 0)) for m in strategy_metrics])
    avg_wr = _avg([float(m.get("win_rate", 0)) for m in strategy_metrics])
    volatility = _std(returns)
    negative_years = sum(1 for value in returns if value < 0)
    avg_return = _avg(returns)
    worst_return = min(returns) if returns else 0.0
    return {
        "score": _score(avg_return, worst_return, volatility, negative_years, avg_pf, avg_wr),
        "avg_return": avg_return,
        "worst_return": worst_return,
        "volatility": volatility,
        "negative_years": float(negative_years),
        "avg_pf": avg_pf,
        "avg_wr": avg_wr,
    }


def _metrics_only(results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: payload.get("metrics", {})
        for name, payload in results.items()
    }


def _update(job: dict[str, Any], **updates: Any) -> None:
    job.update(updates)
    job["updated_at"] = _now()
    write_job(job)


def run(job_id: str) -> None:
    job = read_job(job_id)
    if not job:
        raise SystemExit(f"Job not found: {job_id}")

    try:
        _update(job, status="running", message="Đang chạy optimize")
        progress = int(job.get("progress", 0))
        all_results = []
        train_years = [int(y) for y in job["train_years"]]
        trade_years = [int(y) for y in job["trade_years"]]
        runs = int(job.get("advanced_runs", 1))
        equity = float(job["equity"])
        sl_pct = float(job["sl_pct"])
        min_rr = float(job.get("min_rr", 2.0))

        for train_year in train_years:
            candidates = []
            for run_idx in range(1, runs + 1):
                _update(job, message=f"Train {train_year} · candidate {run_idx}/{runs}")
                state = optimize_train_year_candidate(train_year, equity=equity, sl_pct=sl_pct, min_rr=min_rr)
                results_by_year = {}
                metrics_by_year = {}
                for trade_year in trade_years:
                    results, _ = run_all_strategies_backtest(state, trade_year, equity, sl_pct=sl_pct, min_rr=min_rr)
                    results_by_year[trade_year] = results
                    metrics_by_year[str(trade_year)] = {
                        "combined_return": _combined_return(results),
                        "strategies": _metrics_only(results),
                    }
                score = _score_candidate(results_by_year)
                candidates.append((score["score"], state, score, metrics_by_year))
                progress += 1
                _update(job, progress=progress)

            candidates.sort(key=lambda item: item[0], reverse=True)
            _, best_state, best_score, best_metrics = candidates[0]
            save_params_for_train_year(best_state, train_year, set_active=False)
            all_results.append({
                "train_year": train_year,
                "saved": True,
                "score": best_score,
                "trade_years": best_metrics,
            })
            _update(job, results=all_results, message=f"Đã lưu config train {train_year}")

        _update(job, status="completed", progress=job["total"], message="Hoàn tất")
    except Exception as exc:
        _update(job, status="failed", message=str(exc), error=repr(exc))
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    run(args.job_id)


if __name__ == "__main__":
    main()
