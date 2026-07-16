"""
Adaptive strategy miner v3 — rules + ML filter + smart exits.
"""
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from feature_engine import FeatureMatrix
from ml_scorer import MLScorer
from strategy import Trade, compute_metrics

LABEL_CACHE: dict[tuple, tuple] = {}


@dataclass
class Rule:
  feature: str
  direction: str
  op: str
  threshold: float
  weight: float = 1.0


@dataclass
class MinedStrategy:
  long_rules: list[Rule] = field(default_factory=list)
  short_rules: list[Rule] = field(default_factory=list)
  score_threshold: float = 2.0
  atr_mult_sl: float = 0.9
  rr_ratio: float = 2.5
  max_hold_bars: int = 36
  min_bars_between: int = 4
  min_rules_match: int = 2
  max_trades_per_week: int = 2
  ml_prob_min: float = 0.40
  exit_mode: str = "trail"       # full | partial | trail
  partial_pct: float = 0.4
  partial_at_r: float = 1.2
  trail_activate_r: float = 1.0
  trail_distance_r: float = 0.5
  session_filter: bool = True
  ml_scorer: MLScorer | None = None
  name: str = "mined_v3"


CONTINUOUS_FEATURES = [
  "rsi", "adx", "bb_pos", "bb_width_pct", "atr_pct", "zscore_20",
  "price_vs_ema21", "price_vs_ema50", "ema_slope_8", "ema_slope_21",
  "macd_hist", "roc_5", "body_ratio", "lower_wick_ratio", "upper_wick_ratio",
]
BINARY_LONG = ["sweep_low_fade", "squeeze_break_up", "pullback_long", "range_buy",
               "engulf_bull", "macd_cross_up", "ema_stack_bull"]
BINARY_SHORT = ["sweep_high_fade", "squeeze_break_dn", "pullback_short", "range_sell",
                "engulf_bear", "macd_cross_dn", "ema_stack_bear"]


def _label_outcomes(fm, start, end, rr=2.5, atr_mult=0.9):
  key = (start, end, rr, atr_mult)
  if key in LABEL_CACHE:
    return LABEL_CACHE[key]

  long_win = np.zeros(fm.n, dtype=np.int8)
  short_win = np.zeros(fm.n, dtype=np.int8)
  o, h, l, atr_v = fm.open, fm.high, fm.low, fm.atr
  max_hold = 36
  last_i = min(end - max_hold - 2, fm.n - max_hold - 2)

  for i in range(start, last_i):
    av = atr_v[i]
    if np.isnan(av) or av <= 0:
      continue
    entry = o[i + 1]
    sl_d = atr_mult * av
    lsl, ltp = entry - sl_d, entry + sl_d * rr
    ssl, stp = entry + sl_d, entry - sl_d * rr
    j_end = min(i + 2 + max_hold, end)

    for j in range(i + 2, j_end):
      if l[j] <= lsl:
        break
      if h[j] >= ltp:
        long_win[i] = 1
        break
    for j in range(i + 2, j_end):
      if h[j] >= ssl:
        break
      if l[j] <= stp:
        short_win[i] = 1
        break

  LABEL_CACHE[key] = (long_win, short_win)
  return long_win, short_win


def _mine_threshold_rules(fm, feat_name, direction, wins, start, end, top_n=3):
  feat = fm.get(feat_name)
  rules = []
  valid = np.zeros(fm.n, dtype=bool)
  valid[start:end] = True
  valid[:fm.warmup] = False
  valid &= ~np.isnan(feat)
  if valid.sum() < 30:
    return []
  baseline = wins[valid].mean()
  min_wr = max(baseline + 0.05, 0.32)
  for pct in [20, 35, 50, 65, 80]:
    thr = np.nanpercentile(feat[valid], pct)
    for op in ("gt", "lt"):
      cond = valid & (feat > thr if op == "gt" else feat < thr)
      if cond.sum() < 10:
        continue
      wr = wins[cond].mean()
      lift = wr - baseline
      if lift > 0.03 and wr >= min_wr:
        rules.append((lift * 15 + wr * 8, Rule(feat_name, direction, op, thr, weight=lift * 10)))
  rules.sort(key=lambda x: x[0], reverse=True)
  return [r for _, r in rules[:top_n]]


