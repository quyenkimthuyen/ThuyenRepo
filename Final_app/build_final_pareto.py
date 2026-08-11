#!/usr/bin/env python3
"""Pareto + validation report for Final_app (same OOS as GUIDE)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

FINAL = Path(__file__).resolve().parent
OOS_FROM, OOS_TO = "2026-01-01", "2026-08-07"
OUT_MD = FINAL / "results_final_guide_validation.md"
OUT_JSON = FINAL / "results_final_guide_validation.json"

DESKS = [
  ("M15", "EUR", FINAL / "EdgeMinerEURUSDM15"),
  ("M15", "GBP", FINAL / "EdgeMinerGBPUSDM15"),
  ("M5", "EUR", FINAL / "EdgeMinerEURUSDM5"),
  ("M5", "GBP", FINAL / "EdgeMinerGBPUSDM5"),
]


def load_rows():
  rows = []
  for tf, sym, root in DESKS:
    p = root / "results/trade_models.json"
    if not p.exists():
      continue
    store = json.loads(p.read_text(encoding="utf-8"))
    for m in store.get("models") or []:
      if m.get("archived"):
        continue
      of, ot = str(m.get("oos_from") or "")[:10], str(m.get("oos_to") or "")[:10]
      if of != OOS_FROM or ot != OOS_TO:
        continue
      r = float(m.get("total_r") or 0)
      pf = float(m.get("profit_factor") or 0)
      dd = float(m.get("max_drawdown_r") or 1e9)
      wr = float(m.get("win_rate_pct") or 0)
      r_dd = (r / dd) if dd > 1e-9 else None
      rows.append({
        "tf": tf, "symbol": sym, "desk": root.name,
        "label": m.get("label"), "id": m.get("id"),
        "total_r": round(r, 3), "profit_factor": round(pf, 3),
        "win_rate_pct": round(wr, 2), "max_drawdown_r": None if dd > 1e8 else round(dd, 3),
        "n_trades": m.get("n_trades"), "r_over_dd": None if r_dd is None else round(r_dd, 3),
        "kb_profile": m.get("kb_profile"), "train_weeks": m.get("train_weeks"),
      })
  return rows


def dominates(a, b) -> bool:
  better = (
    a["total_r"] >= b["total_r"]
    and a["profit_factor"] >= b["profit_factor"]
    and (a["max_drawdown_r"] or 1e9) <= (b["max_drawdown_r"] or 1e9)
  )
  strict = (
    a["total_r"] > b["total_r"]
    or a["profit_factor"] > b["profit_factor"]
    or (a["max_drawdown_r"] or 1e9) < (b["max_drawdown_r"] or 1e9)
  )
  return better and strict


def main() -> int:
  rows = load_rows()
  front = [a for a in rows if not any(dominates(b, a) for b in rows if b is not a)]
  front_ids = {r["id"] for r in front}
  ranked = sorted(rows, key=lambda r: (-(r.get("r_over_dd") or -1e9), -r["total_r"]))

  lines = [
    "# Final_app — GUIDE validation (from-scratch train)",
    "",
    f"OOS **`{OOS_FROM}` → `{OOS_TO}`** · generated {datetime.now().astimezone().isoformat(timespec='seconds')}",
    "",
    "Playbook: `GUIDE_TRAIN_TRADE_MODELS.md`",
    f"Live models on-window: **{len(rows)}** · Pareto ★: **{len(front)}**",
    "",
    "## Best per cell (TF × Symbol)",
    "",
  ]
  for tf in ("M15", "M5"):
    for sym in ("EUR", "GBP"):
      cell = [r for r in rows if r["tf"] == tf and r["symbol"] == sym]
      if not cell:
        lines.append(f"- **{tf} {sym}**: _(chưa có model — train chưa xong)_")
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
    "## All models (R/DD rank)",
    "",
    "| ★ | TF | Sym | Label | R | PF | WR | DD | R/DD | n | KB |",
    "|---|----|-----|-------|---|----|----|----|------|---|----|",
  ]
  for r in ranked:
    mark = "★" if r["id"] in front_ids else ""
    lines.append(
      f"| {mark} | {r['tf']} | {r['symbol']} | {r['label']} | {r['total_r']} | {r['profit_factor']} | "
      f"{r['win_rate_pct']} | {r['max_drawdown_r']} | {r['r_over_dd']} | {r['n_trades']} | {r['kb_profile']} |"
    )

  lines += [
    "",
    "## Kỳ vọng GUIDE (qualitative)",
    "",
    "1. Cùng OOS → so sánh EUR/GBP × M15/M5 hợp lệ.",
    "2. M15 EUR thường PF/WR/R/DD cao hơn, ít lệnh hơn M5.",
    "3. M5 thường Total R / mật độ cao hơn; BestQuality R/DD cạnh tranh.",
    "4. GBP frontier khác EUR (spread/noise) — không copy genome.",
    "5. Objective `quality` → active nên nghiêng BestQuality/Balance chứ không chỉ BestTotalR.",
    "",
  ]
  OUT_MD.write_text("\n".join(lines), encoding="utf-8")
  OUT_JSON.write_text(json.dumps({"oos_from": OOS_FROM, "oos_to": OOS_TO, "pareto": front, "models": ranked}, indent=2), encoding="utf-8")
  print(f"Wrote {OUT_MD} ({len(rows)} models)")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
