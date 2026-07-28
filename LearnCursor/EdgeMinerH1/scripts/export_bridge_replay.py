#!/usr/bin/env python3
"""
Export Best-3m walk-forward decisions for ForgeBridge Replay mode (MT5 tester compare).

Writes:
  mt5/bridge/replay_decisions.json  — full payload
  mt5/bridge/replay_signals.csv     — EA-friendly rows

Usage:
  python scripts/export_bridge_replay.py
  python scripts/export_bridge_replay.py --oos-from 2025-01-01 --oos-to 2026-07-20
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import get_train_window_indices, get_week_indices, load_eurusd_h1
from feature_engine import FeatureMatrix
from kb_profiles import load_kb
from mt5_bridge.models import DEFAULT_MODEL_ID, get_model_run_params, resolve_model
from mt5_bridge.protocol import (
  BRIDGE_DIR,
  ensure_bridge_dir,
  replay_csv_path,
  replay_path,
)
from optimizer import optimize_on_window, reset_kb_cache, set_kb_profile
from run_backtest import generate_weekly_schedule
from strategy import compute_metrics
from strategy_miner import generate_signals_mined, backtest_mined


def _exit_code(mode: str) -> int:
  # Match scripts/generate_wf_ea.py exit_map
  return {"full": 0, "hybrid": 1, "trail": 2, "partial": 3}.get((mode or "trail").lower(), 2)


def _fmt_bar(ts) -> str:
  return pd.Timestamp(ts).strftime("%Y.%m.%d %H:%M")


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--model-id", default=DEFAULT_MODEL_ID)
  ap.add_argument("--oos-from", default=None)
  ap.add_argument("--oos-to", default=None)
  ap.add_argument("--bridge-dir", type=Path, default=BRIDGE_DIR)
  ap.add_argument("--spread", type=float, default=None)
  ap.add_argument("--slippage", type=float, default=None)
  args = ap.parse_args()

  model = resolve_model(args.model_id)
  params = get_model_run_params(model, args.model_id)
  train_months = int(params["train_months"])
  kb_profile = params["kb_profile"]
  kb_snapshot = params["kb_snapshot"]
  spread = float(args.spread if args.spread is not None else params["spread_pips"])
  slip = float(args.slippage if args.slippage is not None else params["slippage_pips"])
  oos_from = pd.Timestamp(args.oos_from or params.get("oos_from") or "2025-01-01")
  oos_to = pd.Timestamp(args.oos_to or params.get("oos_to") or "2026-12-31")

  reset_kb_cache()
  set_kb_profile(kb_profile, kb_snapshot)
  kb = load_kb(kb_profile, kb_snapshot)

  df = load_eurusd_h1()
  fm = FeatureMatrix(df)
  weeks = generate_weekly_schedule(df, oos_from, min(oos_to, df.index[-1]))
  weeks = [w for w in weeks if w[0] >= oos_from and w[0] <= oos_to]

  signals: list[dict] = []
  weekly: list[dict] = []
  all_trades = []
  prev = None

  print(
    f"Export bridge replay | model={params.get('trade_model_id')} "
    f"weeks={len(weeks)} KB={kb_profile}@{kb_snapshot} train={train_months}m"
  )
  for week_start, week_end in tqdm(weeks, desc="Bridge replay"):
    ts, te = get_train_window_indices(df, week_start, train_months)
    if ts is None or (te - ts) < 200:
      weekly.append({"week_start": str(week_start.date()), "status": "skip_train"})
      continue
    strat = optimize_on_window(
      fm, ts, te, use_learning=True, as_of=week_start, kb=kb,
    )
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
      fm, strat, sig, oos_s, oos_e, spread_pips=spread, slippage_pips=slip,
    )
    all_trades.extend(trades)
    m = compute_metrics(trades)

    for tr in trades:
      entry_ts = pd.Timestamp(tr.entry_time)
      ei = int(fm.index.searchsorted(entry_ts))
      si = max(ei - 1, 0)
      signals.append({
        "t": _fmt_bar(fm.index[si]),
        "d": int(tr.direction),
        "atr_m": float(strat.atr_mult_sl),
        "rr": float(strat.rr_ratio),
        "exit": _exit_code(strat.exit_mode),
        "exit_mode": strat.exit_mode,
        "trail_act": float(strat.trail_activate_r),
        "trail_dist": float(strat.trail_distance_r),
        "max_hold": int(strat.max_hold_bars),
      })

    weekly.append({
      "week_start": str(week_start.date()),
      "week_end": str(week_end.date()),
      "strategy": strat.name,
      "oos_trades": m["n_trades"],
      "oos_r": round(m["total_r"], 3),
    })

  overall = compute_metrics(all_trades)
  bridge_dir = ensure_bridge_dir(args.bridge_dir)
  payload = {
    "meta": {
      "source": "ForgeBridge replay export",
      "model_id": params.get("trade_model_id"),
      "label": params.get("label"),
      "train_months": train_months,
      "kb_profile": kb_profile,
      "kb_snapshot": kb_snapshot,
      "oos_from": str(oos_from.date()),
      "oos_to": str(oos_to.date()),
      "spread_pips": spread,
      "slippage_pips": slip,
      "n_signals": len(signals),
      "overall": {
        "n_trades": overall["n_trades"],
        "win_rate_pct": round(overall["win_rate"] * 100, 2),
        "total_r": round(overall["total_r"], 3),
        "profit_factor": round(overall["profit_factor"], 3),
        "max_drawdown_r": round(overall["max_drawdown_r"], 2),
      },
    },
    "weekly": weekly,
    "signals": signals,
  }
  out_json = replay_path(bridge_dir)
  out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

  out_csv = replay_csv_path(bridge_dir)
  with open(out_csv, "w", encoding="utf-8", newline="\n") as f:
    w = csv.writer(f)
    w.writerow(["t", "d", "atr_m", "rr", "exit", "trail_act", "trail_dist", "max_hold"])
    for s in signals:
      w.writerow([
        s["t"], s["d"], f"{s['atr_m']:.6f}", f"{s['rr']:.4f}",
        s["exit"], f"{s['trail_act']:.4f}", f"{s['trail_dist']:.4f}", s["max_hold"],
      ])

  print(f"Wrote {out_json}")
  print(f"Wrote {out_csv}")
  print(
    f"Signals={len(signals)} trades={overall['n_trades']} "
    f"total_r={overall['total_r']:+.2f} WR={overall['win_rate']*100:.1f}%"
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