def _mine_binary_rules(fm, feat_names, direction, wins, start, end):
  rules = []
  valid = np.zeros(fm.n, dtype=bool)
  valid[start:end] = True
  valid[:fm.warmup] = False
  baseline = wins[valid].mean() if valid.sum() > 0 else 0.28
  for name in feat_names:
    feat = fm.get(name)
    cond = valid & (feat > 0.5)
    if cond.sum() < 8:
      continue
    wr = wins[cond].mean()
    lift = wr - baseline
    if lift > 0.025 and wr >= max(baseline + 0.04, 0.32):
      rules.append(Rule(name, direction, "eq1", 0.5, weight=max(lift, 0.04) * 12))
  rules.sort(key=lambda r: r.weight, reverse=True)
  return rules[:6]


def _count_matching_rules(fm, rules, i):
  score, count = 0.0, 0
  for r in rules:
    v = fm.get(r.feature)[i]
    if np.isnan(v):
      continue
    ok = (r.op == "eq1" and v > 0.5) or (r.op == "gt" and v > r.threshold) or (r.op == "lt" and v < r.threshold)
    if ok:
      score += r.weight
      count += 1
  return score, count


def generate_signals_mined(fm, strat, start_idx=0, end_idx=None):
  if end_idx is None:
    end_idx = fm.n
  signals = np.zeros(fm.n, dtype=np.int8)
  candidates = []

  ml_l_arr = strat.ml_scorer._prob_long if strat.ml_scorer and strat.ml_scorer._prob_long is not None else None
  ml_s_arr = strat.ml_scorer._prob_short if strat.ml_scorer and strat.ml_scorer._prob_short is not None else None

  for i in range(max(start_idx, fm.warmup), end_idx - 1):
    if strat.session_filter and not (7 <= fm.hours[i] <= 20):
      continue

    ls, lc = _count_matching_rules(fm, strat.long_rules, i)
    ss, sc = _count_matching_rules(fm, strat.short_rules, i)

    ml_l = float(ml_l_arr[i]) if ml_l_arr is not None else 0.5
    ml_s = float(ml_s_arr[i]) if ml_s_arr is not None else 0.5

    # Kết hợp rule score + ML probability
    combined_l = ls * (0.5 + ml_l)
    combined_s = ss * (0.5 + ml_s)

    if lc >= strat.min_rules_match and combined_l >= strat.score_threshold and combined_l > combined_s:
      if ml_l >= strat.ml_prob_min:
        candidates.append((combined_l + ml_l * 2, 1, i))
    elif sc >= strat.min_rules_match and combined_s >= strat.score_threshold and combined_s > combined_l:
      if ml_s >= strat.ml_prob_min:
        candidates.append((combined_s + ml_s * 2, -1, i))

  if candidates and strat.max_trades_per_week > 0:
    week_buckets: dict[str, list] = {}
    for score, direction, i in candidates:
      wk = fm.index[i].strftime("%Y-%W")
      week_buckets.setdefault(wk, []).append((score, direction, i))
    for items in week_buckets.values():
      items.sort(key=lambda x: x[0], reverse=True)
      last_bar = -strat.min_bars_between - 1
      taken = 0
      for score, direction, i in items:
        if taken >= strat.max_trades_per_week:
          break
        if i - last_bar >= strat.min_bars_between:
          signals[i] = direction
          last_bar = i
          taken += 1
  return signals


