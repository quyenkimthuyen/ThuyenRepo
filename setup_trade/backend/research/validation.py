from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.core.config import DATA_DIR, PERIODS_PATH, load_json, save_json
from backend.core.folds import get_fold
from backend.data.loader import load_candles, slice_period
from backend.indicators import add_indicators
from backend.reports.html_report import render_backtest_html
from backend.research.analyze import analyze_period
from backend.research.optimize import optimize_period
from backend.simulator.backtest import run_backtest

VALIDATION_PATH = DATA_DIR / "runs" / "validations.json"
PASS_CRITERIA = load_json(PERIODS_PATH).get("pass_criteria") or {}


def _check_pass(metrics: dict[str, Any], mc: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "min_trades": metrics.get("trades", 0) >= int(PASS_CRITERIA.get("min_trades", 30)),
        "profit_factor": metrics.get("profit_factor", 0) >= float(PASS_CRITERIA.get("min_profit_factor", 1.3)),
        "max_drawdown": metrics.get("max_drawdown_pips", 999) <= float(PASS_CRITERIA.get("max_drawdown_pips", 250)),
        "expectancy": metrics.get("expectancy_pips", 0) > float(PASS_CRITERIA.get("min_expectancy_pips", 0)),
        "monte_carlo_pf_p5": mc.get("pf_p5", 0) >= float(PASS_CRITERIA.get("monte_carlo_pf_p5_min", 1.0)),
    }
    return {"pass": all(checks.values()), "checks": checks}


def _phase_summary(result: dict[str, Any], *, label: str) -> dict[str, Any]:
    m = result.get("metrics") or {}
    mc = result.get("monte_carlo") or {}
    verdict = _check_pass(m, mc)
    return {
        "label": label,
        "period": result.get("period"),
        "trades": m.get("trades", 0),
        "win_rate": m.get("win_rate", 0),
        "profit_factor": m.get("profit_factor", 0),
        "expectancy_pips": m.get("expectancy_pips", 0),
        "total_pips": m.get("total_pips", 0),
        "max_drawdown_pips": m.get("max_drawdown_pips", 0),
        "monte_carlo": mc,
        "pass": verdict["pass"],
        "checks": verdict["checks"],
        "by_setup": m.get("by_setup", {}),
    }


def run_walk_forward_validation(
    fold_id: str,
    *,
    skip_optimize: bool = False,
    save_strategy: bool = True,
) -> dict[str, Any]:
    fold = get_fold(fold_id)
    label_period = fold["label_period"]
    optimize_period = fold["optimize_period"]
    final_period = fold["final_test_period"]

    analyze = analyze_period(label_period, apply_disable=True)

    best_params = None
    if not skip_optimize:
        opt_meta = optimize_period(optimize_period, method="greedy", save_best=save_strategy)
        best_params = opt_meta.get("best_params")
    else:
        opt_meta = {"skipped": True}

    df_opt = add_indicators(slice_period(load_candles(), optimize_period))
    in_sample_bt = run_backtest(df_opt, optimize_period)

    df_final = add_indicators(slice_period(load_candles(), final_period))
    final_result = run_backtest(df_final, final_period)

    in_sample = _phase_summary(in_sample_bt, label="In-sample (optimize year)")
    out_of_sample = _phase_summary(final_result, label="Out-of-sample (final year — chưa optimize)")

    oos_pass = out_of_sample["pass"]
    is_pass = in_sample["pass"]
    effective = oos_pass and is_pass

    warnings: list[str] = []
    if not is_pass:
        warnings.append("In-sample (năm optimize) chưa đạt PASS")
    if in_sample["trades"] < 30:
        warnings.append(f"In-sample chỉ {in_sample['trades']} lệnh — mẫu nhỏ, dễ overfit")
    if not oos_pass:
        warnings.append("OOS FAIL — chưa chứng minh edge trên dữ liệu chưa thấy")
    if out_of_sample["trades"] < 30:
        warnings.append(f"OOS chỉ {out_of_sample['trades']} lệnh — chưa đủ ý nghĩa thống kê")

    verdict_text = "CÓ EDGE (OOS PASS)" if effective else "CHƯA CÓ EDGE ĐÁNG TIN (OOS FAIL)"

    report_html = _render_validation_html(fold_id, fold, analyze, in_sample, out_of_sample, warnings, verdict_text)
    report_path = DATA_DIR / "runs" / f"{fold_id}_validation.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_html, encoding="utf-8")

    final_html_path = DATA_DIR / "runs" / f"{fold_id}_final_{final_period}.html"
    final_html_path.write_text(
        render_backtest_html(final_result, title=f"OOS Final — {fold_id} — {final_period}"),
        encoding="utf-8",
    )

    record = {
        "fold_id": fold_id,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "fold": fold,
        "analyze_summary": {
            "label_count": analyze.get("label_count"),
            "alignment_ratio": analyze.get("alignment", {}).get("alignment_ratio"),
            "target_met": analyze.get("target_met"),
        },
        "optimize_meta": opt_meta,
        "best_params": best_params,
        "in_sample": in_sample,
        "out_of_sample": out_of_sample,
        "verdict": verdict_text,
        "effective": effective,
        "warnings": warnings,
        "report_path": str(report_path),
        "final_report_path": str(final_html_path),
    }
    _save_validation(record)
    return record


