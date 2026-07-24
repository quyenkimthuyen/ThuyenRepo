#!/usr/bin/env python3
"""Backtest the FROZEN last_strategy (no weekly remine, no ML) for fair MT5 comparison."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_loader import load_eurusd_m15
from feature_engine import FeatureMatrix
from strategy import compute_metrics
from strategy_miner import MinedStrategy, Rule, generate_signals_mined, backtest_mined

FROZEN = ROOT / "mt5" / "frozen" / "best_3m_frozen.json"


def main():
  snap = json.loads(FROZEN.read_text(encoding="utf-8"))
  s = snap["strategy"]

  def rules(lst):
    return [Rule(r["feat"], "long" if "long" in str(lst) else "short", r["op"], float(r["thr"]), float(r["w"]))
            for r in lst]

  # Rule.direction is unused in matching; feature/op/threshold/weight matter
  long_rules = [Rule(r["feat"], "long", r["op"], float(r["thr"]), float(r["w"])) for r in s["long_rules"]]
  short_rules = [Rule(r["feat"], "short", r["op"], float(r["thr"]), float(r["w"])) for r in s["short_rules"]]

  strat = MinedStrategy(
    long_rules=long_rules,
    short_rules=short_rules,
    score_threshold=float(s["score_threshold"]),
    atr_mult_sl=float(s["atr_mult_sl"]),
    rr_ratio=float(s["rr"]),
    max_hold_bars=int(s.get("max_hold_bars", 36)),
    min_bars_between=int(s.get("min_bars_between", 4)),
    min_rules_match=int(s.get("min_rules_match", 2)),
    max_trades_per_day=int(s.get("max_trades_per_day", 2)),
    ml_prob_min=float(s.get("ml_prob_min", 0.3)),
    exit_mode=str(s.get("exit_mode", "hybrid")),
    trail_activate_r=float(s.get("trail_activate_r", 1.8)),
    trail_distance_r=float(s.get("trail_distance_r", 0.6)),
    session_filter=bool(s.get("session_filter", True)),
    ml_scorer=None,  # frozen: ML off → prob=0.5
    name=str(s.get("name", "frozen")),
  )

  df = load_eurusd_m15()
  fm = FeatureMatrix(df)

  windows = [
    ("2025 full", "2025-01-01", "2025-12-31"),
    ("OOS app window", "2025-01-01", "2026-07-20"),
  ]

  print(f"Frozen strategy: {strat.name}")
  print(f"RR={strat.rr_ratio} ATRx={strat.atr_mult_sl:.4f} exit={strat.exit_mode} thr={strat.score_threshold:.4f}")
  print("(no weekly remine, no ML, no KB)\n")

  for label, a, b in windows:
    i0 = fm.index.searchsorted(a)
    i1 = fm.index.searchsorted(b)
    if i1 <= i0:
      print(f"{label}: no bars")
      continue
    sig = generate_signals_mined(fm, strat, i0, i1)
    trades = backtest_mined(fm, strat, sig, i0, i1, spread_pips=1.0, slippage_pips=0.3)
    m = compute_metrics(trades)
    print(f"=== FROZEN Python · {label} ({a} → {b}) ===")
    print(f"  trades={m['n_trades']}  WR={m['win_rate']*100:.2f}%  PF={m['profit_factor']:.3f}")
    print(f"  total_r={m['total_r']:+.3f}  maxDD_r={m['max_drawdown_r']:.2f}  pips={m['total_pips']:.1f}")
    print()


if __name__ == "__main__":
  main()
