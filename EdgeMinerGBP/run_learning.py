#!/usr/bin/env python3
"""
Self-Learning Forex System — cải thiện dần qua nhiều epoch.

Mỗi epoch:
  1. Walk-forward OOS (không look-ahead trong epoch)
  2. Ghi nhận rule/ML experience từ kết quả lệnh
  3. Tiến hóa genomes → epoch sau khởi đầu thông minh hơn

Chạy nhiều epoch → hệ thống tích lũy kinh nghiệm → metrics cải thiện dần.

Usage:
  python run_learning.py              # 5 epoch (mặc định)
  python run_learning.py --epochs 10  # 10 epoch
  python run_learning.py --reset      # xóa knowledge, bắt đầu lại
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from data_loader import load_gbpusd_h1, get_train_window_indices, get_week_indices
from feature_engine import FeatureMatrix
from knowledge_base import KnowledgeBase, KNOWLEDGE_PATH
from kb_profiles import (
  create_profile, register_profile, slice_df_for_period,
  profile_path, DEFAULT_PROFILE_ID,
)
from config import TRAIN_MONTHS, MIN_TRAIN_BARS, DEFAULT_SPREAD_PIPS, DEFAULT_SLIPPAGE_PIPS
from meta_learner import mine_strategy_learning, record_trade_learning
from optimizer import TARGET_TRADES_PER_WEEK
from strategy import compute_metrics
from strategy_miner import generate_signals_mined, backtest_mined, MinedStrategy

REPORT_DIR = Path(__file__).parent / "results"


def generate_weekly_schedule(df, first_trade_date):
  weeks, current, end = [], first_trade_date, df.index[-1]
  while current < end:
    weeks.append((current, current + pd.Timedelta(days=7)))
    current += pd.Timedelta(days=7)
  return weeks


def run_epoch(df, fm: FeatureMatrix, kb: KnowledgeBase, epoch: int) -> dict:
  train_end_date = df.index[0] + pd.DateOffset(months=TRAIN_MONTHS)
  oos_mask = df.index >= train_end_date
  first_trade_date = df.index[oos_mask][0]
  first_trade_date -= pd.Timedelta(days=first_trade_date.weekday())
  if first_trade_date < train_end_date:
    first_trade_date += pd.Timedelta(days=7)

  weeks = generate_weekly_schedule(df, first_trade_date)
  all_oos_trades = []
  weekly_log = []
  prev_strat: MinedStrategy | None = None

  desc = f"Epoch {epoch} (genomes={len(kb.genomes)}, rules={len(kb.rule_stats)})"
  for week_start, week_end in tqdm(weeks, desc=desc):
    train_start_idx, train_end_idx = get_train_window_indices(df, week_start, TRAIN_MONTHS)
    if train_start_idx is None or (train_end_idx - train_start_idx) < MIN_TRAIN_BARS:
      continue

    strat = mine_strategy_learning(fm, train_start_idx, train_end_idx, kb, as_of=week_start)
    if strat is None:
      strat = prev_strat
    if strat is None:
      continue
    prev_strat = strat

    oos_start, oos_end = get_week_indices(df, week_start, week_end)
    if oos_start is None:
      continue

    signals = generate_signals_mined(fm, strat, oos_start, oos_end)
    week_trades = backtest_mined(
      fm, strat, signals, oos_start, oos_end,
      spread_pips=DEFAULT_SPREAD_PIPS, slippage_pips=DEFAULT_SLIPPAGE_PIPS,
    )

    for t in week_trades:
      try:
        entry_idx = fm.index.get_loc(t.entry_time)
        signal_idx = max(entry_idx - 1, 0)
        record_trade_learning(kb, fm, strat, signal_idx, t.direction, t.r_multiple)
      except Exception:
        pass

    all_oos_trades.extend(week_trades)
    week_m = compute_metrics(week_trades)
    weekly_log.append({
      "week": str(week_start.date()),
      "trades": week_m["n_trades"],
      "wr": round(week_m["win_rate"], 3),
      "r": round(week_m["total_r"], 2),
    })

  overall = compute_metrics(all_oos_trades)
  one_year_ago = df.index[-1] - pd.DateOffset(years=1)
  year_trades = [t for t in all_oos_trades if t.entry_time >= one_year_ago]
  year_m = compute_metrics(year_trades)
  traded_weeks = max(len([w for w in weekly_log if w["trades"] > 0]), 1)
  avg_tpw = overall["n_trades"] / traded_weeks

  epoch_metrics = {
    "epoch": epoch,
    "n_trades": overall["n_trades"],
    "trades_per_week": round(avg_tpw, 2),
    "win_rate_pct": round(overall["win_rate"] * 100, 2),
    "avg_rr": round(overall["avg_rr"], 3),
    "profit_factor": round(overall["profit_factor"], 3),
    "total_pips": round(overall["total_pips"], 2),
    "total_r": round(overall["total_r"], 3),
    "year_win_rate_pct": round(year_m["win_rate"] * 100, 2),
    "year_avg_rr": round(year_m["avg_rr"], 3),
    "year_total_r": round(year_m["total_r"], 3),
    "genomes_in_kb": len(kb.genomes),
    "rules_tracked": len(kb.rule_stats),
    "ml_samples": len(kb.ml_experience),
  }

  kb.record_epoch(epoch, epoch_metrics)
  kb.save()

  from kb_profiles import save_epoch_snapshot, profile_id_from_kb
  save_epoch_snapshot(kb, profile_id_from_kb(kb), epoch_metrics)

  return {
    "epoch_metrics": epoch_metrics,
    "weekly_log": weekly_log,
    "trades": [
      {"entry": str(t.entry_time), "dir": "LONG" if t.direction == 1 else "SHORT",
       "r": round(t.r_multiple, 2), "pnl_pips": round(t.pnl_pips, 1)}
      for t in all_oos_trades
    ],
  }


def print_epoch_report(m: dict):
  print(f"\n--- Epoch {m['epoch']} ---")
  print(f"  Lệnh: {m['n_trades']} ({m['trades_per_week']}/tuần)")
  print(f"  WR: {m['win_rate_pct']}% | RR: {m['avg_rr']} | PF: {m['profit_factor']}")
  print(f"  Tổng: {m['total_r']}R ({m['total_pips']} pips)")
  print(f"  KB: {m['genomes_in_kb']} genomes | {m['rules_tracked']} rules | {m['ml_samples']} ML mẫu")


def print_final_comparison(history: list[dict]):
  if not history:
    return
  print(f"\n{'='*60}")
  print("TIẾN BỘ QUA CÁC EPOCH")
  print(f"{'='*60}")
  print(f"{'Epoch':>6} {'Lệnh':>6} {'WR%':>7} {'RR':>6} {'TotalR':>8} {'Genomes':>8}")
  for m in history:
    print(f"{m['epoch']:>6} {m['n_trades']:>6} {m['win_rate_pct']:>7.1f} "
          f"{m['avg_rr']:>6.2f} {m['total_r']:>8.1f} {m['genomes_in_kb']:>8}")
  if len(history) >= 2:
    d_wr = history[-1]["win_rate_pct"] - history[0]["win_rate_pct"]
    d_r = history[-1]["total_r"] - history[0]["total_r"]
    d_rr = history[-1]["avg_rr"] - history[0]["avg_rr"]
    print(f"\nΔ Epoch1→{history[-1]['epoch']}: WR {d_wr:+.1f}% | RR {d_rr:+.2f} | R {d_r:+.1f}")


def main():
  parser = argparse.ArgumentParser(description="Self-learning GBP/USD walk-forward")
  parser.add_argument("--epochs", type=int, default=5, help="Số epoch học (mặc định 5)")
  parser.add_argument("--reset", action="store_true", help="Xóa knowledge base của profile")
  parser.add_argument("--kb-profile", default=DEFAULT_PROFILE_ID,
                      help="ID profile KB (lưu tại learning/kb_profiles/)")
  parser.add_argument("--kb-name", default=None, help="Tên hiển thị profile")
  parser.add_argument("--from-date", default="2022-01-01", help="Data từ ngày")
  parser.add_argument("--until-date", default=None, help="Data đến ngày (giai đoạn KB)")
  args = parser.parse_args()

  profile_id = args.kb_profile
  if profile_id != DEFAULT_PROFILE_ID and not profile_path(profile_id).exists():
    create_profile(profile_id, args.kb_name or profile_id)

  kb_path = profile_path(profile_id)
  if args.reset and kb_path.exists():
    kb_path.unlink()
    print(f"Đã xóa KB profile: {profile_id}")

  kb = KnowledgeBase(kb_path)
  print("Tải dữ liệu GBP/USD H1...")
  df = load_gbpusd_h1(args.from_date)
  df = slice_df_for_period(df, args.from_date, args.until_date)
  if len(df) < MIN_TRAIN_BARS + 100:
    print("Không đủ dữ liệu cho giai đoạn đã chọn.")
    return 1
  fm = FeatureMatrix(df)
  print(f"{len(df)} bars ({df.index[0].date()} -> {df.index[-1].date()})")
  print(f"KB profile: {profile_id} | epochs trước: {kb.epoch_count} | genomes: {len(kb.genomes)}")

  print(f"\n{'='*60}")
  print("SELF-LEARNING SYSTEM v4")
  print(f"Epochs: {args.epochs} | Mục tiêu: ~{TARGET_TRADES_PER_WEEK} lệnh/tuần")
  print("Mỗi epoch học từ kết quả → epoch sau thông minh hơn")
  print(f"{'='*60}")

  all_epoch_results = []
  for epoch in range(1, args.epochs + 1):
    result = run_epoch(df, fm, kb, epoch)
    m = result["epoch_metrics"]
    all_epoch_results.append(m)
    print_epoch_report(m)

  print_final_comparison(all_epoch_results)
  print(f"\n{kb.improvement_summary()}")

  register_profile(
    profile_id,
    args.kb_name or profile_id,
    str(df.index[0].date()),
    str(df.index[-1].date()),
    args.epochs,
    note=f"learning {args.epochs} epoch(s)",
  )

  REPORT_DIR.mkdir(exist_ok=True)
  report = {
    "epochs": args.epochs,
    "kb_profile": profile_id,
    "trained_from": str(df.index[0].date()),
    "trained_to": str(df.index[-1].date()),
    "epoch_history": all_epoch_results,
    "kb_summary": {
      "genomes": len(kb.genomes),
      "rules": len(kb.rule_stats),
      "ml_samples": len(kb.ml_experience),
      "best_fitness": kb.best_fitness_ever,
    },
    "last_epoch_trades": result["trades"] if all_epoch_results else [],
  }
  path = REPORT_DIR / "learning_report.json"
  with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

  print(f"\nKnowledge profile: {kb_path}")
  print(f"Báo cáo: {path}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