def backtest_mined(
  fm, strat, signals, start_idx=0, end_idx=None,
  spread_pips: float = 0.0, slippage_pips: float = 0.0,
):
  from execution import adjust_entry_price, adjust_exit_price

  if end_idx is None:
    end_idx = fm.n
  o, h, l, c, atr_v = fm.open, fm.high, fm.low, fm.close, fm.atr
  trades = []
  i = max(start_idx, fm.warmup)
  in_trade = False
  direction = entry_price = sl = tp = risk = 0.0
  entry_idx = partial_done = trail_active = 0.0

  while i < end_idx - 1:
    if in_trade:
      exit_price = c[i]
      hit_sl = hit_tp = False

      # Hybrid: trail chỉ sau khi gần TP (bảo vệ lợi nhuận, không cắt sớm)
      if strat.exit_mode in ("trail", "hybrid") and not partial_done:
        act = strat.trail_activate_r
        if direction == 1 and h[i] >= entry_price + risk * act:
          trail_active = 1.0
          sl = max(sl, h[i] - risk * strat.trail_distance_r)
        elif direction == -1 and l[i] <= entry_price - risk * act:
          trail_active = 1.0
          sl = min(sl, l[i] + risk * strat.trail_distance_r)

      # Partial TP
      if strat.exit_mode == "partial" and not partial_done:
        if direction == 1 and h[i] >= entry_price + risk * strat.partial_at_r:
          partial_done = 1.0
          sl = entry_price + risk * 0.1
        elif direction == -1 and l[i] <= entry_price - risk * strat.partial_at_r:
          partial_done = 1.0
          sl = entry_price - risk * 0.1

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

      if hit_sl or hit_tp or (i - entry_idx) >= strat.max_hold_bars:
        reason = "tp" if hit_tp else ("trail" if trail_active and hit_sl else "sl")
        if not hit_sl and not hit_tp:
          exit_price, reason = c[i], "timeout"

        exit_price = adjust_exit_price(exit_price, int(direction), spread_pips, slippage_pips)

        if strat.exit_mode == "partial" and partial_done:
          pnl_r = strat.partial_pct * strat.partial_at_r
          rem = (exit_price - entry_price) * direction / risk if risk > 0 else 0
          pnl_r += (1 - strat.partial_pct) * rem
          if hit_tp:
            pnl_r = strat.partial_pct * strat.partial_at_r + (1 - strat.partial_pct) * strat.rr_ratio
        else:
          pnl_r = (exit_price - entry_price) * direction / risk if risk > 0 else 0

        trades.append(Trade(
          fm.index[entry_idx], fm.index[i], int(direction),
          entry_price, exit_price, sl, tp, pnl_r * risk * 10000, pnl_r, reason,
        ))
        in_trade = False
        partial_done = trail_active = 0.0
      i += 1
      continue

    sig = signals[i]
    if sig != 0:
      av = atr_v[i]
      if np.isnan(av) or av <= 0:
        i += 1
        continue
      entry_idx = i + 1
      if entry_idx >= end_idx:
        break
      entry_price = adjust_entry_price(o[entry_idx], int(sig), spread_pips, slippage_pips)
      sl_d = strat.atr_mult_sl * av
      direction = float(sig)
      risk = sl_d
      partial_done = trail_active = 0.0
      if direction == 1:
        sl, tp = entry_price - sl_d, entry_price + sl_d * strat.rr_ratio
      else:
        sl, tp = entry_price + sl_d, entry_price - sl_d * strat.rr_ratio
      in_trade = True
      i = entry_idx + 1
      continue
    i += 1
  return trades


def _weeks_in_window(start, end):
  return max((end - start) / 168.0, 1.0)


def score_strategy_metrics(m, weeks, target_tpw=2.0):
  if m["n_trades"] < 3:
    return -1e6
  tpw = m["n_trades"] / weeks
  wr, rr, tr, pf = m["win_rate"], m["avg_rr"], m["total_r"], m["profit_factor"]
  freq_score = 55 - abs(tpw - target_tpw) * 30
  if tpw < 0.8:
    freq_score -= 50
  if tpw > 4:
    freq_score -= 40

  s = wr * 150 + min(rr, 4) * 55 + min(pf, 4) * 12 + tr * 8 + freq_score
  if wr >= 0.55 and rr >= 1.9:
    s += 80
  if wr >= 0.58 and rr >= 2.0:
    s += 130
  if wr >= 0.60 and rr >= 2.0:
    s += 80
  if rr >= 2.0:
    s += 40
  if rr < 1.7:
    s -= (1.7 - rr) * 100
  if wr < 0.40:
    s -= (0.40 - wr) * 180
  if tr <= 0:
    s -= 40
  return s


