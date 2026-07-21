#!/usr/bin/env python3
"""Walk-Forward Backtest — Adaptive Strategy Mining."""
import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from tqdm import tqdm

from config import (
  DEFAULT_HOLDOUT_MONTHS, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS,
  DEFAULT_MAX_HOLD_BARS, DEFAULT_MIN_BARS_BETWEEN,
  DEFAULT_TRAIL_ACTIVATE_R, DEFAULT_TRAIL_DISTANCE_R,
  MIN_TRAIN_BARS, TRAIN_MONTHS,
)
from data_loader import load_eurusd_h1, get_train_window_indices, get_week_indices
from feature_engine import FeatureMatrix
from kb_profiles import (
  DEFAULT_PROFILE_ID, kb_valid_for_backtest, load_kb, suggest_profiles_for_oos,
)
from optimizer import (
  optimize_on_window, TARGET_TRADES_PER_WEEK,
  set_kb_profile, get_knowledge_base, reset_kb_cache,
)
from knowledge_base import KnowledgeBase
from strategy import compute_metrics
from strategy_miner import (
  MinedStrategy, generate_signals_mined, backtest_mined, Rule,
)

REPORT_DIR = Path(__file__).parent / "results"
ProgressCallback = Callable[[int, int, object], None]


def generate_weekly_schedule(df, first_trade_date, end_date=None):
  weeks, current = [], first_trade_date
  end = end_date if end_date is not None else df.index[-1]
  while current < end:
    weeks.append((current, current + pd.Timedelta(days=7)))
    current += pd.Timedelta(days=7)
  return weeks


def generate_monthly_schedule(df, first_trade_date, end_date=None):
  """Lịch walk-forward theo tháng — mine 1 lần, trade cả tháng OOS."""
  end = end_date if end_date is not None else df.index[-1]
  current = pd.Timestamp(first_trade_date).normalize().replace(day=1)
  periods = []
  while current < end:
    period_end = min(current + pd.DateOffset(months=1), pd.Timestamp(end))
    if period_end > current:
      periods.append((current, period_end))
    current = period_end
  return periods


def generate_reopt_schedule(df, first_trade_date, end_date=None, reopt_period: str = "week"):
  if reopt_period == "month":
    return generate_monthly_schedule(df, first_trade_date, end_date)
  return generate_weekly_schedule(df, first_trade_date, end_date)


def strategy_to_dict(s: MinedStrategy) -> dict:
  def rules_to_list(rules: list[Rule]):
    return [{"feat": r.feature, "op": r.op, "thr": round(r.threshold, 4), "w": round(r.weight, 3)}
            for r in rules]
  return {
    "name": s.name,
    "exit_mode": s.exit_mode,
    "ml_prob_min": s.ml_prob_min,
    "score_threshold": s.score_threshold,
    "min_rules_match": s.min_rules_match,
    "rr": s.rr_ratio,
    "atr_mult": s.atr_mult_sl,
    "max_hold_bars": s.max_hold_bars,
    "min_bars_between": s.min_bars_between,
    "max_trades_per_week": s.max_trades_per_week,
    "trail_activate_r": s.trail_activate_r,
    "trail_distance_r": s.trail_distance_r,
    "session_filter": s.session_filter,
    "long_rules": rules_to_list(s.long_rules),
    "short_rules": rules_to_list(s.short_rules),
  }


def _trades_to_json(trades) -> list[dict]:
  return [
    {
      "entry": str(t.entry_time), "exit": str(t.exit_time),
      "dir": "LONG" if t.direction == 1 else "SHORT",
      "entry_px": round(t.entry_price, 5), "exit_px": round(t.exit_price, 5),
      "sl": round(t.sl, 5), "tp": round(t.tp, 5),
      "pnl_pips": round(t.pnl_pips, 1), "r": round(t.r_multiple, 2),
      "reason": t.exit_reason,
    }
    for t in trades
  ]


def _run_holdout_forward(
  df: pd.DataFrame, fm: FeatureMatrix, holdout_cutoff: pd.Timestamp,
  use_learning: bool, train_months: int,
  spread_pips: float, slippage_pips: float,
  kb: KnowledgeBase | None = None,
) -> tuple[list, dict | None]:
  """Mine 1 lần tại holdout, trade holdout không re-optimize (strict forward)."""
  train_start_idx, train_end_idx = get_train_window_indices(df, holdout_cutoff, train_months)
  if train_start_idx is None:
    return [], None
  strat = optimize_on_window(
    fm, train_start_idx, train_end_idx,
    use_learning=use_learning, as_of=holdout_cutoff, kb=kb,
  )
  if strat is None:
    return [], None
  holdout_mask = df.index >= holdout_cutoff
  if not holdout_mask.any():
    return [], strategy_to_dict(strat)
  start_i = df.index.get_loc(df.index[holdout_mask][0])
  sig = generate_signals_mined(fm, strat, start_i, fm.n)
  trades = backtest_mined(
    fm, strat, sig, start_i, fm.n,
    spread_pips=spread_pips, slippage_pips=slippage_pips,
  )
  return trades, strategy_to_dict(strat)


