#!/usr/bin/env python3
"""
Export Best-3m walk-forward as a weekly schedule + exact signal calendar.
Used to build an MT5 EA that closely matches app OOS results.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_h1, get_train_window_indices, get_week_indices
from feature_engine import FeatureMatrix
from kb_profiles import load_kb
from optimizer import optimize_on_window, set_kb_profile, reset_kb_cache
from run_backtest import generate_weekly_schedule, strategy_to_dict
from strategy import compute_metrics
from strategy_miner import (
  MinedStrategy, Rule, generate_signals_mined, backtest_mined,
)

OUT = ROOT / "mt5" / "frozen" / "best_3m_wf_schedule.json"


def full_strategy_dict(s: MinedStrategy) -> dict:
  base = strategy_to_dict(s)
  base.update({
    "score_threshold": float(s.score_threshold),
    "atr_mult_sl": float(s.atr_mult_sl),
    "rr_ratio": float(s.rr_ratio),
    "min_rules_match": int(s.min_rules_match),
    "max_trades_per_week": int(s.max_trades_per_week),
    "min_bars_between": int(s.min_bars_between),
    "max_hold_bars": int(s.max_hold_bars),
    "ml_prob_min": float(s.ml_prob_min),
    "exit_mode": s.exit_mode,
    "partial_pct": float(s.partial_pct),
    "partial_at_r": float(s.partial_at_r),
    "trail_activate_r": float(s.trail_activate_r),
    "trail_distance_r": float(s.trail_distance_r),
    "session_filter": bool(s.session_filter),
  })
  return base


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--train-months", type=int, default=3)
  ap.add_argument("--kb-profile", default="era_2023_2025")
  ap.add_argument("--kb-epoch", type=int, default=1)
  ap.add_argument("--oos-from", default="2025-01-01")
  ap.add_argument("--oos-to", default="2026-12-31")
  ap.add_argument("--spread", type=float, default=1.0)
  ap.add_argument("--slippage", type=float, default=0.3)
  ap.add_argument("--out", type=Path, default=OUT)
  args = ap.parse_args()

  reset_kb_cache()
  set_kb_profile(args.kb_profile, args.kb_epoch)
  kb = load_kb(args.kb_profile, args.kb_epoch)

  df = load_eurusd_h1()
  fm = FeatureMatrix(df)
  oos_from = pd.Timestamp(args.oos_from)
  oos_to = pd.Timestamp(args.oos_to)
  weeks = generate_weekly_schedule(df, oos_from, min(oos_to, df.index[-1]))
  weeks = [w for w in weeks if w[0] >= oos_from and w[0] <= oos_to]

  weekly = []
  signals = []
  all_trades = []
  prev: MinedStrategy | None = None

  print(f"Export WF schedule | weeks={len(weeks)} | KB={args.kb_profile}@ep{args.kb_epoch} | train={args.train_months}m")
  for week_start, week_end in tqdm(weeks, desc="Export WF"):
    ts, te = get_train_window_indices(df, week_start, args.train_months)
    if ts is None or (te - ts) < 200:
      weekly.append({"week_start": str(week_start.date()), "status": "skip_train"})
      continue
    strat = optimize_on_window(fm, ts, te, use_learning=True, as_of=week_start, kb=kb)
    if strat is None:
      strat = prev
    if strat is None:
      weekly.append({"week_start": str(week_start.date()), "status": "skip_no_strategy"})
      continue
    prev = strat

    oos_s, oos_e = get_week_indices(df, week_start, week_end)
    if oos_s is None:
      continue

    sig = generate_signals_mined(fm, strat, oos_s, oos_e)
    trades = backtest_mined(
      fm, strat, sig, oos_s, oos_e,
      spread_pips=args.spread, slippage_pips=args.slippage,
    )
    all_trades.extend(trades)
    m = compute_metrics(trades)

    # Only entries that actually opened (skip signals ignored while in-trade).
    # Store SIGNAL bar time (entry is next bar open) — matches Python i -> i+1.
    for tr in trades:
      # entry_time is bar i+1; signal bar is previous H1
      entry_ts = pd.Timestamp(tr.entry_time)
      # find signal index
      ei = int(fm.index.searchsorted(entry_ts))
      si = max(ei - 1, 0)
      signals.append({
        "t": str(fm.index[si]),
        "d": int(tr.direction),
        "atr_m": float(strat.atr_mult_sl),
        "rr": float(strat.rr_ratio),
        "exit": strat.exit_mode,
        "trail_act": float(strat.trail_activate_r),
        "trail_dist": float(strat.trail_distance_r),
        "partial_pct": float(strat.partial_pct),
        "partial_at_r": float(strat.partial_at_r),
        "max_hold": int(strat.max_hold_bars),
      })

    weekly.append({
      "week_start": str(week_start.date()),
      "week_end": str(week_end.date()),
      "strategy": full_strategy_dict(strat),
      "oos_trades": m["n_trades"],
      "oos_r": round(m["total_r"], 3),
      "oos_wr": round(m["win_rate"], 3),
    })

  overall = compute_metrics(all_trades)
  payload = {
    "meta": {
      "source": "Best 3m walk-forward export",
      "train_months": args.train_months,
      "kb_profile": args.kb_profile,
      "kb_epoch": args.kb_epoch,
      "oos_from": args.oos_from,
      "oos_to": args.oos_to,
      "spread_pips": args.spread,
      "slippage_pips": args.slippage,
      "n_weeks": len(weekly),
      "n_signals": len(signals),
      "overall": {
        "n_trades": overall["n_trades"],
        "win_rate_pct": round(overall["win_rate"] * 100, 2),
        "total_r": round(overall["total_r"], 3),
        "profit_factor": round(overall["profit_factor"], 3),
        "max_drawdown_r": round(overall["max_drawdown_r"], 2),
        "total_pips": round(overall["total_pips"], 2),
      },
    },
    "weekly": weekly,
    "signals": signals,
  }
  args.out.parent.mkdir(parents=True, exist_ok=True)
  args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
  print(f"Wrote {args.out}")
  print(f"Signals={len(signals)} trades={overall['n_trades']} total_r={overall['total_r']:+.2f} WR={overall['win_rate']*100:.1f}%")


if __name__ == "__main__":
  main()
