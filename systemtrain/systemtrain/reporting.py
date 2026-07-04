"""Format and print detailed strategy backtest reports."""

from __future__ import annotations

from typing import Any


def format_metrics(metrics: dict[str, Any]) -> str:
    return (
        f"WR={metrics.get('win_rate', 0):.1%}  "
        f"PF={metrics.get('profit_factor', 0):.2f}  "
        f"RR={metrics.get('realized_rr', 0):.2f}  "
        f"DD={metrics.get('max_drawdown', 0):.1%}  "
        f"trades={metrics.get('trade_count', 0)}  "
        f"return={metrics.get('total_return', 0):.1%}  "
        f"stab={metrics.get('monthly_stability', 0):.1%}"
    )


def print_strategy_report(results: list[dict[str, Any]], title: str = "Strategy Report") -> None:
    print(f"\n{'=' * 72}")
    print(f"  {title}")
    print(f"{'=' * 72}")
    print(f"  Total strategies: {len(results)}")
    passed = [r for r in results if r.get("passed")]
    print(f"  Passed OOS gate:  {len(passed)}")
    print(f"{'=' * 72}\n")

    for i, r in enumerate(results, 1):
        rank = r.get("rank_order", i)
        status = "PASS" if r.get("passed") else "FAIL"
        print(f"[{rank}]  |  {status}  |  fitness={r.get('fitness', 0):.3f}")
        print(f"    TRAIN : {format_metrics(r.get('train_metrics', {}))}")
        print(f"    OOS   : {format_metrics(r.get('oos_metrics', {}))}")
        mc = r.get("monte_carlo", {})
        if mc:
            print(
                f"    MC    : positive={mc.get('positive_pct', 0):.1%}  "
                f"median_return={mc.get('median_return', 0):.1%}  "
                f"p5={mc.get('p5_return', 0):.1%}"
            )
        wf = r.get("wf_summary", {})
        if wf and wf.get("folds_total", 0) > 0:
            print(
                f"    WF    : folds_passed={wf.get('folds_passed', 0)}/{wf.get('folds_total', 0)}  "
                f"avg_WR={wf.get('avg_win_rate', 0):.1%}"
            )
        reasons = r.get("verdict_reasons", [])
        if reasons:
            print(f"    Verdict: {', '.join(reasons)}")
        print()

    if results:
        print(f"{'-' * 72}")
        print("  SUMMARY TABLE")
        print(f"{'-' * 72}")
        header = f"{'#':>3} {'Status':>6} {'WR_train':>9} {'WR_oos':>8} {'PF_oos':>7} {'DD_oos':>8} {'Trades':>7}"
        print(header)
        print("-" * 72)
        for i, r in enumerate(results, 1):
            tm = r.get("train_metrics", {})
            om = r.get("oos_metrics", {})
            status = "PASS" if r.get("passed") else "FAIL"
            print(
                f"{i:>3} {status:>6} "
                f"{tm.get('win_rate', 0):>8.1%} "
                f"{om.get('win_rate', 0):>8.1%} "
                f"{om.get('profit_factor', 0):>7.2f} "
                f"{om.get('max_drawdown', 0):>7.1%} "
                f"{om.get('trade_count', 0):>7}"
            )
        print(f"{'=' * 72}\n")


def summary_dict(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [r for r in results if r.get("passed")]
    oos_wrs = [r["oos_metrics"]["win_rate"] for r in results if r.get("oos_metrics")]
    return {
        "total": len(results),
        "passed": len(passed),
        "best_oos_wr": max(oos_wrs) if oos_wrs else 0.0,
        "avg_oos_wr": sum(oos_wrs) / len(oos_wrs) if oos_wrs else 0.0,
    }
