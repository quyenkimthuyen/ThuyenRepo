#!/usr/bin/env python3
"""So sánh cập nhật chiến lược: mỗi tuần vs mỗi tháng."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from data_loader import load_gbpusd_h1
from gui.trade_model import get_model_by_id, get_model_run_params, load_active_model_id
from run_backtest import run_walk_forward


def _summary(result: dict) -> dict:
  o = result["overall_oos"]
  y = result["last_1_year"]
  c = result["constraints_met"]
  reopts = len([w for w in result.get("weekly_log", []) if w.get("oos_trades") is not None])
  return {
    "reopt_period": result["config"].get("reopt_period", "week"),
    "periods": reopts,
    "n_trades": o["n_trades"],
    "trades_per_week": o["trades_per_week"],
    "win_rate_pct": o["win_rate_pct"],
    "avg_rr": o["avg_rr"],
    "profit_factor": o["profit_factor"],
    "total_r": o["total_r"],
    "max_dd_r": o["max_drawdown_r"],
    "year_wr_pct": y["win_rate_pct"],
    "year_total_r": y["total_r"],
    "constraints_ok": all(c.values()),
  }


def main():
  import argparse
  p = argparse.ArgumentParser()
  p.add_argument("--model-id", default=None)
  p.add_argument("--oos-from", default=None)
  p.add_argument("--oos-to", default=None)
  p.add_argument("--out", type=Path, default=ROOT / "results" / "reopt_compare.json")
  args = p.parse_args()

  mid = args.model_id or load_active_model_id()
  model = get_model_by_id(mid) if mid else None
  params = get_model_run_params(model)

  oos_from = args.oos_from or params.get("oos_from") or "2025-01-01"
  oos_to = args.oos_to or params.get("oos_to")

  df = load_gbpusd_h1("2022-01-01")
  print(f"So sánh reopt | model={mid} | OOS {oos_from} → {oos_to or 'latest'}")
  print(f"Train={params['train_months']}T | KB={params['kb_profile']} ep={params.get('kb_snapshot')}\n")

  common = dict(
    df=df,
    use_learning=params["use_kb"],
    train_months=params["train_months"],
    spread_pips=params["spread_pips"],
    slippage_pips=params["slippage_pips"],
    kb_profile=params["kb_profile"] if params["use_kb"] else None,
    kb_snapshot=params.get("kb_snapshot"),
    oos_from=oos_from,
    oos_to=oos_to,
    verbose=True,
  )

  results = {}
  for period in ("week", "month"):
    print(f"\n{'='*60}\nChạy reopt_period={period}\n{'='*60}")
    r = run_walk_forward(**common, reopt_period=period)
    results[period] = r

  rows = [_summary(results[k]) for k in ("week", "month")]
  w, m = rows[0], rows[1]

  print(f"\n{'='*60}")
  print("SO SÁNH CẬP NHẬT CHIẾN LƯỢC")
  print(f"{'='*60}")
  hdr = f"{'Metric':<22} {'Tuần':>12} {'Tháng':>12} {'Δ (tháng-tuần)':>16}"
  print(hdr)
  print("-" * len(hdr))
  metrics = [
    ("Số kỳ re-opt", "periods", ".0f"),
    ("Tổng lệnh", "n_trades", ".0f"),
    ("Lệnh/tuần", "trades_per_week", ".2f"),
    ("Win rate %", "win_rate_pct", ".2f"),
    ("Avg RR", "avg_rr", ".3f"),
    ("Profit factor", "profit_factor", ".3f"),
    ("Total R", "total_r", "+.2f"),
    ("Max DD (R)", "max_dd_r", ".2f"),
    ("WR 1 năm %", "year_wr_pct", ".2f"),
    ("R 1 năm", "year_total_r", "+.2f"),
  ]
  for label, key, fmt in metrics:
    wv, mv = w[key], m[key]
    delta = mv - wv if isinstance(wv, (int, float)) else 0
    if fmt == ".0f":
      print(f"{label:<22} {wv:12.0f} {mv:12.0f} {delta:+12.0f}")
    elif fmt == ".3f":
      print(f"{label:<22} {wv:12.3f} {mv:12.3f} {delta:+12.3f}")
    elif fmt == "+.2f":
      print(f"{label:<22} {wv:+12.2f} {mv:+12.2f} {delta:+12.2f}")
    else:
      print(f"{label:<22} {wv:12.2f} {mv:12.2f} {delta:+12.2f}")

  winner = "month" if m["total_r"] > w["total_r"] else "week"
  if abs(m["total_r"] - w["total_r"]) < 1.0:
    verdict = "Tương đương — chênh lệch Total R < 1R"
  else:
    verdict = f"**{winner}** tốt hơn về Total R ({max(w['total_r'], m['total_r']):+.1f}R vs {min(w['total_r'], m['total_r']):+.1f}R)"

  print(f"\nKết luận: {verdict}")
  if m["max_dd_r"] < w["max_dd_r"]:
    print(f"  · Tháng có drawdown thấp hơn ({m['max_dd_r']:.2f}R vs {w['max_dd_r']:.2f}R)")
  elif w["max_dd_r"] < m["max_dd_r"]:
    print(f"  · Tuần có drawdown thấp hơn ({w['max_dd_r']:.2f}R vs {m['max_dd_r']:.2f}R)")

  out = {
    "model_id": mid,
    "oos_from": oos_from,
    "oos_to": oos_to,
    "summary": {k: rows[i] for i, k in enumerate(("week", "month"))},
    "verdict": verdict,
    "winner": winner,
  }
  args.out.parent.mkdir(parents=True, exist_ok=True)
  with open(args.out, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
  print(f"\nĐã lưu: {args.out}")


if __name__ == "__main__":
  main()