def run_walk_forward(
  df: pd.DataFrame,
  use_learning: bool = True,
  train_months: int = TRAIN_MONTHS,
  on_progress: Optional[ProgressCallback] = None,
  verbose: bool = True,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  holdout_months: int = DEFAULT_HOLDOUT_MONTHS,
  risk_pct_per_trade: float = 1.0,
  kb_profile: str | None = None,
  kb_snapshot: int | str | None = None,
  oos_from: str | None = None,
  oos_to: str | None = None,
  reopt_period: str = "week",
  max_trades_per_day: int = 0,
  max_hold_bars: int | None = None,
  min_bars_between: int | None = None,
  trail_hybrid: tuple[float, float] | None = None,
) -> dict:
  reset_kb_cache()
  kb_instance: KnowledgeBase | None = None
  kb_validation = {"ok": True, "message": "KB OFF"}
  profile_id = kb_profile or DEFAULT_PROFILE_ID

  if use_learning:
    set_kb_profile(profile_id, kb_snapshot)
    kb_instance = get_knowledge_base(profile_id, kb_snapshot)
    check_start = oos_from or str(df.index[0].date())
    ok, msg = kb_valid_for_backtest(profile_id, check_start, oos_to)
    kb_validation = {"ok": ok, "message": msg, "profile_id": profile_id}

  holdout_cutoff = None
  if holdout_months > 0:
    holdout_cutoff = df.index[-1] - pd.DateOffset(months=holdout_months)

  df_wf = df[df.index < holdout_cutoff] if holdout_cutoff is not None else df
  fm = FeatureMatrix(df)

  train_end_date = df_wf.index[0] + pd.DateOffset(months=train_months)
  oos_mask = df_wf.index >= train_end_date
  first_trade_date = df_wf.index[oos_mask][0]
  first_trade_date -= pd.Timedelta(days=first_trade_date.weekday())
  if first_trade_date < train_end_date:
    first_trade_date += pd.Timedelta(days=7)

  if oos_from:
    oos_from_ts = pd.Timestamp(oos_from)
    if oos_from_ts > first_trade_date:
      first_trade_date = oos_from_ts - pd.Timedelta(days=oos_from_ts.weekday())

  wf_end = holdout_cutoff if holdout_cutoff is not None else df_wf.index[-1]
  if oos_to:
    wf_end = min(wf_end, pd.Timestamp(oos_to))

  weeks = generate_reopt_schedule(df_wf, first_trade_date, wf_end, reopt_period)
  if oos_from:
    weeks = [w for w in weeks if w[0] >= pd.Timestamp(oos_from)]
  if oos_to:
    weeks = [w for w in weeks if w[0] <= pd.Timestamp(oos_to)]
  all_oos_trades = []
  weekly_log = []
  last_strat: MinedStrategy | None = None
  prev_strat: MinedStrategy | None = None
  period_label = "tháng" if reopt_period == "month" else "tuần"

  if verbose:
    print(f"Walk-forward | bars={len(df)} | KB={'ON' if use_learning else 'OFF'} "
          f"| profile={profile_id if use_learning else '-'} | {period_label}={len(weeks)} "
          f"| reopt={reopt_period}")
    if use_learning:
      print(f"  KB check: {kb_validation['message']}")

  week_iter = tqdm(weeks, desc=f"Walk-forward ({reopt_period})", disable=not verbose or on_progress is not None)
  for wi, (week_start, week_end) in enumerate(week_iter):
    if on_progress:
      on_progress(wi + 1, len(weeks), week_start)

    train_start_idx, train_end_idx = get_train_window_indices(df, week_start, train_months)
    if train_start_idx is None or (train_end_idx - train_start_idx) < MIN_TRAIN_BARS:
      weekly_log.append({"week_start": str(week_start.date()), "status": "skip_train"})
      continue

    strat = optimize_on_window(
      fm, train_start_idx, train_end_idx,
      use_learning=use_learning, as_of=week_start, kb=kb_instance,
    )
    if strat is None:
      strat = prev_strat
    if strat is None:
      weekly_log.append({"week_start": str(week_start.date()), "status": "skip_no_strategy"})
      continue

    last_strat, prev_strat = strat, strat
    if max_trades_per_day > 0:
      strat.max_trades_per_day = max_trades_per_day
    if max_hold_bars is not None:
      strat.max_hold_bars = max_hold_bars
    if min_bars_between is not None:
      strat.min_bars_between = min_bars_between
    if trail_hybrid is not None:
      strat.exit_mode = "hybrid"
      strat.trail_activate_r, strat.trail_distance_r = trail_hybrid
    oos_start, oos_end = get_week_indices(df, week_start, week_end)
    if oos_start is None:
      continue

    signals = generate_signals_mined(fm, strat, oos_start, oos_end)
    train_signals = generate_signals_mined(fm, strat, train_start_idx, train_end_idx)
    train_trades = backtest_mined(
      fm, strat, train_signals, train_start_idx, train_end_idx,
      spread_pips=spread_pips, slippage_pips=slippage_pips,
    )
    train_m = compute_metrics(train_trades, risk_pct_per_trade)

    week_trades = backtest_mined(
      fm, strat, signals, oos_start, oos_end,
      spread_pips=spread_pips, slippage_pips=slippage_pips,
    )
    all_oos_trades.extend(week_trades)
    week_m = compute_metrics(week_trades, risk_pct_per_trade)

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

  holdout_trades, holdout_strat = [], None
  if holdout_cutoff is not None:
    holdout_trades, holdout_strat = _run_holdout_forward(
      df, fm, holdout_cutoff, use_learning, train_months, spread_pips, slippage_pips, kb_instance,
    )

  overall = compute_metrics(all_oos_trades, risk_pct_per_trade)
  one_year_ago = df.index[-1] - pd.DateOffset(years=1)
  year_trades = [t for t in all_oos_trades if t.entry_time >= one_year_ago]
  year_m = compute_metrics(year_trades, risk_pct_per_trade)
  traded_weeks = max(len([w for w in weekly_log if w.get("oos_trades", 0) > 0]), 1)
  avg_tpw = overall["n_trades"] / traded_weeks

  holdout_m = compute_metrics(holdout_trades, risk_pct_per_trade) if holdout_trades else None

  def _pack_metrics(m: dict) -> dict:
    return {
      "n_trades": m["n_trades"],
      "trades_per_week": round(avg_tpw, 2) if m is overall else round(m["n_trades"] / max(holdout_months * 4.33, 1), 2),
      "win_rate_pct": round(m["win_rate"] * 100, 2),
      "avg_rr": round(m["avg_rr"], 3),
      "profit_factor": round(m["profit_factor"], 3),
      "total_pips": round(m["total_pips"], 2),
      "total_r": round(m["total_r"], 3),
      "max_drawdown_r": round(m["max_drawdown_r"], 2),
      "max_win_streak": m.get("max_win_streak", 0),
      "max_loss_streak": m.get("max_loss_streak", 0),
      "risk_of_ruin_pct": m.get("risk_of_ruin_pct", 0),
    }

  result = {
    "data_range": {"start": str(df.index[0].date()), "end": str(df.index[-1].date()), "bars": len(df)},
    "oos_start": str(first_trade_date.date()),
    "config": {
      "version": "adaptive_miner_v4",
      "train_months": train_months,
      "target_trades_per_week": TARGET_TRADES_PER_WEEK,
      "pair": "EUR/USD", "tf": "H1",
      "use_learning_kb": use_learning,
      "kb_profile": profile_id if use_learning else None,
      "kb_snapshot": (kb_snapshot if kb_snapshot not in (None, "latest") else "latest") if use_learning else None,
      "kb_validation": kb_validation,
      "oos_from": oos_from,
      "oos_to": oos_to,
      "spread_pips": spread_pips,
      "slippage_pips": slippage_pips,
      "holdout_months": holdout_months,
      "risk_pct_per_trade": risk_pct_per_trade,
      "reopt_period": reopt_period,
      "max_trades_per_day": max_trades_per_day or None,
      "max_hold_bars": max_hold_bars if max_hold_bars is not None else DEFAULT_MAX_HOLD_BARS,
      "min_bars_between": min_bars_between if min_bars_between is not None else DEFAULT_MIN_BARS_BETWEEN,
      "trail_activate_r": (trail_hybrid[0] if trail_hybrid else DEFAULT_TRAIL_ACTIVATE_R),
      "trail_distance_r": (trail_hybrid[1] if trail_hybrid else DEFAULT_TRAIL_DISTANCE_R),
      "trail_hybrid": list(trail_hybrid) if trail_hybrid else [
        DEFAULT_TRAIL_ACTIVATE_R, DEFAULT_TRAIL_DISTANCE_R,
      ],
    },
    "overall_oos": _pack_metrics(overall),
    "last_1_year": _pack_metrics(year_m),
    "constraints_met": {
      "win_rate_above_60": year_m["win_rate"] >= 0.60,
      "rr_above_2": year_m["avg_rr"] >= 2.0,
      "profitable": year_m["total_r"] > 0,
      "trades_per_week_near_2": 1.2 <= avg_tpw <= 3.0,
    },
    "last_strategy": strategy_to_dict(last_strat) if last_strat else None,
    "weekly_log": weekly_log,
    "trades": _trades_to_json(all_oos_trades),
  }

  if holdout_m:
    result["holdout_forward"] = {
      "cutoff": str(holdout_cutoff.date()),
      "months": holdout_months,
      "metrics": _pack_metrics(holdout_m),
      "strategy": holdout_strat,
      "trades": _trades_to_json(holdout_trades),
    }

  return result


