#!/usr/bin/env python3
"""Diagnose where e21 OOS fills are lost: signals vs trades, IS vs OOS rate.

Grid rows print n=18..28 over a 12-month OOS while presets target 4.5+
trades/week. This walks the same weekly schedule as run_backtest.run_walk_forward
but records, per week, raw signal count and realized trades for both the train
window and the OOS week so the bottleneck (rule gating vs day cap / open
position) is measurable instead of inferred.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env  # noqa: E402


# Named override sets so gates can be ablated one at a time without shell-quoting JSON.
ABLATIONS: dict[str, dict] = {
  "base": {},
  "no_chase": {"anti_chase": False},
  "chase_and": {"anti_chase_logic": "and"},
  "chase_loose": {"anti_chase_fixed_rsi": 68.0, "anti_chase_fixed_vwap": 2.5},
  "no_surgery": {"edge_surgery": False},
  "surgery_side_only": {"edge_surgery_hours": False, "edge_surgery_dominant_side_ratio": 0.75},
  "rules1": {"min_rules_matches": [1, 2]},
  "score_low": {"score_thresholds": [0.4, 0.6, 1.0]},
  "ml_low": {"ml_probability_thresholds": [0.30, 0.34, 0.38]},
  "session_wide": {"session_ranges": [[7, 20]]},
  "spacing8": {"min_bars_between": [8], "max_trades_per_day": 3},
  "tpw_high": {"target_trades_per_week": 8.0},
  # Veto-aware mining: rank genomes on the book that survives anti-chase.
  "veto_aware": {"anti_chase_score_with_veto": True},
  "veto_aware_floor": {
    "anti_chase_score_with_veto": True,
    "min_trades_per_week": 1.5,
    "max_trades_per_day": 2,
    "min_rules_matches": [1, 2],
    "score_thresholds": [0.6, 1.0, 1.6],
  },
  "veto_elite": {
    "anti_chase_score_with_veto": True,
    "min_trades_per_week": 1.5,
    "selection_mode": "elite_frontier",
    "min_rules_matches": [1, 2],
    "score_thresholds": [0.6, 1.0, 1.6],
    "target_trades_per_week": 5.0,
  },
  "veto_elite_rr": {
    "anti_chase_score_with_veto": True,
    "min_trades_per_week": 1.2,
    "selection_mode": "elite_frontier",
    "rr_ratios": [2.8, 3.2],
    "atr_multipliers": [1.2, 1.35],
    "min_rules_matches": [1, 2],
    "score_thresholds": [0.6, 1.0, 1.6],
    "target_trades_per_week": 4.0,
  },
  "veto_aware_floor3": {
    "anti_chase_score_with_veto": True,
    "min_trades_per_week": 3.0,
    "max_trades_per_day": 3,
    "min_bars_between": [8],
    "min_rules_matches": [1, 2],
    "score_thresholds": [0.6, 1.0, 1.6],
    "session_ranges": [[7, 19]],
  },
}


def _bind(desk: str) -> dict:
  cfg = apply_desk_env(desk)
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def main() -> int:
  ap = argparse.ArgumentParser()
  ap.add_argument("--desk", default="e21")
  ap.add_argument("--presets", default="eur_wr55_london,eur_wr55_qty")
  ap.add_argument("--weeks", type=int, default=6)
  ap.add_argument("--oos-from", default="2025-01-01")
  ap.add_argument("--oos-to", default="2025-06-30")
  ap.add_argument("--kb-profile", default="era_2024_full")
  ap.add_argument("--epoch", default="latest")
  ap.add_argument("--no-kb", action="store_true")
  ap.add_argument("--overrides", default="", help="JSON dict merged into each preset space")
  ap.add_argument("--ablations", default="", help="comma list of ABLATIONS names")
  ap.add_argument("--probe", action="store_true", help="stage-by-stage gate rejection counts")
  ap.add_argument("--probe-as-of", default="2025-03-03")
  ap.add_argument("--probe-bars", type=int, default=8000)
  args = ap.parse_args()

  _bind(args.desk)

  import numpy as np
  import pandas as pd

  from config import (
    DEFAULT_SLIPPAGE_PIPS,
    DEFAULT_SPREAD_PIPS,
    DEFAULT_START_DATE,
    DEFAULT_FEATURE_PROFILE,
  )
  from data_loader import (
    get_train_window_indices,
    get_week_indices,
    load_eurusd_m15,
  )
  from feature_engine import FeatureMatrix
  from mining_presets import PRESETS
  from optimizer import get_knowledge_base, optimize_on_window, reset_kb_cache, set_kb_profile
  from run_backtest import generate_weekly_schedule
  from strategy import compute_metrics
  from strategy_miner import (
    backtest_mined,
    generate_signals_mined,
    mining_search_space_from_dict,
  )

  overrides = json.loads(args.overrides) if args.overrides else {}
  df = load_eurusd_m15(DEFAULT_START_DATE)
  fm = FeatureMatrix(df, profile=DEFAULT_FEATURE_PROFILE)
  print(f"data bars={len(df)} {df.index[0]} -> {df.index[-1]}", flush=True)

  first = pd.Timestamp(args.oos_from)
  first -= pd.Timedelta(days=first.weekday())
  weeks = generate_weekly_schedule(df, first, pd.Timestamp(args.oos_to))
  weeks = [w for w in weeks if w[0] >= pd.Timestamp(args.oos_from)]
  print(f"oos weeks={len(weeks)}", flush=True)

  abl_names = [a.strip() for a in args.ablations.split(",") if a.strip()] or [""]
  runs: list[tuple[str, dict]] = []
  for preset in [p.strip() for p in args.presets.split(",") if p.strip()]:
    for abl in abl_names:
      extra = ABLATIONS[abl] if abl else {}
      label = f"{preset}+{abl}" if abl else preset
      runs.append((label, {**PRESETS[preset], **extra, **overrides}))

  if args.probe:
    from strategy_miner import _count_matching_rules, _htf_bias, _pa_confluence_bonus
    as_of = pd.Timestamp(args.probe_as_of)
    t0, t1 = get_train_window_indices(df, as_of, args.weeks)
    hours = getattr(fm, "broker_hours", None)
    if hours is None:
      hours = fm.hours
    for name, space_dict in runs:
      space = mining_search_space_from_dict(space_dict)
      reset_kb_cache()
      kb = None
      if not args.no_kb:
        snap = None if args.epoch == "latest" else int(args.epoch)
        set_kb_profile(args.kb_profile, snap)
        kb = get_knowledge_base(args.kb_profile, snap)
      strat = optimize_on_window(
        fm, t0, t1, use_learning=not args.no_kb, as_of=as_of, kb=kb, search_space=space,
      )
      if strat is None:
        print(f"{name}: no strategy", flush=True)
        continue
      ml_l = strat.ml_scorer._prob_long if strat.ml_scorer is not None else None
      ml_s = strat.ml_scorer._prob_short if strat.ml_scorer is not None else None
      blocked = set(int(h) for h in (getattr(strat, "blocked_hours", ()) or ()))
      c = dict(bars=0, session=0, blocked=0, rules=0, score=0, ml=0, cand=0, chase=0)
      end = min(t1 + args.probe_bars, fm.n - 1)
      for i in range(t1, end):
        c["bars"] += 1
        if strat.session_filter and not (
          strat.session_start_hour <= hours[i] <= strat.session_end_hour
        ):
          c["session"] += 1
          continue
        if blocked and int(hours[i]) in blocked:
          c["blocked"] += 1
          continue
        ls, lc = _count_matching_rules(fm, strat.long_rules, i)
        ss, sc = _count_matching_rules(fm, strat.short_rules, i)
        pl = float(ml_l[i]) if ml_l is not None else 0.5
        ps = float(ml_s[i]) if ml_s is not None else 0.5
        cl = ls * (0.5 + pl) * _htf_bias(fm, i, 1, strat) + _pa_confluence_bonus(fm, i, 1)
        cs = ss * (0.5 + ps) * _htf_bias(fm, i, -1, strat) + _pa_confluence_bonus(fm, i, -1)
        long_ok = bool(getattr(strat, "allow_long", True)) and lc >= strat.min_rules_match
        short_ok = bool(getattr(strat, "allow_short", True)) and sc >= strat.min_rules_match
        if not (long_ok or short_ok):
          c["rules"] += 1
          continue
        if not ((long_ok and cl >= strat.score_threshold) or (short_ok and cs >= strat.score_threshold)):
          c["score"] += 1
          continue
        take_long = long_ok and cl >= strat.score_threshold and cl > cs
        if not ((take_long and pl >= strat.ml_prob_min) or ((not take_long) and ps >= strat.ml_prob_min)):
          c["ml"] += 1
          continue
        c["cand"] += 1
      sig = generate_signals_mined(fm, strat, t1, end)
      kept = int(np.count_nonzero(sig[t1:end]))
      weeks_span = c["bars"] / (7 * 24 * 4)
      print(
        f"\n=== PROBE {name} · {strat.name} ===\n"
        f"  thr={strat.score_threshold} min_match={strat.min_rules_match} "
        f"ml_min={strat.ml_prob_min} mtd={strat.max_trades_per_day} "
        f"spacing={strat.min_bars_between} rules L/S={len(strat.long_rules)}/{len(strat.short_rules)}\n"
        f"  allow L/S={strat.allow_long}/{strat.allow_short} blocked_hours={sorted(blocked)}\n"
        f"  bars={c['bars']} (~{weeks_span:.1f}w) reject: session={c['session']} "
        f"blocked={c['blocked']} rules={c['rules']} score={c['score']} ml={c['ml']}\n"
        f"  candidates={c['cand']} ({c['cand'] / max(weeks_span, 0.1):.1f}/wk) "
        f"-> after daycap+chase signals={kept} ({kept / max(weeks_span, 0.1):.2f}/wk)",
        flush=True,
      )
    return 0

  for name, space_dict in runs:
    space = mining_search_space_from_dict(space_dict)

    reset_kb_cache()
    kb = None
    if not args.no_kb:
      snap = None if args.epoch == "latest" else int(args.epoch)
      set_kb_profile(args.kb_profile, snap)
      kb = get_knowledge_base(args.kb_profile, snap)

    is_sig = is_trades = os_sig = 0
    oos_trades: list = []
    prev = None
    skipped = 0
    is_weeks = 0
    for week_start, week_end in weeks:
      t0, t1 = get_train_window_indices(df, week_start, args.weeks)
      if t0 is None:
        skipped += 1
        continue
      strat = optimize_on_window(
        fm, t0, t1, use_learning=not args.no_kb, as_of=week_start,
        kb=kb, search_space=space,
      )
      if strat is None:
        strat = prev
      if strat is None:
        skipped += 1
        continue
      prev = strat

      o0, o1 = get_week_indices(df, week_start, week_end)
      if o0 is None:
        skipped += 1
        continue

      tr_sig = generate_signals_mined(fm, strat, t0, t1)
      tr_trades = backtest_mined(
        fm, strat, tr_sig, t0, t1,
        spread_pips=DEFAULT_SPREAD_PIPS, slippage_pips=DEFAULT_SLIPPAGE_PIPS,
      )
      is_sig += int(np.count_nonzero(tr_sig[t0:t1]))
      is_trades += len(tr_trades)
      is_weeks += args.weeks

      sig = generate_signals_mined(fm, strat, o0, o1)
      os_sig += int(np.count_nonzero(sig[o0:o1]))
      wk = backtest_mined(
        fm, strat, sig, o0, o1,
        spread_pips=DEFAULT_SPREAD_PIPS, slippage_pips=DEFAULT_SLIPPAGE_PIPS,
      )
      oos_trades.extend(wk)

    m = compute_metrics(oos_trades)
    n_weeks = max(len(weeks) - skipped, 1)
    print(
      f"\n=== {name} (weeks={args.weeks} kb={'off' if args.no_kb else args.kb_profile}) ===\n"
      f"  IS  : sig={is_sig} trades={is_trades} "
      f"sig/wk={is_sig / max(is_weeks, 1):.2f} trades/wk={is_trades / max(is_weeks, 1):.2f}\n"
      f"  OOS : sig={os_sig} trades={m['n_trades']} "
      f"sig/wk={os_sig / n_weeks:.2f} trades/wk={m['n_trades'] / n_weeks:.2f}\n"
      f"  OOS : WR={m['win_rate'] * 100:.1f} RR={m['avg_rr']:.2f} R={m['total_r']:.1f} "
      f"eval_weeks={n_weeks} skipped={skipped}",
      flush=True,
    )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
