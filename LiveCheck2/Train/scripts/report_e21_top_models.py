#!/usr/bin/env python3
"""Rank e21 trade models and grid rows by Total R against the live bar.

Reads runtime/e21/results/trade_models.json plus every grid_search/gs_*.json so
the best books found so far can be compared in one table, with the WR>55 /
RR>2.5 / R>100 bar applied per row.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNTIME = Path(__file__).resolve().parent.parent / "runtime" / "e21" / "results"
BAR = {"wr": 54.99, "rr": 2.5, "r": 100.0}


def _f(value) -> float:
  try:
    return float(value)
  except (TypeError, ValueError):
    return 0.0


def _verdict(wr: float, rr: float, r: float) -> str:
  miss = []
  if wr <= BAR["wr"]:
    miss.append("WR")
  if rr <= BAR["rr"]:
    miss.append("RR")
  if r <= BAR["r"]:
    miss.append("R")
  return "ĐẠT" if not miss else "thiếu " + "+".join(miss)


def main() -> int:
  models_path = RUNTIME / "trade_models.json"
  if models_path.exists():
    raw = json.loads(models_path.read_text(encoding="utf-8"))
    models = raw.get("models") if isinstance(raw, dict) else raw
    models = models or []
    print(f"=== Trade Models đã promote ({len(models)}) ===")
    rows = []
    for m in models:
      oos = m.get("oos") or m.get("metrics") or {}
      rows.append((
        _f(oos.get("total_r")), _f(oos.get("win_rate_pct")), _f(oos.get("avg_rr")),
        int(_f(oos.get("n_trades"))), m.get("id") or "?",
        m.get("mining_preset") or (m.get("space") or {}).get("_preset") or "?",
        m.get("status") or m.get("state") or "",
        f"{oos.get('oos_from', '?')}→{oos.get('oos_to', '?')}",
      ))
    for r, wr, rr, n, mid, preset, status, window in sorted(rows, reverse=True):
      print(
        f"  R={r:7.1f} WR={wr:5.1f} RR={rr:5.2f} n={n:4d} · {_verdict(wr, rr, r):<14} "
        f"· {preset:<22} {status:<8} {window} · {mid}"
      )
    if not rows:
      print("  (chưa có model nào được promote)")
  else:
    print("=== Trade Models: chưa có file trade_models.json ===")

  runs = sorted((RUNTIME / "grid_search").glob("gs_*.json"))
  all_rows: list[tuple] = []
  for path in runs:
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data.get("rows") or []:
      if row.get("error"):
        continue
      all_rows.append((
        _f(row.get("total_r")), _f(row.get("win_rate_pct")), _f(row.get("avg_rr")),
        int(_f(row.get("n_trades"))), _f(row.get("max_drawdown_r")),
        str(row.get("mining_preset") or "?"), str(row.get("label") or ""),
        path.stem,
      ))

  print(f"\n=== Top 15 Total R trên {len(runs)} lần grid ({len(all_rows)} combo) ===")
  for r, wr, rr, n, dd, preset, label, run in sorted(all_rows, reverse=True)[:15]:
    print(
      f"  R={r:7.1f} WR={wr:5.1f} RR={rr:5.2f} n={n:4d} DD={dd:5.1f} "
      f"· {_verdict(wr, rr, r):<14} · {preset:<20} · {run} · {label[:60]}"
    )

  passing = [x for x in all_rows if _verdict(x[1], x[2], x[0]) == "ĐẠT"]
  print(f"\nSố combo đạt cả 3 tiêu chí WR>55 / RR>2.5 / R>100: {len(passing)}")

  qual = [x for x in all_rows if x[1] > BAR["wr"] and x[2] > BAR["rr"]]
  print(f"Số combo đạt WR>55 và RR>2.5 (bất kể R): {len(qual)}")
  for r, wr, rr, n, dd, preset, label, run in sorted(qual, reverse=True)[:8]:
    print(
      f"  R={r:7.1f} WR={wr:5.1f} RR={rr:5.2f} n={n:4d} "
      f"· {preset:<20} · {run} · {label[:60]}"
    )
  if qual:
    best_ev = max((x[0] / max(x[3], 1), x) for x in qual)[1]
    ev = best_ev[0] / max(best_ev[3], 1)
    print(
      f"\nEV/lệnh cao nhất trong nhóm đạt WR+RR: {ev:.2f}R "
      f"→ cần n≈{int(BAR['r'] / max(ev, 0.01)) + 1} lệnh để vượt R>100 "
      f"(hiện n={best_ev[3]})"
    )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
