#!/usr/bin/env python3
"""Build Pareto table EUR/GBP × M15/M5 on canonical OOS 2026-01-01→2026-08-07."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent
OOS_FROM, OOS_TO = "2026-01-01", "2026-08-07"
OUT = REPO / "results_cross_oos_pareto.md"
OUT_JSON = REPO / "results_cross_oos_pareto.json"

DESKS = [
  ("M15", "EUR", REPO / "backtest/EdgeMinerEURUSDM15"),
  ("M15", "GBP", REPO / "backtest/EdgeMinerGBPUSDM15"),
  ("M5", "EUR", REPO / "backtestM5/EdgeMinerEURUSDM5"),
  ("M5", "GBP", REPO / "backtestM5/EdgeMinerGBPUSDM5"),
]


def load_rows():
  rows = []
  for tf, sym, root in DESKS:
    store = json.loads((root / "results/trade_models.json").read_text(encoding="utf-8"))
    for m in store.get("models") or []:
      if m.get("archived"):
        continue
      of = str(m.get("oos_from") or "")[:10]
      ot = str(m.get("oos_to") or "")[:10]
      if of != OOS_FROM or ot != OOS_TO:
        continue
      r = float(m.get("total_r") or 0)
      pf = float(m.get("profit_factor") or 0)
      dd = float(m.get("max_drawdown_r") or 1e9)
      wr = float(m.get("win_rate_pct") or 0)
      n = int(m.get("n_trades") or 0)
      r_dd = (r / dd) if dd > 1e-9 else None
      rows.append({
        "tf": tf, "symbol": sym, "desk": root.name,
        "label": m.get("label"), "id": m.get("id"),
        "oos_from": of, "oos_to": ot,
        "total_r": round(r, 3), "profit_factor": round(pf, 3),
        "win_rate_pct": round(wr, 2), "max_drawdown_r": round(dd, 3) if dd < 1e8 else None,
        "n_trades": n, "trades_per_week": m.get("trades_per_week"),
        "r_over_dd": round(r_dd, 3) if r_dd is not None else None,
      })
  return rows


def dominates(a, b) -> bool:
  """a dominates b on (max R, max PF, min DD). Strict on at least one."""
  better_or_eq = (
    a["total_r"] >= b["total_r"]
    and a["profit_factor"] >= b["profit_factor"]
    and (a["max_drawdown_r"] or 1e9) <= (b["max_drawdown_r"] or 1e9)
  )
  strictly = (
    a["total_r"] > b["total_r"]
    or a["profit_factor"] > b["profit_factor"]
    or (a["max_drawdown_r"] or 1e9) < (b["max_drawdown_r"] or 1e9)
  )
  return better_or_eq and strictly


def pareto_front(rows):
  front = []
  for a in rows:
    if any(dominates(b, a) for b in rows if b is not a):
      continue
    front.append(a)
  return front


def main():
  rows = load_rows()
  front = pareto_front(rows)
  front_ids = {r["id"] for r in front}
  rows_sorted = sorted(rows, key=lambda r: (-(r.get("r_over_dd") or -1e9), -(r["total_r"])))

  lines = [
    "# Cross Pareto — EUR/GBP × M15/M5",
    "",
    f"One measuring stick: OOS **`{OOS_FROM}` → `{OOS_TO}`** only.",
    "",
    "Objectives for Pareto: **max Total R**, **max PF**, **min MaxDD R**.",
    f"Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
    "",
    f"Live models on-window: **{len(rows)}** · Pareto front: **{len(front)}**",
    "",
    "## Pareto front",
    "",
    "| TF | Sym | Label | Total R | PF | WR% | MaxDD | R/DD | n |",
    "|----|-----|-------|---------|-----|-----|-------|------|---|",
  ]
  for r in sorted(front, key=lambda x: (-(x.get("r_over_dd") or 0), -x["total_r"])):
    lines.append(
      f"| {r['tf']} | {r['symbol']} | {r['label']} | {r['total_r']} | {r['profit_factor']} | "
      f"{r['win_rate_pct']} | {r['max_drawdown_r']} | {r['r_over_dd']} | {r['n_trades']} |"
    )

  lines += [
    "",
    "## All models (same OOS) — ranked by R/DD then Total R",
    "",
    "| Pareto | TF | Sym | Label | Total R | PF | WR% | MaxDD | R/DD | n | TPW |",
    "|--------|----|-----|-------|---------|-----|-----|-------|------|---|-----|",
  ]
  for r in rows_sorted:
    mark = "★" if r["id"] in front_ids else ""
    lines.append(
      f"| {mark} | {r['tf']} | {r['symbol']} | {r['label']} | {r['total_r']} | {r['profit_factor']} | "
      f"{r['win_rate_pct']} | {r['max_drawdown_r']} | {r['r_over_dd']} | {r['n_trades']} | {r['trades_per_week']} |"
    )

  # per cell best
  lines += ["", "## Best per cell (TF × Symbol)", ""]
  for tf in ("M15", "M5"):
    for sym in ("EUR", "GBP"):
      cell = [r for r in rows if r["tf"] == tf and r["symbol"] == sym]
      if not cell:
        lines.append(f"- **{tf} {sym}**: _(no on-window models)_")
        continue
      by_r = max(cell, key=lambda r: r["total_r"])
      by_pf = max(cell, key=lambda r: r["profit_factor"])
      by_q = max(cell, key=lambda r: r.get("r_over_dd") or -1e9)
      lines.append(
        f"- **{tf} {sym}**: maxR `{by_r['label']}` ({by_r['total_r']}R) · "
        f"maxPF `{by_pf['label']}` (PF {by_pf['profit_factor']}) · "
        f"best R/DD `{by_q['label']}` ({by_q['r_over_dd']})"
      )

  lines += [
    "",
    "## Read",
    "",
    "- ★ = on the 3-objective Pareto front (no other model beats it on R, PF, and DD simultaneously).",
    "- Prefer **R/DD** when choosing a single live book; use Pareto when comparing styles across TF/symbol.",
    "- M15 vs M5 density differs; same OOS removes date bias but not bar-capacity differences.",
    "",
  ]
  OUT.write_text("\n".join(lines), encoding="utf-8")
  OUT_JSON.write_text(json.dumps({
    "oos_from": OOS_FROM, "oos_to": OOS_TO,
    "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "pareto": front, "models": rows_sorted,
  }, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"Wrote {OUT} ({len(rows)} models, {len(front)} Pareto)")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
