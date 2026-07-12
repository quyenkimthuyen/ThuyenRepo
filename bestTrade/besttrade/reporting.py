"""Backtest report builder."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from besttrade.analytics import bootstrap_monte_carlo, monthly_breakdown, quarterly_breakdown
from besttrade.engine import STRATEGY_NAME, load_strategy_config, run_multi_year
from besttrade.params import locked_params, locked_risk
from besttrade.paths import BESTTRADE_ROOT


OUTPUT_DIR = BESTTRADE_ROOT / "output"


def _fmt_pct(v: float, signed: bool = True) -> str:
    return f"{v:+.1%}" if signed else f"{v:.1%}"


def _trade_row(t: Any) -> dict[str, Any]:
    return {
        "entry_time": str(t.entry_time)[:19],
        "exit_time": str(t.exit_time)[:19] if t.exit_time else "",
        "direction": "LONG" if t.direction == 1 else "SHORT",
        "entry_price": round(float(t.entry_price), 5),
        "exit_price": round(float(t.exit_price), 5) if t.exit_price else None,
        "sl_price": round(float(t.sl_price), 5),
        "tp_price": round(float(t.tp_price), 5),
        "pnl": round(float(t.pnl), 2),
        "result": t.result or "",
    }


def build_report(
    years: list[int],
    equity: float = 1000.0,
    sl_pct: float | None = None,
    min_rr: float | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    risk = locked_risk()
    sl = sl_pct if sl_pct is not None else risk["sl_pct"]
    rr = min_rr if min_rr is not None else risk["min_rr"]
    p = params or locked_params()
    cfg = load_strategy_config()

    results = run_multi_year(years, p, equity, sl, rr)

    all_trades = []
    year_rows = []
    total_pnl = 0.0
    total_trades = 0

    for r in results:
        m = r.metrics
        year_pnl = sum(t.pnl for t in r.trades)
        total_pnl += year_pnl
        total_trades += m.get("trade_count", 0)
        end_equity = equity + year_pnl
        year_rows.append({
            "year": r.year,
            "trade_count": m.get("trade_count", 0),
            "win_rate": m.get("win_rate", 0),
            "profit_factor": m.get("profit_factor", 0),
            "realized_rr": m.get("realized_rr", 0),
            "total_return": m.get("total_return", 0),
            "pnl_usd": round(year_pnl, 2),
            "end_equity": round(end_equity, 2),
            "trades": [_trade_row(t) for t in r.trades],
        })
        all_trades.extend(r.trades)

    wins = [t for t in all_trades if t.pnl > 0]
    losses = [t for t in all_trades if t.pnl <= 0]
    gp = sum(t.pnl for t in wins)
    gl = abs(sum(t.pnl for t in losses))
    combined_return = total_pnl / equity if equity else 0

    mc = bootstrap_monte_carlo(all_trades, equity, simulations=2000)
    months = monthly_breakdown(all_trades, equity)
    quarters = quarterly_breakdown(all_trades, equity)
    positive_months = sum(1 for m in months if float(m["PnL"]) > 0)
    monthly_stability = positive_months / len(months) if months else 0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": STRATEGY_NAME,
        "symbol": cfg.get("strategy", {}).get("symbol", "EURUSD"),
        "timeframe": cfg.get("strategy", {}).get("timeframe", "1h"),
        "years": years,
        "params": p,
        "risk": {"sl_pct": sl, "min_rr": rr, "equity": equity},
        "summary": {
            "total_trades": total_trades,
            "win_rate": len(wins) / len(all_trades) if all_trades else 0,
            "profit_factor": gp / gl if gl else 0,
            "realized_rr": (gp / len(wins)) / (gl / len(losses)) if wins and losses and gl else 0,
            "total_return": combined_return,
            "total_pnl_usd": round(total_pnl, 2),
            "end_equity": round(equity + total_pnl, 2),
            "gross_profit": round(gp, 2),
            "gross_loss": round(gl, 2),
            "avg_win": round(gp / len(wins), 2) if wins else 0,
            "avg_loss": round(gl / len(losses), 2) if losses else 0,
            "positive_years": sum(1 for y in year_rows if y["total_return"] > 0),
            "negative_years": sum(1 for y in year_rows if y["total_return"] < 0),
            "monthly_stability": monthly_stability,
        },
        "monte_carlo": mc,
        "by_year": year_rows,
        "monthly": months,
        "quarterly": quarters,
    }


def format_text_report(report: dict[str, Any]) -> str:
    s = report["summary"]
    risk = report["risk"]
    lines = [
        "=" * 72,
        "  BESTTRADE BACKTEST REPORT — Pin Bar Elite",
        "=" * 72,
        f"  Generated : {report['generated_at'][:19]} UTC",
        f"  Symbol    : {report['symbol']} {report['timeframe']}",
        f"  Years     : {report['years'][0]} – {report['years'][-1]}",
        f"  Equity    : ${risk['equity']:,.0f}  |  Risk: {risk['sl_pct']*100:.1f}%/lệnh  |  RR: {risk['min_rr']:.1f}",
        "",
        "─" * 72,
        "  TỔNG HỢP",
        "─" * 72,
        f"  Tổng lệnh      : {s['total_trades']}",
        f"  Win rate       : {s['win_rate']:.1%}",
        f"  Profit factor  : {s['profit_factor']:.2f}",
        f"  Realized RR    : {s['realized_rr']:.2f}R",
        f"  Tổng return    : {_fmt_pct(s['total_return'])}",
        f"  Tổng PnL       : ${s['total_pnl_usd']:+,.2f}",
        f"  Vốn cuối       : ${s['end_equity']:,.2f}",
        f"  Năm dương/âm   : {s['positive_years']}/{s['negative_years']}",
        f"  Monthly stab.  : {s['monthly_stability']:.0%}",
        "",
        "─" * 72,
        "  THEO NĂM",
        "─" * 72,
        f"  {'Năm':<6} {'Lệnh':>5} {'WR':>7} {'PF':>6} {'Return':>9} {'PnL $':>10}",
    ]
    for y in report["by_year"]:
        lines.append(
            f"  {y['year']:<6} {y['trade_count']:>5} {y['win_rate']:>6.0%} "
            f"{y['profit_factor']:>6.2f} {_fmt_pct(y['total_return']):>9} {y['pnl_usd']:>+10.2f}"
        )

    lines += [
        "",
        "─" * 72,
        "  MONTE CARLO",
        "─" * 72,
    ]
    mc = report["monte_carlo"]
    lines += [
        f"  Simulations    : {mc.get('simulations', 0)}",
        f"  % dương        : {mc.get('positive_pct', 0):.0%}",
        f"  Return median  : {_fmt_pct(mc.get('median_return', 0))}",
        f"  P5 / P95       : {_fmt_pct(mc.get('p5_return', 0))} / {_fmt_pct(mc.get('p95_return', 0))}",
        f"  Verdict        : {mc.get('verdict', '')}",
        "",
        "─" * 72,
        "  THEO THÁNG",
        "─" * 72,
        f"  {'Tháng':<10} {'Lệnh':>5} {'WR':>6} {'PnL':>10} {'Return':>9}",
    ]
    for m in report["monthly"]:
        lines.append(
            f"  {m['Tháng']:<10} {m['Lệnh']:>5} {m['WR']:>6} {m['PnL']:>10.2f} {m['Return']:>9}"
        )

    lines += [
        "",
        "─" * 72,
        "  CHI TIẾT LỆNH",
        "─" * 72,
    ]
    for y in report["by_year"]:
        lines.append(f"\n  [{y['year']}]")
        if not y["trades"]:
            lines.append("    (không có lệnh)")
            continue
        for i, t in enumerate(y["trades"], 1):
            lines.append(
                f"    {i:2d}. {t['entry_time']} {t['direction']:<5} "
                f"PnL {t['pnl']:+.2f}  {t['result']}  "
                f"entry {t['entry_price']:.5f} → exit {t['exit_price']}"
            )

    lines += ["", "=" * 72]
    return "\n".join(lines)


def save_report(
    report: dict[str, Any],
    output_dir: Path | None = None,
    prefix: str = "backtest_report",
) -> dict[str, Path]:
    import json

    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    y0, y1 = report["years"][0], report["years"][-1]
    stem = f"{prefix}_{y0}_{y1}"

    json_path = out_dir / f"{stem}.json"
    txt_path = out_dir / f"{stem}.txt"
    md_path = out_dir / f"{stem}.md"

    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    txt_path.write_text(format_text_report(report), encoding="utf-8")
    md_path.write_text(format_markdown_report(report), encoding="utf-8")

    return {"json": json_path, "txt": txt_path, "md": md_path}


def format_markdown_report(report: dict[str, Any]) -> str:
    s = report["summary"]
    risk = report["risk"]
    lines = [
        f"# BestTrade Backtest Report — {report['strategy']}",
        "",
        f"- **Generated:** {report['generated_at'][:19]} UTC",
        f"- **Symbol:** {report['symbol']} {report['timeframe']}",
        f"- **Period:** {report['years'][0]} – {report['years'][-1]}",
        f"- **Equity:** ${risk['equity']:,.0f} | Risk {risk['sl_pct']*100:.1f}% | RR {risk['min_rr']:.1f}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total trades | {s['total_trades']} |",
        f"| Win rate | {s['win_rate']:.1%} |",
        f"| Profit factor | {s['profit_factor']:.2f} |",
        f"| Total return | {_fmt_pct(s['total_return'])} |",
        f"| Total PnL | ${s['total_pnl_usd']:+,.2f} |",
        f"| End equity | ${s['end_equity']:,.2f} |",
        f"| Monthly stability | {s['monthly_stability']:.0%} |",
        "",
        "## By Year",
        "",
        "| Year | Trades | WR | PF | Return | PnL |",
        "|------|--------|-----|-----|--------|-----|",
    ]
    for y in report["by_year"]:
        lines.append(
            f"| {y['year']} | {y['trade_count']} | {y['win_rate']:.0%} | "
            f"{y['profit_factor']:.2f} | {_fmt_pct(y['total_return'])} | ${y['pnl_usd']:+,.2f} |"
        )

    mc = report["monte_carlo"]
    lines += [
        "",
        "## Monte Carlo",
        "",
        f"- Positive simulations: **{mc.get('positive_pct', 0):.0%}**",
        f"- Median return: **{_fmt_pct(mc.get('median_return', 0))}**",
        f"- {mc.get('verdict', '')}",
        "",
        "## Monthly",
        "",
        "| Month | Trades | WR | PnL | Return |",
        "|-------|--------|-----|-----|--------|",
    ]
    for m in report["monthly"]:
        lines.append(f"| {m['Tháng']} | {m['Lệnh']} | {m['WR']} | {m['PnL']} | {m['Return']} |")

    lines += ["", "## Trades by Year", ""]
    for y in report["by_year"]:
        lines.append(f"### {y['year']} ({y['trade_count']} trades)")
        if not y["trades"]:
            lines.append("_No trades_")
            continue
        lines.append("")
        lines.append("| # | Entry | Dir | PnL | Result |")
        lines.append("|---|-------|-----|-----|--------|")
        for i, t in enumerate(y["trades"], 1):
            lines.append(
                f"| {i} | {t['entry_time']} | {t['direction']} | {t['pnl']:+.2f} | {t['result']} |"
            )
        lines.append("")

    return "\n".join(lines)
