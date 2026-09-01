#!/usr/bin/env python3
"""Decompose e21 Total R into n x EV to see which lever actually moves it.

Total R = n_trades x EV_per_trade. The live bar (WR>55 / RR>2.5 / R>100) has been
missed on every grid so far, so this reports where each combo sits on both axes
and whether EV decays as fill rate rises — that decay is what decides if Total R
can be bought with volume or needs a better entry.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUNS = Path(__file__).resolve().parent.parent / "runtime" / "e21" / "results" / "grid_search"


def _f(value) -> float:
  try:
    return float(value)
  except (TypeError, ValueError):
    return 0.0


def _load() -> list[dict]:
  rows: list[dict] = []
  seen: set[tuple] = set()
  for path in sorted(RUNS.glob("gs_*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data.get("rows") or []:
      if row.get("error"):
        continue
      n = int(_f(row.get("n_trades")))
      if n <= 0:
        continue
      key = (
        str(row.get("mining_preset")), str(row.get("label")),
        n, round(_f(row.get("total_r")), 3),
      )
      if key in seen:  # same combo re-run across rounds
        continue
      seen.add(key)
      rows.append({
        "preset": str(row.get("mining_preset") or "?"),
        "label": str(row.get("label") or ""),
        "n": n,
        "wr": _f(row.get("win_rate_pct")),
        "rr": _f(row.get("avg_rr")),
        "r": _f(row.get("total_r")),
        "dd": _f(row.get("max_drawdown_r")),
        "tpw": _f(row.get("trades_per_week")),
        "ev": _f(row.get("total_r")) / n,
        "run": path.stem,
      })
  return rows


def _stat(name: str, values: list[float]) -> str:
  if not values:
    return f"{name}: -"
  return (
    f"{name}: median={statistics.median(values):.2f} "
    f"p90={sorted(values)[int(len(values) * 0.9) - 1]:.2f} max={max(values):.2f}"
  )


def main() -> int:
  rows = _load()
  print(f"combo duy nhat: {len(rows)}\n")

  print("=== EV/lenh theo bucket so lenh n ===")
  buckets = [(1, 9), (10, 19), (20, 29), (30, 44), (45, 10**6)]
  for lo, hi in buckets:
    grp = [r for r in rows if lo <= r["n"] <= hi]
    if not grp:
      continue
    ev = [r["ev"] for r in grp]
    wr = [r["wr"] for r in grp]
    rr = [r["rr"] for r in grp]
    print(
      f"  n {lo}-{hi if hi < 10**6 else '+'}: k={len(grp):3d} "
      f"EV median={statistics.median(ev):5.2f} p90={sorted(ev)[int(len(ev) * 0.9) - 1]:5.2f} "
      f"| WR median={statistics.median(wr):5.1f} | RR median={statistics.median(rr):4.2f} "
      f"| R median={statistics.median([r['r'] for r in grp]):6.1f} "
      f"max={max(r['r'] for r in grp):6.1f}"
    )

  print("\n=== Theo preset (median) ===")
  by_preset: dict[str, list[dict]] = defaultdict(list)
  for r in rows:
    by_preset[r["preset"]].append(r)
  for preset, grp in sorted(by_preset.items(), key=lambda kv: -statistics.median([r["r"] for r in kv[1]])):
    print(
      f"  {preset:<22} k={len(grp):3d} n={statistics.median([r['n'] for r in grp]):5.1f} "
      f"EV={statistics.median([r['ev'] for r in grp]):5.2f} "
      f"WR={statistics.median([r['wr'] for r in grp]):5.1f} "
      f"RR={statistics.median([r['rr'] for r in grp]):4.2f} "
      f"R={statistics.median([r['r'] for r in grp]):6.1f} "
      f"Rmax={max(r['r'] for r in grp):6.1f} nmax={max(r['n'] for r in grp):4d}"
    )

  print("\n=== Tuong quan n <-> EV (co phai tang lenh thi giam chat luong?) ===")
  ns = [r["n"] for r in rows]
  evs = [r["ev"] for r in rows]
  mean_n, mean_ev = statistics.fmean(ns), statistics.fmean(evs)
  cov = statistics.fmean([(a - mean_n) * (b - mean_ev) for a, b in zip(ns, evs)])
  sd_n = statistics.pstdev(ns) or 1e-9
  sd_ev = statistics.pstdev(evs) or 1e-9
  print(f"  corr(n, EV) = {cov / (sd_n * sd_ev):+.3f}  (n median={statistics.median(ns)}, EV median={mean_ev:.2f})")
  print(f"  {_stat('EV toan bo', evs)}")
  print(f"  {_stat('n toan bo', [float(x) for x in ns])}")

  print("\n=== So lenh can de dat R>100 theo tung muc EV ===")
  for ev in (0.4, 0.6, 0.8, 0.93, 1.13):
    print(f"  EV={ev:.2f}R/lenh -> can n>={int(100 / ev) + 1:4d} lenh")

  print("\n=== Combo dat WR>55 va RR>2.5: thieu bao nhieu lenh? ===")
  qual = [r for r in rows if r["wr"] > 54.99 and r["rr"] > 2.5]
  if not qual:
    print("  (khong co)")
  for r in sorted(qual, key=lambda x: -x["ev"]):
    need = int(100 / max(r["ev"], 0.01)) + 1
    print(
      f"  EV={r['ev']:5.2f} n={r['n']:3d} R={r['r']:6.1f} WR={r['wr']:5.1f} RR={r['rr']:4.2f} "
      f"-> can n>={need:4d} (thieu {need - r['n']:4d}) · {r['preset']} · {r['label'][:52]}"
    )

  print("\n=== Tran Total R theo do dai OOS (n cao nhat da tung thay) ===")
  best_n = max(rows, key=lambda r: r["n"])
  print(
    f"  n cao nhat = {best_n['n']} (tpw={best_n['tpw']:.2f}) EV={best_n['ev']:.2f} "
    f"R={best_n['r']:.1f} · {best_n['preset']} · {best_n['label'][:60]}"
  )
  tpws = [r["tpw"] for r in rows if r["tpw"] > 0]
  if tpws:
    print(
      f"  tpw median={statistics.median(tpws):.2f} p90={sorted(tpws)[int(len(tpws) * 0.9) - 1]:.2f} "
      f"max={max(tpws):.2f}"
    )
    for tpw in (0.5, 1.0, 1.5, 2.0):
      for months in (12, 26, 60):
        weeks = months * 4.345
        print(
          f"    tpw={tpw:.1f} x OOS {months}m ({weeks:.0f} tuan) -> n={int(tpw * weeks):4d}"
          f" | R@EV0.93={tpw * weeks * 0.93:6.1f}"
        )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