def save_backtest_report(result: dict, report_dir: Path = REPORT_DIR) -> Path:
  report_dir.mkdir(exist_ok=True)
  path = report_dir / "backtest_report.json"
  with open(path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
  if result.get("trades"):
    pd.DataFrame(result["trades"]).to_csv(report_dir / "oos_trades.csv", index=False)
  return path


def print_report(r: dict):
  o, y, c = r["overall_oos"], r["last_1_year"], r["constraints_met"]
  print(f"\n{'='*60}\nKẾT QUẢ BACKTEST OOS\n{'='*60}")
  print(f"\n[WF OOS - {o['n_trades']} lệnh | {o['trades_per_week']}/tuần]")
  print(f"  WR: {o['win_rate_pct']}% | RR: {o['avg_rr']} | R: {o['total_r']} | DD: {o['max_drawdown_r']}R")
  if "holdout_forward" in r:
    h = r["holdout_forward"]["metrics"]
    print(f"\n[HOLD-OUT FORWARD - {h['n_trades']} lệnh từ {r['holdout_forward']['cutoff']}]")
    print(f"  WR: {h['win_rate_pct']}% | R: {h['total_r']}R")
  print(f"\n[1 NĂM] WR: {y['win_rate_pct']}% | R: {y['total_r']}R")
  ok = all(c.values())
  print(f"\n{'✓ ĐẠT YÊU CẦU' if ok else '✗ CHƯA ĐẠT'}\n{'='*60}\n")


def main():
  parser = argparse.ArgumentParser(description="Walk-forward EUR/USD backtest")
  parser.add_argument("--no-kb", action="store_true", help="Tắt knowledge base")
  parser.add_argument("--spread", type=float, default=DEFAULT_SPREAD_PIPS)
  parser.add_argument("--slippage", type=float, default=DEFAULT_SLIPPAGE_PIPS)
  parser.add_argument("--holdout-months", type=int, default=DEFAULT_HOLDOUT_MONTHS)
  parser.add_argument("--kb-profile", default=DEFAULT_PROFILE_ID, help="ID KB profile (giai đoạn)")
  parser.add_argument("--kb-epoch", default=None,
                      help="Snapshot epoch (cumulative, vd 2 hoặc 8). Mặc định: latest")
  parser.add_argument("--oos-from", default=None, help="OOS bắt đầu YYYY-MM-DD")
  parser.add_argument("--oos-to", default=None, help="OOS kết thúc YYYY-MM-DD")
  parser.add_argument("--reopt-period", choices=["week", "month"], default="week",
                      help="Tần suất cập nhật chiến lược: week (mặc định) hoặc month")
  args = parser.parse_args()

  df = load_eurusd_h1("2022-01-01")
  print(f"{len(df)} bars: {df.index[0].date()} -> {df.index[-1].date()}")
  kb_snap = int(args.kb_epoch) if args.kb_epoch and args.kb_epoch != "latest" else None
  result = run_walk_forward(
    df, use_learning=not args.no_kb,
    spread_pips=args.spread, slippage_pips=args.slippage,
    holdout_months=args.holdout_months,
    kb_profile=args.kb_profile if not args.no_kb else None,
    kb_snapshot=kb_snap,
    oos_from=args.oos_from, oos_to=args.oos_to,
    reopt_period=args.reopt_period,
  )
  path = save_backtest_report(result)
  print_report(result)
  print(f"Báo cáo: {path}")
  return 0 if all(result["constraints_met"].values()) else 1


if __name__ == "__main__":
  sys.exit(main())
