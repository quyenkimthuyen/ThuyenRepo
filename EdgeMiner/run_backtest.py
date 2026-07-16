#!/usr/bin/env python3
"""Walk-Forward Backtest v2 — Adaptive Strategy Mining."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from data_loader import load_eurusd_h1, get_train_window_indices, get_week_indices
from feature_engine import FeatureMatrix
from optimizer import optimize_on_window, TARGET_TRADES_PER_WEEK
from strategy import compute_metrics
from strategy_miner import (
  MinedStrategy, generate_signals_mined, backtest_mined, Rule,
)

REPORT_DIR = Path(__file__).parent / "results"
TRAIN_MONTHS = 3
MIN_TRAIN_BARS = 500


def generate_weekly_schedule(df, first_trade_date):
  weeks, current, end = [], first_trade_date, df.index[-1]
  while current < end:
    weeks.append((current, current + pd.Timedelta(days=7)))
    current += pd.Timedelta(days=7)
  return weeks


def strategy_to_dict(s: MinedStrategy) -> dict:
  def rules_to_list(rules: list[Rule]):
    return [{"feat": r.feature, "op": r.op, "thr": round(r.threshold, 4), "w": round(r.weight, 3)}
            for r in rules]
  return {
    "name": s.name,
    "exit_mode": s.exit_mode,
    "ml_prob_min": s.ml_prob_min,
    "rr": s.rr_ratio,
    "atr_mult": s.atr_mult_sl,
    "long_rules": rules_to_list(s.long_rules),
    "short_rules": rules_to_list(s.short_rules),
  }


def run_walk_forward(df: pd.DataFrame) -> dict:
  fm = FeatureMatrix(df)
  train_end_date = df.index[0] + pd.DateOffset(months=TRAIN_MONTHS)
  oos_mask = df.index >= train_end_date
  first_trade_date = df.index[oos_mask][0]
  first_trade_date -= pd.Timedelta(days=first_trade_date.weekday())
  if first_trade_date < train_end_date:
    first_trade_date += pd.Timedelta(days=7)

  weeks = generate_weekly_schedule(df, first_trade_date)
  all_oos_trades = []
  weekly_log = []
  last_strat: MinedStrategy | None = None
  prev_strat: MinedStrategy | None = None  # fallback if mining fails

  print(f"\n{'='*60}")
  print("WALK-FORWARD v3 — RULES + ML + SMART EXITS")
  print(f"{'='*60}")
  print(f"Dữ liệu: {df.index[0].date()} -> {df.index[-1].date()} ({len(df)} bars)")
  print(f"Mục tiêu: ~{TARGET_TRADES_PER_WEEK} lệnh/tuần | Train: {TRAIN_MONTHS} tháng")
  print(f"OOS từ: {first_trade_date.date()} | {len(weeks)} tuần")
  print(f"{'='*60}\n")

  for week_start, week_end in tqdm(weeks, desc="Walk-forward"):
    train_start_idx, train_end_idx = get_train_window_indices(df, week_start, TRAIN_MONTHS)
    if train_start_idx is None or (train_end_idx - train_start_idx) < MIN_TRAIN_BARS:
      weekly_log.append({"week_start": str(week_start.date()), "status": "skip_train"})
      continue

    strat = optimize_on_window(fm, train_start_idx, train_end_idx)
    if strat is None:
      strat = prev_strat  # dùng chiến lược tuần trước nếu mine thất bại
    if strat is None:
      weekly_log.append({"week_start": str(week_start.date()), "status": "skip_no_strategy"})
      continue

    last_strat = strat
    prev_strat = strat

    oos_start, oos_end = get_week_indices(df, week_start, week_end)
    if oos_start is None:
      continue

    signals = generate_signals_mined(fm, strat, oos_start, oos_end)
    train_signals = generate_signals_mined(fm, strat, train_start_idx, train_end_idx)
    train_trades = backtest_mined(fm, strat, train_signals, train_start_idx, train_end_idx)
    train_m = compute_metrics(train_trades)

    week_trades = backtest_mined(fm, strat, signals, oos_start, oos_end)
    all_oos_trades.extend(week_trades)
    week_m = compute_metrics(week_trades)

    weekly_log.append({
      "week_start": str(week_start.date()),
      "strategy": strat.name,
      "score_thr": strat.score_threshold,
      "long_rules": len(strat.long_rules),
      "short_rules": len(strat.short_rules),
      "train_wr": round(train_m["win_rate"], 3),
      "oos_trades": week_m["n_trades"],
      "oos_wr": round(week_m["win_rate"], 3),
      "oos_pips": round(week_m["total_pips"], 1),
      "oos_r": round(week_m["total_r"], 2),
    })

  overall = compute_metrics(all_oos_trades)
  one_year_ago = df.index[-1] - pd.DateOffset(years=1)
  year_trades = [t for t in all_oos_trades if t.entry_time >= one_year_ago]
  year_m = compute_metrics(year_trades)
  n_weeks = len([w for w in weekly_log if w.get("oos_trades") is not None])
  traded_weeks = len([w for w in weekly_log if w.get("oos_trades", 0) > 0 or "oos_trades" in w])
  avg_tpw = overall["n_trades"] / max(traded_weeks, 1)

  return {
    "data_range": {"start": str(df.index[0].date()), "end": str(df.index[-1].date()), "bars": len(df)},
    "config": {
      "version": "adaptive_miner_v3",
      "train_months": TRAIN_MONTHS,
      "target_trades_per_week": TARGET_TRADES_PER_WEEK,
      "pair": "EUR/USD", "tf": "H1",
    },
    "overall_oos": {
      "n_trades": overall["n_trades"],
      "trades_per_week": round(avg_tpw, 2),
      "win_rate_pct": round(overall["win_rate"] * 100, 2),
      "avg_rr": round(overall["avg_rr"], 3),
      "profit_factor": round(overall["profit_factor"], 3),
      "total_pips": round(overall["total_pips"], 2),
      "total_r": round(overall["total_r"], 3),
    },
    "last_1_year": {
      "n_trades": year_m["n_trades"],
      "win_rate_pct": round(year_m["win_rate"] * 100, 2),
      "avg_rr": round(year_m["avg_rr"], 3),
      "profit_factor": round(year_m["profit_factor"], 3),
      "total_pips": round(year_m["total_pips"], 2),
      "total_r": round(year_m["total_r"], 3),
    },
    "constraints_met": {
      "win_rate_above_60": year_m["win_rate"] >= 0.60,
      "rr_above_2": year_m["avg_rr"] >= 2.0,
      "profitable": year_m["total_r"] > 0,
      "trades_per_week_near_2": 1.2 <= avg_tpw <= 3.0,
    },
    "last_strategy": strategy_to_dict(last_strat) if last_strat else None,
    "weekly_log": weekly_log,
    "trades": [
      {
        "entry": str(t.entry_time), "exit": str(t.exit_time),
        "dir": "LONG" if t.direction == 1 else "SHORT",
        "entry_px": round(t.entry_price, 5), "exit_px": round(t.exit_price, 5),
        "pnl_pips": round(t.pnl_pips, 1), "r": round(t.r_multiple, 2),
        "reason": t.exit_reason,
      }
      for t in all_oos_trades
    ],
  }


def print_report(r: dict):
  o, y, c = r["overall_oos"], r["last_1_year"], r["constraints_met"]
  print(f"\n{'='*60}\nKẾT QUẢ BACKTEST OOS — ADAPTIVE MINER v3\n{'='*60}")
  print(f"\n[TOÀN BỘ OOS - {o['n_trades']} lệnh | {o['trades_per_week']} lệnh/tuần]")
  print(f"  Win Rate: {o['win_rate_pct']}% | RR: {o['avg_rr']} | PF: {o['profit_factor']}")
  print(f"  Tổng: {o['total_pips']} pips | {o['total_r']}R")
  print(f"\n[1 NĂM GẦN NHẤT - {y['n_trades']} lệnh]")
  print(f"  Win Rate: {y['win_rate_pct']}% {'✓' if c['win_rate_above_60'] else '✗'} (>60%)")
  print(f"  RR:       {y['avg_rr']} {'✓' if c['rr_above_2'] else '✗'} (>2)")
  print(f"  Lợi nhuận: {y['total_r']}R {'✓' if c['profitable'] else '✗'}")
  print(f"  Tần suất:  {o['trades_per_week']} lệnh/tuần {'✓' if c['trades_per_week_near_2'] else '✗'} (mục tiêu ~2)")
  ok = all(c.values())
  print(f"\n{'✓ ĐẠT YÊU CẦU' if ok else '✗ CHƯA ĐẠT ĐỦ YÊU CẦU'}\n{'='*60}\n")


def main():
  print("Tải dữ liệu EUR/USD H1 (2022+)...")
  df = load_eurusd_h1("2022-01-01")
  print(f"{len(df)} bars: {df.index[0].date()} -> {df.index[-1].date()}")
  result = run_walk_forward(df)
  REPORT_DIR.mkdir(exist_ok=True)
  path = REPORT_DIR / "backtest_report.json"
  with open(path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
  print_report(result)
  print(f"Báo cáo: {path}")
  if result["trades"]:
    pd.DataFrame(result["trades"]).to_csv(REPORT_DIR / "oos_trades.csv", index=False)
  return 0 if all(result["constraints_met"].values()) else 1


if __name__ == "__main__":
  sys.exit(main())