def mine_strategy(fm, train_start, train_end, target_tpw=2.0):
  global LABEL_CACHE
  if len(LABEL_CACHE) > 200:
    LABEL_CACHE.clear()

  span = train_end - train_start
  split = train_start + int(span * 0.65)
  weeks = _weeks_in_window(train_start, train_end)

  best = best_fallback = None
  best_score = best_fallback_score = -1e9

  exit_modes = [("full", {}),
                ("hybrid", {"trail_activate_r": 1.8, "trail_distance_r": 0.6}),
                ("partial", {"partial_pct": 0.35, "partial_at_r": 1.5})]

  for rr in [2.5, 3.0]:
    for atr_m in [0.9, 1.05]:
      long_wins, short_wins = _label_outcomes(fm, train_start, train_end, rr, atr_m)

      ml = MLScorer()
      ml.fit(fm, train_start, train_end, long_wins, short_wins)

      long_rules, short_rules = [], []
      for feat in CONTINUOUS_FEATURES:
        long_rules.extend(_mine_threshold_rules(fm, feat, "long", long_wins, train_start, train_end, 2))
        short_rules.extend(_mine_threshold_rules(fm, feat, "short", short_wins, train_start, train_end, 2))
      long_rules.extend(_mine_binary_rules(fm, BINARY_LONG, "long", long_wins, train_start, train_end))
      short_rules.extend(_mine_binary_rules(fm, BINARY_SHORT, "short", short_wins, train_start, train_end))
      long_rules = sorted(long_rules, key=lambda r: r.weight, reverse=True)[:6]
      short_rules = sorted(short_rules, key=lambda r: r.weight, reverse=True)[:6]

      for name in ["sweep_low_fade", "pullback_long"]:
        if len(long_rules) < 2:
          long_rules.append(Rule(name, "long", "eq1", 0.5, weight=0.4))
      for name in ["sweep_high_fade", "pullback_short"]:
        if len(short_rules) < 2:
          short_rules.append(Rule(name, "short", "eq1", 0.5, weight=0.4))

      for exit_mode, exit_kw in exit_modes:
        for thr in [0.6, 1.0, 1.6, 2.2]:
          for min_match in [1, 2]:
            for ml_thr in [0.36, 0.40, 0.44, 0.48]:
              strat = MinedStrategy(
                long_rules=long_rules, short_rules=short_rules,
                score_threshold=thr, atr_mult_sl=atr_m, rr_ratio=rr,
                min_bars_between=4, min_rules_match=min_match,
                max_trades_per_week=2, ml_prob_min=ml_thr,
                exit_mode=exit_mode, ml_scorer=ml,
                name=f"v3_{exit_mode}_rr{rr}",
                **exit_kw,
              )
              sig = generate_signals_mined(fm, strat, train_start, train_end)
              fit_trades = backtest_mined(fm, strat, sig, train_start, split)
              val_trades = backtest_mined(fm, strat, sig, split, train_end)
              comb = compute_metrics(fit_trades + val_trades)
              val_m = compute_metrics(val_trades)

              if comb["n_trades"] < 3:
                continue

              s = score_strategy_metrics(comb, weeks, target_tpw)
              if val_m["n_trades"] >= 2 and val_m["total_r"] < -4:
                s -= 80

              if s > best_fallback_score:
                best_fallback_score, best_fallback = s, strat

              if comb["win_rate"] >= 0.50 and comb["avg_rr"] >= 1.6 and comb["total_r"] > 0:
                if s > best_score:
                  best_score, best = s, strat

  return best if best is not None else best_fallback
