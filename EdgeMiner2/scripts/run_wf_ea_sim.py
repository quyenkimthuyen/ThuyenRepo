#!/usr/bin/env python3
"""Simulate ForgeBest3m_WF EA on Dukascopy H1 (same calendar + costs as export)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_h1
from feature_engine import FeatureMatrix
from strategy import Trade, compute_metrics
from strategy_miner import MinedStrategy, backtest_mined
from execution import adjust_entry_price, adjust_exit_price

SCHEDULE = ROOT / "mt5" / "frozen" / "best_3m_wf_schedule.json"


def main():
  sched = json.loads(SCHEDULE.read_text(encoding="utf-8"))
  meta = sched["meta"]
  signals = sched["signals"]

  df = load_eurusd_h1()
  fm = FeatureMatrix(df)
  # Build signal array
  import numpy as np
  sig = np.zeros(fm.n, dtype=np.int8)

  # Use one strategy template; per-signal params applied in custom loop
  # Custom backtest respecting per-signal atr/rr/exit
  o = fm.open; h = fm.high; l = fm.low; c = fm.close; atr = fm.atr
  spread, slip = float(meta["spread_pips"]), float(meta["slippage_pips"])

  # Map signal times
  sig_map = {}
  for s in signals:
    t = pd.Timestamp(s["t"])
    i = int(fm.index.searchsorted(t))
    if i < fm.n and fm.index[i] == t:
      sig_map[i] = s
      sig[i] = int(s["d"])

  trades = []
  i = fm.warmup
  end = fm.n - 1
  in_trade = False
  direction = entry_price = sl = tp = risk = 0.0
  entry_idx = 0
  trail_active = 0.0
  exit_mode = "hybrid"
  trail_act = 1.8
  trail_dist = 0.6
  max_hold = 36
  rr = 3.0

  while i < end:
    if in_trade:
      hit_sl = hit_tp = False
      if exit_mode in ("trail", "hybrid") and not trail_active:
        if direction == 1 and h[i] >= entry_price + risk * trail_act:
          trail_active = 1.0
          sl = max(sl, h[i] - risk * trail_dist)
        elif direction == -1 and l[i] <= entry_price - risk * trail_act:
          trail_active = 1.0
          sl = min(sl, l[i] + risk * trail_dist)
      elif exit_mode in ("trail", "hybrid") and trail_active:
        if direction == 1:
          sl = max(sl, h[i] - risk * trail_dist)
        else:
          sl = min(sl, l[i] + risk * trail_dist)

      exit_price = c[i]
      if direction == 1:
        if l[i] <= sl:
          hit_sl, exit_price = True, sl
        elif h[i] >= tp:
          hit_tp, exit_price = True, tp
      else:
        if h[i] >= sl:
          hit_sl, exit_price = True, sl
        elif l[i] <= tp:
          hit_tp, exit_price = True, tp

      if hit_sl or hit_tp or (i - entry_idx) >= max_hold:
        reason = "tp" if hit_tp else ("trail" if trail_active and hit_sl else "sl")
        if not hit_sl and not hit_tp:
          exit_price, reason = c[i], "timeout"
        exit_price = adjust_exit_price(exit_price, int(direction), spread, slip)
        pnl_r = (exit_price - entry_price) * direction / risk if risk > 0 else 0
        trades.append(Trade(
          fm.index[entry_idx], fm.index[i], int(direction),
          entry_price, exit_price, sl, tp, pnl_r * risk * 10000, pnl_r, reason,
        ))
        in_trade = False
        trail_active = 0.0
      i += 1
      continue

    if i in sig_map:
      s = sig_map[i]
      av = atr[i]
      if av == av and av > 0:
        entry_idx = i + 1
        if entry_idx >= end:
          break
        direction = float(s["d"])
        entry_price = adjust_entry_price(o[entry_idx], int(direction), spread, slip)
        risk = float(s["atr_m"]) * av
        rr = float(s["rr"])
        exit_mode = str(s.get("exit") or "hybrid")
        trail_act = float(s.get("trail_act") or 1.8)
        trail_dist = float(s.get("trail_dist") or 0.6)
        max_hold = int(s.get("max_hold") or 36)
        if direction > 0:
          sl, tp = entry_price - risk, entry_price + risk * rr
        else:
          sl, tp = entry_price + risk, entry_price - risk * rr
        in_trade = True
        i = entry_idx
        continue
    i += 1

  m = compute_metrics(trades)
  print("=== ForgeBest3m_WF simulation (Dukascopy H1, same calendar as EA) ===")
  print(f"Period: {meta['oos_from']} -> {meta['oos_to']}")
  print(f"Spread={spread} slip={slip}")
  print(f"Signals in calendar: {len(signals)}")
  print(f"Trades: {m['n_trades']}")
  print(f"Win rate: {m['win_rate']*100:.2f}%")
  print(f"Profit factor: {m['profit_factor']:.3f}")
  print(f"Total R: {m['total_r']:+.3f}")
  print(f"Max DD R: {m['max_drawdown_r']:.2f}")
  print(f"Total pips: {m['total_pips']:.1f}")
  print(f"Avg RR: {m['avg_rr']:.3f}")

  # Compare app
  app_path = ROOT / "results" / "trade_models" / "tm_best_3m_64e3f742.json"
  if app_path.exists():
    app = json.loads(app_path.read_text())["overall_oos"]
    print("\n=== vs App Best 3m overall_oos ===")
    print(f"App:   R={app['total_r']:+.3f}  WR={app['win_rate_pct']}%  trades={app['n_trades']}  PF={app['profit_factor']}")
    print(f"EA-sim: R={m['total_r']:+.3f}  WR={m['win_rate']*100:.2f}%  trades={m['n_trades']}  PF={m['profit_factor']:.3f}")


if __name__ == "__main__":
  main()
