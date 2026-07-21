#!/usr/bin/env python3
"""So sánh quota lệnh: 2/tuần (mặc định) vs 1/ngày."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_h1
from gui.trade_model import get_model_run_params, load_active_model_id
from run_backtest import run_walk_forward


def _summary(result: dict) -> dict:
  o = result["overall_oos"]
  y = result["last_1_year"]
  cfg = result.get("config") or {}
  return {
    "quota": "1/ngày" if cfg.get("max_trades_per_day") else "2/tuần",
    "n_trades": o["n_trades"],
    "trades_per_week": o["trades_per_week"],
    "win_rate_pct": o["win_rate_pct"],
    "avg_rr": o["avg_rr"],
    "profit_factor": o["profit_factor"],
    "total_r": o["total_r"],
    "max_dd_r": o["max_drawdown_r"],
    "year_wr_pct": y["win_rate_pct"],
    "year_total_r": y["total_r"],
  }


def main():
  import argparse
  p = argparse.ArgumentParser()
  p.add_argument("--oos-from", default="2025-01-01")
  p.add_argument("--oos-to", default="2026-12-31")
  p.add_argument("--out", type=Path, default=ROOT / "results" / "trade_quota_compare.json")
  args = p.parse_args()

  mid = load_active_model_id()
  params = get_model_run_params()
  df = load_eurusd_h1("2022-01-01")
  print(f"So sánh quota lệnh | model={mid} | OOS {args.oos_from} → {args.oos_to}\n")

  common = dict(
    df=df,
    use_learning=params["use_kb"],
    train_months=params["train_months"],
    spread_pips=params["spread_pips"],
    slippage_pips=params["slippage_pips"],
    kb_profile=params["kb_profile"] if params["use_kb"] else None,
    kb_snapshot=params.get("kb_snapshot"),
    oos_from=args.oos_from,
    oos_to=args.oos_to,
    reopt_period="week",
    verbose=True,
  )

  scenarios = [
    ("week_2", {"max_trades_per_day": 0}),
    ("day_1", {"max_trades_per_day": 1}),
  ]
  results = {}
  for key, kw in scenarios:
    label = "2 lệnh/tuần" if key == "week_2" else "1 lệnh/ngày"
    print(f"\n{'='*60}\n{label}\n{'='*60}")
    results[key] = run_walk_forward(**common, **kw)

  w, d = _summary(results["week_2"]), _summary(results["day_1"])

  print(f"\n{'='*60}")
  print("SO SÁNH QUOTA LỆNH")
  print(f"{'='*60}")
  print(f"{'Metric':<22} {'2/tuần':>12} {'1/ngày':>12} {'Δ':>12}")
  print("-" * 60)
  for label, key, fmt in [
    ("Tổng lệnh", "n_trades", ".0f"),
    ("Lệnh/tuần", "trades_per_week", ".2f"),
    ("Win rate %", "win_rate_pct", ".2f"),
    ("Avg RR", "avg_rr", ".3f"),
    ("Profit factor", "profit_factor", ".3f"),
    ("Total R", "total_r", "+.2f"),
    ("Max DD (R)", "max_dd_r", ".2f"),
    ("R 1 năm", "year_total_r", "+.2f"),
  ]:
    wv, dv = w[key], d[key]
    delta = dv - wv
    if fmt == ".0f":
      print(f"{label:<22} {wv:12.0f} {dv:12.0f} {delta:+12.0f}")
    elif fmt == ".3f":
      print(f"{label:<22} {wv:12.3f} {dv:12.3f} {delta:+12.3f}")
    elif fmt == "+.2f":
      print(f"{label:<22} {wv:+12.2f} {dv:+12.2f} {delta:+12.2f}")
    else:
      print(f"{label:<22} {wv:12.2f} {dv:12.2f} {delta:+12.2f}")

  winner = "day_1" if d["total_r"] > w["total_r"] else "week_2"
  wlabel = "1 lệnh/ngày" if winner == "day_1" else "2 lệnh/tuần"
  print(f"\nKết luận: **{wlabel}** tốt hơn về Total R ({max(w['total_r'], d['total_r']):+.1f}R vs {min(w['total_r'], d['total_r']):+.1f}R)")

  out = {"model_id": mid, "summary": {"week_2": w, "day_1": d}, "winner": winner}
  args.out.parent.mkdir(parents=True, exist_ok=True)
  with open(args.out, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
  print(f"\nĐã lưu: {args.out}")


if __name__ == "__main__":
  main()