def _save_validation(record: dict[str, Any]) -> None:
    store: dict[str, Any] = {"validations": []}
    if VALIDATION_PATH.exists():
        store = load_json(VALIDATION_PATH)
    store.setdefault("validations", []).append(record)
    save_json(VALIDATION_PATH, store)


def get_latest_validation(fold_id: str) -> dict[str, Any] | None:
    if not VALIDATION_PATH.exists():
        return None
    store = load_json(VALIDATION_PATH)
    matches = [v for v in store.get("validations", []) if v.get("fold_id") == fold_id]
    return matches[-1] if matches else None


def _render_validation_html(
    fold_id: str,
    fold: dict[str, Any],
    analyze: dict[str, Any],
    in_sample: dict[str, Any],
    oos: dict[str, Any],
    warnings: list[str],
    verdict: str,
) -> str:
    import html as html_lib

    def row(phase: dict[str, Any]) -> str:
        chk = phase.get("checks") or {}
        chk_str = ", ".join(f"{k}: {'OK' if v else 'X'}" for k, v in chk.items())
        return f"""<tr>
          <td>{html_lib.escape(phase['label'])}</td>
          <td>{html_lib.escape(str(phase['period']))}</td>
          <td>{phase['trades']}</td>
          <td>{phase['win_rate']:.1%}</td>
          <td>{phase['profit_factor']}</td>
          <td>{phase['expectancy_pips']}</td>
          <td>{phase['total_pips']}</td>
          <td>{phase['max_drawdown_pips']}</td>
          <td>{'PASS' if phase['pass'] else 'FAIL'}</td>
          <td><small>{html_lib.escape(chk_str)}</small></td>
        </tr>"""

    warn_html = "".join(f"<li>{html_lib.escape(w)}</li>" for w in warnings)
    align = analyze.get("alignment", {})

    return f"""<!DOCTYPE html>
<html lang="vi"><head><meta charset="UTF-8"/><title>Validation {fold_id}</title>
<style>
  body {{ font-family: system-ui; margin: 2rem; background: #0f1419; color: #e7ecf3; }}
  .verdict {{ font-size: 1.3rem; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
  .pass {{ background: #1a3d2e; color: #3ecf8e; }}
  .fail {{ background: #3d1a1a; color: #ff6b6b; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ border: 1px solid #2a3548; padding: 0.5rem; text-align: left; }}
  th {{ background: #1a2332; }}
</style></head><body>
  <h1>Walk-forward — {html_lib.escape(fold_id)}</h1>
  <p>Label {fold['label_year']} → Optimize {fold['optimize_year']} → Final {fold['final_test_year']}</p>
  <div class="verdict {'pass' if oos['pass'] else 'fail'}">{html_lib.escape(verdict)}</div>
  <h2>In-sample vs OOS</h2>
  <table>
    <tr><th>Phase</th><th>Period</th><th>Trades</th><th>WR</th><th>PF</th><th>Exp</th><th>Total</th><th>MaxDD</th><th>Verdict</th><th>Checks</th></tr>
    {row(in_sample)}
    {row(oos)}
  </table>
  <h2>Labels</h2>
  <p>{analyze.get('label_count', 0)} / {analyze.get('target_setups', 50)} · alignment {align.get('alignment_ratio', 0):.1%}</p>
  <h2>Cảnh báo</h2>
  <ul>{warn_html or '<li>—</li>'}</ul>
</body></html>"""
