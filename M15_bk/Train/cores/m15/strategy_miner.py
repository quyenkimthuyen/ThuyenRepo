"""
Adaptive strategy miner v3 — rules + ML filter + smart exits.
"""
from dataclasses import dataclass, field, replace
from typing import Optional

import threading

import numpy as np
import pandas as pd

from config import (
  BARS_PER_WEEK, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS,
  MAX_TRADES_PER_DAY, TARGET_TRADES_PER_WEEK,
)
from feature_engine import FeatureMatrix
from ml_scorer import MLScorer
from strategy import Trade, compute_metrics

LABEL_CACHE: dict[tuple, tuple] = {}
_LABEL_LOCK = threading.Lock()
_LAST_BARS: int | None = None


def clear_label_cache() -> None:
  """Xóa cache label khi lịch sử MT5 thay đổi số bar."""
  with _LABEL_LOCK:
    LABEL_CACHE.clear()


def ensure_label_cache_for_df(bar_count: int) -> None:
  """Invalidate label cache khi số bar thay đổi."""
  global _LAST_BARS
  with _LABEL_LOCK:
    if _LAST_BARS is not None and _LAST_BARS != bar_count:
      LABEL_CACHE.clear()
    _LAST_BARS = bar_count


def notify_data_updated(bar_count: int) -> None:
  """Gọi sau mỗi lần ghi cache giá mới."""
  global _LAST_BARS
  with _LABEL_LOCK:
    LABEL_CACHE.clear()
    _LAST_BARS = bar_count


def _align_array(arr: np.ndarray, n: int) -> np.ndarray:
  if len(arr) == n:
    return arr
  if len(arr) > n:
    return arr[:n].copy()
  out = np.zeros(n, dtype=arr.dtype)
  out[: len(arr)] = arr
  return out


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
  # Researched M15 defaults: longer hold + wider spacing ↑ total R & WR
  max_hold_bars: int = 96
  min_bars_between: int = 12
  min_rules_match: int = 2
  max_trades_per_day: int = MAX_TRADES_PER_DAY
  ml_prob_min: float = 0.40
  exit_mode: str = "trail"       # full | partial | trail
  partial_pct: float = 0.4
  partial_at_r: float = 1.2
  trail_activate_r: float = 1.0
  trail_distance_r: float = 0.5
  session_filter: bool = True
  session_start_hour: int = 7
  session_end_hour: int = 20
  # Soft HTF bias: boost aligned / dampen counter-trend entries
  htf_align_boost: float = 1.12
  htf_counter_dampen: float = 0.88
  # Opt-in edge surgery (calibrated on train only)
  blocked_hours: tuple[int, ...] = ()
  allow_long: bool = True
  allow_short: bool = True
  # Opt-in anti-chase: block exhaustion entries (SHORT into high RSI, etc.)
  anti_chase: bool = False
  anti_chase_rsi_short_max: float = 100.0  # allow short only if RSI < max
  anti_chase_rsi_long_min: float = 0.0     # allow long only if RSI > min
  anti_chase_vwap_short_max: float = 99.0  # allow short only if vwap_dist < max
  anti_chase_logic: str = "or"             # or | and
  # TP uses ATR×mult×RR; SL still ATR×mult + 1 spread (live Ask/Bid).
  tp_ignores_spread_buffer: bool = False
  min_atr_spread_ratio: float = 0.0
  confirm_r: float = 0.0
  confirm_wait_bars: int = 4
  confirm_cancel_r: float = 0.5
  ml_scorer: MLScorer | None = None
  name: str = "mined_v3"


@dataclass(frozen=True)
class MiningSearchSpace:
  """Immutable mining grid; defaults match researched M15 combo (spacing_12 + hold_96).

  Opt-in only — leave ``selection_mode="legacy"`` (default) to preserve existing
  Trade Models / Grid behavior. ``expectancy_frontier`` changes how candidates are
  ranked inside ``mine_strategy`` without altering the default search ranges.
  """
  rr_ratios: tuple[float, ...] = (2.5, 3.0)
  atr_multipliers: tuple[float, ...] = (0.9, 1.05)
  max_hold_bars: tuple[int, ...] = (96,)
  min_bars_between: tuple[int, ...] = (12,)
  session_ranges: tuple[tuple[int, int], ...] = ((7, 20),)
  session_filters: tuple[bool, ...] = (True,)
  score_thresholds: tuple[float, ...] = (0.6, 1.0, 1.6, 2.2)
  min_rules_matches: tuple[int, ...] = (1, 2)
  ml_probability_thresholds: tuple[float, ...] = (0.36, 0.40, 0.44, 0.48)
  min_feature_samples: int = 30
  min_threshold_samples: int = 10
  min_binary_samples: int = 8
  include_session_regime_rules: bool = False
  target_trades_per_week: float = TARGET_TRADES_PER_WEEK
  drawdown_penalty: float = 0.0
  loss_streak_penalty: float = 0.0
  # legacy | expectancy_frontier | elite_frontier (opt-in joint WR×RR selection)
  selection_mode: str = "legacy"
  # Opt-in: after mining, kill toxic hours / weak side using TRAIN trades only
  edge_surgery: bool = False
  edge_surgery_min_hour_trades: int = 3
  edge_surgery_max_hour_wr: float = 0.42
  edge_surgery_dominant_side_ratio: float = 0.70
  # When False, only dominant/weak-side veto runs (hours stay open).
  edge_surgery_hours: bool = True
  # Opt-in anti-chase gate (train-calibrated RSI / VWAP exhaustion veto)
  anti_chase: bool = False
  # off | calibrate | fixed — fixed does not re-rank genomes (safer OOS)
  anti_chase_mode: str = "calibrate"
  anti_chase_fixed_rsi: float = 65.0
  anti_chase_fixed_vwap: float = 99.0
  anti_chase_rsi_caps: tuple[float, ...] = (60.0, 62.0, 65.0, 68.0, 100.0)
  anti_chase_min_tpw: float = 5.0
  anti_chase_use_vwap: bool = False
  anti_chase_vwap_caps: tuple[float, ...] = (1.5, 2.0, 2.5, 99.0)
  # or = void if RSI or VWAP is chase; and = void only if both are chase
  anti_chase_logic: str = "or"
  # Opt-in: only mine full exits (no hybrid/partial that clip winners → RR↓)
  exit_modes_full_only: bool = False
  # "" | full | hybrid | partial — lock one exit family (overrides full_only).
  exit_mode_lock: str = ""
  trail_activate_r: float = 1.8
  trail_distance_r: float = 0.6
  # "" = use the mined exit. "hybrid"/"trail"/"full" swaps OOS/live exits
  # after mining so genomes stay full-TP (late trail can raise R without remine).
  oos_exit_mode: str = ""
  oos_trail_activate_r: float = 0.0
  oos_trail_distance_r: float = 0.0
  partial_pct: float = 0.35
  partial_at_r: float = 1.5
  # If True, TP = ATR×mult×RR (SL still +1 spread). See execution.stop_and_target_distances.
  tp_ignores_spread_buffer: bool = False
  # 0 = off. Skip entries when ATR < ratio × spread (quiet bars, spread tax dominates).
  min_atr_spread_ratio: float = 0.0
  # 0 = labels use the genome RR. >0 = mine rules/ML on an easier follow-through RR.
  label_rr: float = 0.0
  # 0 = market at next open. >0 = BUY/SELL stop: fill only after confirm_r of follow-through.
  confirm_r: float = 0.0
  confirm_wait_bars: int = 4
  confirm_cancel_r: float = 0.5
  # 0 = desk default (MAX_TRADES_PER_DAY). 1 = first signal of the day only.
  max_trades_per_day: int = 0
  # both | long | short — applied on the chosen genome (train-safe).
  force_side: str = "both"


def mining_search_space_from_dict(value: dict | None) -> MiningSearchSpace:
  """Build a typed search space from JSON-compatible model metadata."""
  if not value:
    return MiningSearchSpace()
  tuple_fields = {
    "rr_ratios", "atr_multipliers", "max_hold_bars", "min_bars_between",
    "session_filters", "score_thresholds", "min_rules_matches",
    "ml_probability_thresholds", "anti_chase_rsi_caps", "anti_chase_vwap_caps",
  }
  kwargs = {}
  for key in MiningSearchSpace.__dataclass_fields__:
    if key not in value:
      continue
    raw = value[key]
    if key == "session_ranges":
      kwargs[key] = tuple(tuple(int(part) for part in pair) for pair in raw)
    elif key in tuple_fields:
      kwargs[key] = tuple(raw)
    else:
      kwargs[key] = raw
  return MiningSearchSpace(**kwargs)


def mining_search_space_to_dict(space: MiningSearchSpace | None) -> dict:
  from dataclasses import asdict
  return asdict(space or MiningSearchSpace())


def constrain_strategy_to_space(
  strat: MinedStrategy, space: MiningSearchSpace | None,
) -> MinedStrategy:
  """Project inherited KB genomes into the controlled experiment space."""
  if space is None:
    return strat

  def nearest(value, choices):
    return min(choices, key=lambda candidate: abs(float(candidate) - float(value)))

  strat.rr_ratio = float(nearest(strat.rr_ratio, space.rr_ratios))
  strat.atr_mult_sl = float(nearest(strat.atr_mult_sl, space.atr_multipliers))
  strat.max_hold_bars = int(nearest(strat.max_hold_bars, space.max_hold_bars))
  strat.min_bars_between = int(nearest(strat.min_bars_between, space.min_bars_between))
  strat.score_threshold = float(nearest(strat.score_threshold, space.score_thresholds))
  strat.min_rules_match = int(nearest(strat.min_rules_match, space.min_rules_matches))
  strat.ml_prob_min = float(nearest(
    strat.ml_prob_min, space.ml_probability_thresholds,
  ))
  strat.session_filter = bool(
    strat.session_filter if strat.session_filter in space.session_filters
    else space.session_filters[0]
  )
  strat.session_start_hour, strat.session_end_hour = min(
    space.session_ranges,
    key=lambda pair: (
      abs(pair[0] - strat.session_start_hour) + abs(pair[1] - strat.session_end_hour)
    ),
  )
  mtd = int(getattr(space, "max_trades_per_day", 0) or 0)
  if mtd > 0:
    strat.max_trades_per_day = mtd
  side = str(getattr(space, "force_side", "both") or "both").lower()
  if side == "short":
    strat.allow_long = False
  elif side == "long":
    strat.allow_short = False
  strat.tp_ignores_spread_buffer = bool(getattr(space, "tp_ignores_spread_buffer", False))
  strat.min_atr_spread_ratio = float(getattr(space, "min_atr_spread_ratio", 0.0) or 0.0)
  strat.confirm_r = float(getattr(space, "confirm_r", 0.0) or 0.0)
  strat.confirm_wait_bars = int(getattr(space, "confirm_wait_bars", 4) or 4)
  strat.confirm_cancel_r = float(getattr(space, "confirm_cancel_r", 0.5) or 0.5)
  return strat


def apply_oos_exit_overlay(
  strat: MinedStrategy,
  space: MiningSearchSpace | None,
) -> MinedStrategy:
  """Keep mined entries/rules; optionally swap the OOS/live exit engine.

  Mining still ranks genomes on full TP/SL. A late hybrid (activate near the
  genome TP) can convert giveback into a win without changing the signal book.
  """
  if strat is None or space is None:
    return strat
  mode = str(getattr(space, "oos_exit_mode", "") or "").strip().lower()
  if not mode:
    return strat
  kw: dict = {"exit_mode": mode}
  act = float(getattr(space, "oos_trail_activate_r", 0.0) or 0.0)
  dist = float(getattr(space, "oos_trail_distance_r", 0.0) or 0.0)
  if act > 0:
    kw["trail_activate_r"] = act
  if dist > 0:
    kw["trail_distance_r"] = dist
  return replace(strat, **kw)


CONTINUOUS_FEATURES = [
  "rsi", "adx", "bb_pos", "bb_width_pct", "atr_pct", "zscore_20",
  "price_vs_ema21", "price_vs_ema50", "ema_slope_8", "ema_slope_21",
  "macd_hist", "roc_5", "body_ratio", "lower_wick_ratio", "upper_wick_ratio",
  "session_vwap_dist", "swing_strength",
]
BINARY_LONG = [
  "sweep_low_fade", "squeeze_break_up", "pullback_long", "range_buy",
  "engulf_bull", "macd_cross_up", "ema_stack_bull",
  "rejection_bull", "displacement_bull", "structure_break_up", "confluence_long",
]
BINARY_SHORT = [
  "sweep_high_fade", "squeeze_break_dn", "pullback_short", "range_sell",
  "engulf_bear", "macd_cross_dn", "ema_stack_bear",
  "rejection_bear", "displacement_bear", "structure_break_dn", "confluence_short",
]
SESSION_REGIME_BINARY = [
  "london_session", "ny_session", "overlap_session", "asia_session", "london_open",
  "regime_trending", "regime_ranging", "regime_high_vol", "regime_low_vol",
]


def _exec_cost_kwargs() -> dict:
  return {
    "spread_pips": float(DEFAULT_SPREAD_PIPS),
    "slippage_pips": float(DEFAULT_SLIPPAGE_PIPS),
  }


def _exit_modes_for_space(space: MiningSearchSpace) -> list[tuple[str, dict]]:
  """Exit families the miner actually scores. Default stays full+hybrid+partial."""
  lock = str(getattr(space, "exit_mode_lock", "") or "").strip().lower()
  trail_kw = {
    "trail_activate_r": float(getattr(space, "trail_activate_r", 1.8) or 1.8),
    "trail_distance_r": float(getattr(space, "trail_distance_r", 0.6) or 0.6),
  }
  partial_kw = {
    "partial_pct": float(getattr(space, "partial_pct", 0.35) or 0.35),
    "partial_at_r": float(getattr(space, "partial_at_r", 1.5) or 1.5),
  }
  if lock == "hybrid":
    return [("hybrid", trail_kw)]
  if lock == "partial":
    return [("partial", partial_kw)]
  if lock == "full" or getattr(space, "exit_modes_full_only", False):
    return [("full", {})]
  return [
    ("full", {}),
    ("hybrid", trail_kw),
    ("partial", partial_kw),
  ]


def _atr_too_small_vs_spread(fm, strat, i: int) -> bool:
  ratio = float(getattr(strat, "min_atr_spread_ratio", 0.0) or 0.0)
  if ratio <= 0:
    return False
  try:
    av = float(fm.atr[i])
  except (TypeError, ValueError, IndexError):
    return True
  if av != av or av <= 0:
    return True
  from execution import spread_from_quote
  pts = 0.0
  arr = getattr(fm, "spread_points", None)
  if arr is not None and 0 <= i < len(arr):
    try:
      pts = float(arr[i] or 0.0)
    except (TypeError, ValueError):
      pts = 0.0
  spr = spread_from_quote(DEFAULT_SPREAD_PIPS, pts)
  if spr <= 0:
    return False
  return av < ratio * spr


def _bar_spread_points(fm, i: int, last_pts: float) -> tuple[float, float]:
  from execution import carry_spread_points
  pts = 0.0
  arr = getattr(fm, "spread_points", None)
  if arr is not None and 0 <= i < len(arr):
    try:
      pts = float(arr[i] or 0.0)
    except (TypeError, ValueError):
      pts = 0.0
  return carry_spread_points(pts, last_pts)


def _confirm_stop_fill(
  fm, start_j: int, end_idx: int, direction: int, ref_price: float, sl_d: float,
  confirm_r: float, cancel_r: float, wait_bars: int,
  spread_pips: float, last_pts: float,
) -> tuple[int, float, float] | None:
  """Pending stop: fill after follow-through, cancel if price dies first.

  Same-bar confirm+cancel → skip (path unknown). Live-like BUY/SELL stop.
  """
  from execution import spread_from_quote
  wait_n = max(1, int(wait_bars or 1))
  last = min(start_j + wait_n, end_idx - 1)
  if sl_d <= 0 or confirm_r <= 0:
    return None
  confirm_px = ref_price + direction * sl_d * float(confirm_r)
  cancel_px = ref_price - direction * sl_d * float(cancel_r)
  pts = last_pts
  for j in range(start_j, last):
    pts, _ = _bar_spread_points(fm, j, pts)
    spr = spread_from_quote(spread_pips, pts)
    bid_h, bid_l = float(fm.high[j]), float(fm.low[j])
    if direction > 0:
      if bid_l <= cancel_px:
        return None
      if bid_h >= confirm_px:
        return (j, confirm_px, pts)
    else:
      ask_h, ask_l = bid_h + spr, bid_l + spr
      if ask_h >= cancel_px:
        return None
      if ask_l <= confirm_px:
        return (j, confirm_px, pts)
  return None


def _label_outcomes(fm, start, end, rr=2.5, atr_mult=0.9, max_hold_bars=36,
                    spread_pips: float | None = None,
                    tp_ignores_spread_buffer: bool = False):
  ensure_label_cache_for_df(fm.n)
  from execution import stop_and_target_distances, spread_from_quote
  spr = float(DEFAULT_SPREAD_PIPS if spread_pips is None else spread_pips)
  key = (
    "bidask1", fm.n, start, end, rr, atr_mult, max_hold_bars, round(spr, 4),
    int(bool(tp_ignores_spread_buffer)),
  )
  with _LABEL_LOCK:
    cached = LABEL_CACHE.get(key)
    if cached is not None:
      long_win, short_win = cached
      if len(long_win) == fm.n and len(short_win) == fm.n:
        return long_win, short_win
      LABEL_CACHE.pop(key, None)

  long_win = np.zeros(fm.n, dtype=np.int8)
  short_win = np.zeros(fm.n, dtype=np.int8)
  o, h, l, atr_v = fm.open, fm.high, fm.low, fm.atr
  max_hold = max_hold_bars
  last_i = min(end - max_hold - 2, fm.n - max_hold - 2)
  last_pts = 0.0

  for i in range(start, last_i):
    av = atr_v[i]
    if np.isnan(av) or av <= 0:
      continue
    pts, last_pts = _bar_spread_points(fm, i + 1, last_pts)
    spr_px = spread_from_quote(spr, pts)
    bid_entry = o[i + 1]
    # BUY at Ask, SELL at Bid — same as live OrderSend / Trade replay.
    buy_entry = bid_entry + spr_px
    sell_entry = bid_entry
    sl_d, tp_d = stop_and_target_distances(
      av, atr_mult, rr, spr, pts,
      tp_ignores_spread_buffer=bool(tp_ignores_spread_buffer),
    )
    lsl, ltp = buy_entry - sl_d, buy_entry + tp_d
    ssl, stp = sell_entry + sl_d, sell_entry - tp_d
    j_end = min(i + 1 + max_hold, end)

    # Include the entry bar (i+1) — live SL is active from the fill tick.
    for j in range(i + 1, j_end):
      if l[j] <= lsl:
        break
      if h[j] >= ltp:
        long_win[i] = 1
        break
    for j in range(i + 1, j_end):
      j_pts, last_pts = _bar_spread_points(fm, j, last_pts)
      j_spr = spread_from_quote(spr, j_pts)
      if h[j] + j_spr >= ssl:
        break
      if l[j] + j_spr <= stp:
        short_win[i] = 1
        break

  with _LABEL_LOCK:
    LABEL_CACHE[key] = (long_win, short_win)
  return long_win, short_win


def _mine_threshold_rules(
  fm, feat_name, direction, wins, start, end, top_n=3,
  min_feature_samples=30, min_threshold_samples=10,
):
  if len(wins) != fm.n:
    return []
  feat = fm.get(feat_name)
  rules = []
  valid = np.zeros(fm.n, dtype=bool)
  valid[start:end] = True
  valid[:fm.warmup] = False
  valid &= ~np.isnan(feat)
  if valid.sum() < min_feature_samples:
    return []
  baseline = wins[valid].mean()
  min_wr = max(baseline + 0.05, 0.32)
  for pct in [20, 35, 50, 65, 80]:
    thr = np.nanpercentile(feat[valid], pct)
    for op in ("gt", "lt"):
      cond = valid & (feat > thr if op == "gt" else feat < thr)
      if cond.sum() < min_threshold_samples:
        continue
      wr = wins[cond].mean()
      lift = wr - baseline
      if lift > 0.03 and wr >= min_wr:
        rules.append((lift * 15 + wr * 8, Rule(feat_name, direction, op, thr, weight=lift * 10)))
  rules.sort(key=lambda x: x[0], reverse=True)
  return [r for _, r in rules[:top_n]]


def _mine_binary_rules(fm, feat_names, direction, wins, start, end, min_binary_samples=8):
  if len(wins) != fm.n:
    return []
  rules = []
  valid = np.zeros(fm.n, dtype=bool)
  valid[start:end] = True
  valid[:fm.warmup] = False
  baseline = wins[valid].mean() if valid.sum() > 0 else 0.28
  for name in feat_names:
    try:
      feat = fm.get(name)
    except (KeyError, AttributeError):
      continue
    if len(feat) != fm.n:
      continue
    cond = valid & (feat > 0.5)
    if cond.sum() < min_binary_samples:
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


def _htf_bias(fm, i: int, direction: int, strat) -> float:
  """Soft higher-timeframe alignment multiplier (price-action confluence)."""
  try:
    htf = float(fm.get("htf_trend")[i])
  except (KeyError, AttributeError, TypeError, ValueError):
    return 1.0
  if np.isnan(htf) or htf == 0.0:
    return 1.0
  boost = float(getattr(strat, "htf_align_boost", 1.12) or 1.12)
  damp = float(getattr(strat, "htf_counter_dampen", 0.88) or 0.88)
  aligned = (direction == 1 and htf > 0) or (direction == -1 and htf < 0)
  return boost if aligned else damp


def _pa_confluence_bonus(fm, i: int, direction: int) -> float:
  """Extra score when multiple PA setups fire together."""
  key = "confluence_long" if direction == 1 else "confluence_short"
  try:
    v = float(fm.get(key)[i])
  except (KeyError, AttributeError, TypeError, ValueError):
    return 0.0
  if np.isnan(v):
    return 0.0
  return 0.35 * v


def generate_signals_mined(
  fm, strat, start_idx=0, end_idx=None, *, include_last_bar: bool = False,
):
  if end_idx is None:
    end_idx = fm.n
  signals = np.zeros(fm.n, dtype=np.int8)
  candidates = []

  if strat.ml_scorer is not None and hasattr(strat.ml_scorer, "refresh_for_fm"):
    strat.ml_scorer.refresh_for_fm(fm)
  ml_l_arr = strat.ml_scorer._prob_long if strat.ml_scorer and strat.ml_scorer._prob_long is not None else None
  ml_s_arr = strat.ml_scorer._prob_short if strat.ml_scorer and strat.ml_scorer._prob_short is not None else None
  hours = getattr(fm, "broker_hours", None)
  if hours is None:
    hours = fm.hours

  # Backtest needs i+1 entry bar → stop at end_idx-1.
  # Live bridge decides on the just-closed last bar → include it.
  stop = min(end_idx, fm.n) if include_last_bar else end_idx - 1
  blocked = set(int(h) for h in (getattr(strat, "blocked_hours", ()) or ()))
  allow_long = bool(getattr(strat, "allow_long", True))
  allow_short = bool(getattr(strat, "allow_short", True))

  for i in range(max(start_idx, fm.warmup), stop):
    if strat.session_filter and not (strat.session_start_hour <= hours[i] <= strat.session_end_hour):
      continue
    if blocked and int(hours[i]) in blocked:
      continue

    ls, lc = _count_matching_rules(fm, strat.long_rules, i)
    ss, sc = _count_matching_rules(fm, strat.short_rules, i)

    ml_l = (
      float(ml_l_arr[i])
      if ml_l_arr is not None and 0 <= i < len(ml_l_arr)
      else 0.5
    )
    ml_s = (
      float(ml_s_arr[i])
      if ml_s_arr is not None and 0 <= i < len(ml_s_arr)
      else 0.5
    )

    # Rule score + ML + soft HTF / PA confluence
    combined_l = ls * (0.5 + ml_l) * _htf_bias(fm, i, 1, strat) + _pa_confluence_bonus(fm, i, 1)
    combined_s = ss * (0.5 + ml_s) * _htf_bias(fm, i, -1, strat) + _pa_confluence_bonus(fm, i, -1)

    if (
      allow_long
      and lc >= strat.min_rules_match
      and combined_l >= strat.score_threshold
      and combined_l > combined_s
    ):
      if ml_l >= strat.ml_prob_min:
        candidates.append((combined_l + ml_l * 2, 1, i))
    elif (
      allow_short
      and sc >= strat.min_rules_match
      and combined_s >= strat.score_threshold
      and combined_s > combined_l
    ):
      if ml_s >= strat.ml_prob_min:
        candidates.append((combined_s + ml_s * 2, -1, i))

  if candidates and strat.max_trades_per_day > 0:
    from mt5_bridge.history_sync import utc_to_broker_time
    day_buckets: dict[str, list] = {}
    for score, direction, i in candidates:
      broker_day = utc_to_broker_time(fm.index[i]).strftime("%Y-%m-%d")
      day_buckets.setdefault(broker_day, []).append((score, direction, i))
    for items in day_buckets.values():
      items.sort(key=lambda x: x[0], reverse=True)
      selected: list[int] = []
      for score, direction, i in items:
        if len(selected) >= strat.max_trades_per_day:
          break
        if all(abs(i - other) >= strat.min_bars_between for other in selected):
          signals[i] = direction
          selected.append(i)

  # Anti-chase void AFTER selection — cancel chase fills without promoting
  # lower-ranked replacements (that pattern destroyed WR in earlier A/Bs).
  if getattr(strat, "anti_chase", False):
    for i in range(fm.n):
      if signals[i] != 0 and _is_chase_entry(fm, strat, i, int(signals[i])):
        signals[i] = 0

  if float(getattr(strat, "min_atr_spread_ratio", 0.0) or 0.0) > 0:
    for i in range(fm.n):
      if signals[i] != 0 and _atr_too_small_vs_spread(fm, strat, i):
        signals[i] = 0
  return signals


def _is_chase_entry(fm, strat, signal_idx: int, direction: int) -> bool:
  """Causal anti-chase check on the SIGNAL bar (no entry-bar lookahead)."""
  if not getattr(strat, "anti_chase", False):
    return False
  try:
    rsi_v = float(fm.get("rsi")[signal_idx])
  except Exception:
    rsi_v = float("nan")
  try:
    vwap_v = float(fm.get("session_vwap_dist")[signal_idx])
  except Exception:
    vwap_v = float("nan")
  logic = str(getattr(strat, "anti_chase_logic", "or") or "or").lower()
  if direction < 0:
    short_max = float(getattr(strat, "anti_chase_rsi_short_max", 100.0) or 100.0)
    vwap_max = float(getattr(strat, "anti_chase_vwap_short_max", 99.0) or 99.0)
    rsi_chase = np.isfinite(rsi_v) and rsi_v >= short_max
    vwap_chase = np.isfinite(vwap_v) and vwap_v >= vwap_max
    if logic == "and":
      return bool(rsi_chase and vwap_chase)
    # OR: RSI chase; VWAP chase only when cap is actively set (< 90).
    if rsi_chase:
      return True
    if vwap_max < 90 and vwap_chase:
      return True
    return False
  if direction > 0:
    long_min = float(getattr(strat, "anti_chase_rsi_long_min", 0.0) or 0.0)
    if np.isfinite(rsi_v) and rsi_v <= long_min:
      return True
  return False


def _json_num(value) -> float | None:
  try:
    x = float(value)
  except (TypeError, ValueError):
    return None
  if not np.isfinite(x):
    return None
  return round(x, 4)


def _rule_expect(rule: Rule) -> str:
  if rule.op == "eq1":
    return "> 0.5 (bật)"
  if rule.op == "gt":
    return f"> {rule.threshold:g}"
  if rule.op == "lt":
    return f"< {rule.threshold:g}"
  return str(rule.op)


def _eval_rule(fm, rule: Rule, i: int) -> tuple[bool, float | None]:
  try:
    v = float(fm.get(rule.feature)[i])
  except Exception:
    return False, None
  if np.isnan(v):
    return False, None
  ok = (
    (rule.op == "eq1" and v > 0.5)
    or (rule.op == "gt" and v > rule.threshold)
    or (rule.op == "lt" and v < rule.threshold)
  )
  return ok, v


def _gate(
  gid: str, label: str, ok: bool, current, expect: str, *, side: str,
) -> dict:
  if isinstance(current, (int, float)) and not isinstance(current, bool):
    current = _json_num(current)
  return {
    "id": gid,
    "label": label,
    "ok": bool(ok),
    "current": current,
    "expect": expect,
    "side": side,
  }


def explain_bar_gates(fm, strat, i: int) -> dict:
  """Per-side gate dump for the closed bar: current vs expect (Live desk)."""
  hours = getattr(fm, "broker_hours", None)
  if hours is None:
    hours = getattr(fm, "hours", None)
  hour = None
  if hours is not None and 0 <= i < len(hours):
    try:
      hour = int(hours[i])
    except (TypeError, ValueError):
      hour = None

  session_on = (not bool(getattr(strat, "session_filter", True))) or (
    hour is not None
    and int(getattr(strat, "session_start_hour", 7))
    <= hour
    <= int(getattr(strat, "session_end_hour", 20))
  )
  blocked = set(int(h) for h in (getattr(strat, "blocked_hours", ()) or ()))
  hour_ok = hour is None or hour not in blocked
  session_expect = (
    f"{int(getattr(strat, 'session_start_hour', 7))}–"
    f"{int(getattr(strat, 'session_end_hour', 20))}h"
    if getattr(strat, "session_filter", True) else "off"
  )
  blocked_expect = (
    "not in " + ",".join(str(h) for h in sorted(blocked))
    if blocked else "any hour"
  )

  def _side(direction: int) -> dict:
    side = "BUY" if direction == 1 else "SELL"
    rules = strat.long_rules if direction == 1 else strat.short_rules
    allowed = bool(getattr(strat, "allow_long" if direction == 1 else "allow_short", True))
    gates = [
      _gate("allow", f"Allow {side}", allowed, "on" if allowed else "off", "on", side=side),
      _gate("session", "Session hour", session_on, hour, session_expect, side=side),
      _gate("blocked_hour", "Hour not blocked", hour_ok, hour, blocked_expect, side=side),
    ]
    score, count = _count_matching_rules(fm, rules, i)
    for r in rules:
      ok, v = _eval_rule(fm, r, i)
      gates.append(_gate(
        f"rule:{r.feature}:{r.op}",
        str(r.feature),
        ok,
        _json_num(v),
        _rule_expect(r),
        side=side,
      ))
    need = int(getattr(strat, "min_rules_match", 1) or 1)
    gates.append(_gate(
      "rules_count",
      f"Rules matched (≥{need})",
      count >= need,
      count,
      f">= {need} / {len(rules)}",
      side=side,
    ))

    ml_arr = None
    scorer = getattr(strat, "ml_scorer", None)
    if scorer is not None:
      ml_arr = scorer._prob_long if direction == 1 else scorer._prob_short
    ml_v = (
      float(ml_arr[i])
      if ml_arr is not None and 0 <= i < len(ml_arr)
      else 0.5
    )
    ml_min = float(getattr(strat, "ml_prob_min", 0.4) or 0.0)
    gates.append(_gate(
      "ml", "ML prob", ml_v >= ml_min, _json_num(ml_v), f">= {ml_min:g}", side=side,
    ))

    other_rules = strat.short_rules if direction == 1 else strat.long_rules
    other_score, _ = _count_matching_rules(fm, other_rules, i)
    other_arr = None
    if scorer is not None:
      other_arr = scorer._prob_short if direction == 1 else scorer._prob_long
    other_ml = (
      float(other_arr[i])
      if other_arr is not None and 0 <= i < len(other_arr)
      else 0.5
    )
    combined = (
      score * (0.5 + ml_v) * _htf_bias(fm, i, direction, strat)
      + _pa_confluence_bonus(fm, i, direction)
    )
    other_combined = (
      other_score * (0.5 + other_ml) * _htf_bias(fm, i, -direction, strat)
      + _pa_confluence_bonus(fm, i, -direction)
    )
    thresh = float(getattr(strat, "score_threshold", 0.0) or 0.0)
    gates.append(_gate(
      "score", "Combined score", combined >= thresh,
      _json_num(combined), f">= {thresh:g}", side=side,
    ))
    gates.append(_gate(
      "score_lead",
      "Leads opposite side",
      combined > other_combined,
      _json_num(combined),
      f"> {_json_num(other_combined) if other_combined is not None else other_combined}",
      side=side,
    ))

    chase_on = bool(getattr(strat, "anti_chase", False))
    chase = _is_chase_entry(fm, strat, i, direction) if chase_on else False
    if chase_on:
      try:
        rsi_now = float(fm.get("rsi")[i])
      except Exception:
        rsi_now = float("nan")
      if direction > 0:
        floor = float(getattr(strat, "anti_chase_rsi_long_min", 0.0) or 0.0)
        expect_ch = f"RSI > {floor:g}"
      else:
        cap = float(getattr(strat, "anti_chase_rsi_short_max", 100.0) or 100.0)
        expect_ch = f"RSI < {cap:g}"
      gates.append(_gate(
        "anti_chase", "Anti-chase", not chase, _json_num(rsi_now), expect_ch, side=side,
      ))

    waiting = [g for g in gates if not g["ok"]]
    ready = (
      allowed and session_on and hour_ok
      and count >= need
      and combined >= thresh
      and combined > other_combined
      and ml_v >= ml_min
      and not chase
    )
    return {
      "side": side,
      "ready": bool(ready),
      "passed": sum(1 for g in gates if g["ok"]),
      "total": len(gates),
      "waiting_n": len(waiting),
      "waiting": [g["label"] for g in waiting],
      "gates": gates,
    }

  bar_time = None
  try:
    bar_time = str(fm.index[i])
  except Exception:
    pass
  return {
    "bar_time": bar_time,
    "hour": hour,
    "buy": _side(1),
    "sell": _side(-1),
  }


def backtest_mined(
  fm, strat, signals, start_idx=0, end_idx=None,
  spread_pips: float = 0.0, slippage_pips: float = 0.0,
  return_open: bool = False,
):
  from execution import (
    PIP, adjust_entry_price, stop_and_target_distances, spread_from_quote,
  )
  from mt5_bridge.history_sync import utc_to_broker_time

  if end_idx is None:
    end_idx = fm.n
  o, h, l, c, atr_v = fm.open, fm.high, fm.low, fm.close, fm.atr
  trades = []
  i = max(start_idx, fm.warmup)
  in_trade = False
  direction = entry_price = sl = tp = risk = 0.0
  entry_idx = partial_done = trail_active = 0.0
  entries_by_broker_day: dict[str, int] = {}
  last_pts = 0.0

  while i < end_idx - 1:
    pts, last_pts = _bar_spread_points(fm, i, last_pts)
    spr_px = spread_from_quote(spread_pips, pts)
    if in_trade:
      bid_h, bid_l, bid_c = h[i], l[i], c[i]
      ask_h, ask_l, ask_c = bid_h + spr_px, bid_l + spr_px, bid_c + spr_px
      exit_price = bid_c
      hit_sl = hit_tp = False

      # Hybrid: trail chỉ sau khi gần TP (bảo vệ lợi nhuận, không cắt sớm)
      # Live: BUY trail from Bid, SELL trail from Ask.
      if strat.exit_mode in ("trail", "hybrid") and not partial_done:
        act = strat.trail_activate_r
        if direction == 1 and bid_h >= entry_price + risk * act:
          trail_active = 1.0
          sl = max(sl, bid_h - risk * strat.trail_distance_r)
        elif direction == -1 and ask_l <= entry_price - risk * act:
          trail_active = 1.0
          sl = min(sl, ask_l + risk * strat.trail_distance_r)

      # Partial TP
      if strat.exit_mode == "partial" and not partial_done:
        if direction == 1 and bid_h >= entry_price + risk * strat.partial_at_r:
          partial_done = 1.0
          sl = entry_price + risk * 0.1
        elif direction == -1 and ask_l <= entry_price - risk * strat.partial_at_r:
          partial_done = 1.0
          sl = entry_price - risk * 0.1

      if direction == 1:
        if bid_l <= sl:
          hit_sl, exit_price = True, sl
        elif bid_h >= tp:
          hit_tp, exit_price = True, tp
      else:
        # SELL closes on Ask (OHLC is Bid).
        if ask_h >= sl:
          hit_sl, exit_price = True, sl
        elif ask_l <= tp:
          hit_tp, exit_price = True, tp

      max_hold = int(strat.max_hold_bars or 0)
      timed_out = max_hold > 0 and (i - entry_idx) >= max_hold
      if hit_sl or hit_tp or timed_out:
        reason = "tp" if hit_tp else ("trail" if trail_active and hit_sl else "sl")
        if not hit_sl and not hit_tp:
          reason = "timeout"
          slip_px = max(0.0, float(slippage_pips)) * PIP
          if direction == 1:
            exit_price = bid_c - slip_px
          else:
            exit_price = ask_c + slip_px

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
      # Void chase signals without replacement (keeps ranking of the original book).
      if _is_chase_entry(fm, strat, i, int(sig)):
        i += 1
        continue
      entry_idx = i + 1
      if entry_idx >= end_idx:
        break
      broker_day = utc_to_broker_time(fm.index[entry_idx]).strftime("%Y-%m-%d")
      if entries_by_broker_day.get(broker_day, 0) >= strat.max_trades_per_day:
        i += 1
        continue
      entry_pts, last_pts = _bar_spread_points(fm, entry_idx, last_pts)
      sl_d, tp_d = stop_and_target_distances(
        av, strat.atr_mult_sl, strat.rr_ratio, spread_pips, entry_pts,
        tp_ignores_spread_buffer=bool(getattr(strat, "tp_ignores_spread_buffer", False)),
      )
      direction = float(sig)
      ref_price = adjust_entry_price(
        o[entry_idx], int(sig), spread_pips, slippage_pips, spread_points=entry_pts,
      )
      confirm_r = float(getattr(strat, "confirm_r", 0.0) or 0.0)
      if confirm_r > 0:
        hit = _confirm_stop_fill(
          fm, entry_idx, end_idx, int(direction), ref_price, sl_d,
          confirm_r,
          float(getattr(strat, "confirm_cancel_r", 0.5) or 0.5),
          int(getattr(strat, "confirm_wait_bars", 4) or 4),
          spread_pips, last_pts,
        )
        if hit is None:
          i += 1
          continue
        entry_idx, entry_price, last_pts = hit
      else:
        entry_price = ref_price
      risk = sl_d
      partial_done = trail_active = 0.0
      if direction == 1:
        sl, tp = entry_price - sl_d, entry_price + tp_d
      else:
        sl, tp = entry_price + sl_d, entry_price - tp_d
      in_trade = True
      fill_day = utc_to_broker_time(fm.index[entry_idx]).strftime("%Y-%m-%d")
      entries_by_broker_day[fill_day] = entries_by_broker_day.get(fill_day, 0) + 1
      i = entry_idx
      continue
    i += 1

  open_pos = None
  if in_trade:
    held = max(0, (end_idx - 1) - int(entry_idx))
    open_pos = {
      "status": "OPEN",
      "entry": str(fm.index[int(entry_idx)]),
      "dir": "LONG" if direction == 1 else "SHORT",
      "entry_px": round(entry_price, 5),
      "sl": round(sl, 5),
      "tp": round(tp, 5),
      "risk_pips": round(risk * 10000, 1),
      "bars_held": held,
      "max_hold_bars": strat.max_hold_bars,
    }

  if return_open:
    return trades, open_pos
  return trades


def _weeks_in_window(start, end):
  return max((end - start) / float(BARS_PER_WEEK), 1.0)


def score_strategy_metrics(
  m, weeks, target_tpw=TARGET_TRADES_PER_WEEK,
  drawdown_penalty: float = 0.0, loss_streak_penalty: float = 0.0,
  selection_mode: str = "legacy",
):
  """Fitness tuned for realistic M15 edge (~45–55% WR × RR≥2) and total R / DD.

  ``selection_mode="expectancy_frontier"`` (opt-in) ranks by joint WR×RR
  geometric mean so the miner cannot buy WR by sacrificing RR (or vice versa).
  """
  if m["n_trades"] < 3:
    return -1e6
  tpw = m["n_trades"] / weeks
  wr, rr, tr, pf = m["win_rate"], m["avg_rr"], m["total_r"], m["profit_factor"]
  dd = float(m.get("max_drawdown_r") or 0)
  elite = selection_mode == "elite_frontier"
  # Soft frequency band: prefer ~7–10 tpw but allow quality over volume.
  # Elite sniper bands around a low target (accept sparse high-quality books).
  if elite:
    freq_score = 35 - abs(tpw - target_tpw) * 12
    if tpw < max(1.5, target_tpw * 0.45):
      freq_score -= 25
    if tpw > max(12.0, target_tpw * 2.5):
      freq_score -= 30
  else:
    freq_score = 45 - abs(tpw - target_tpw) * 22
    if tpw < 5:
      freq_score -= 45
    elif tpw < 7:
      freq_score -= 20
    if tpw > 12:
      freq_score -= 35
    elif tpw > 10:
      freq_score -= 15

  expectancy = wr * rr - (1.0 - wr)  # approx R per trade at fixed RR
  s = (
    wr * 130
    + min(rr, 4.5 if elite else 4) * 50
    + min(pf, 4) * 18
    + tr * (6 if elite else 12)
    + max(expectancy, -0.5) * 90
    + freq_score
  )
  # Achievable quality bonuses (previous 55/58/60 rarely fired)
  if wr >= 0.45 and rr >= 2.0:
    s += 45
  if wr >= 0.48 and rr >= 2.2:
    s += 70
  if wr >= 0.52 and rr >= 2.0:
    s += 90
  if wr >= 0.55 and rr >= 2.0:
    s += 60
  if rr >= 2.0:
    s += 40
  if rr < 1.7:
    s -= (1.7 - rr) * 100
  if wr < 0.40:
    s -= (0.40 - wr) * 200
  if tr <= 0:
    s -= 50
  # Built-in mild risk-adjusted reward (research: lower DD with spacing/hold)
  if dd > 0 and tr > 0:
    s += min(tr / dd, 10.0) * 12
  elif tr > 0 and dd <= 0:
    s += 40
  # Mild default DD / streak friction even when penalties are 0
  s -= dd * (drawdown_penalty if drawdown_penalty > 0 else 0.8)
  s -= float(m.get("max_loss_streak") or 0) * (
    loss_streak_penalty if loss_streak_penalty > 0 else 1.5
  )

  if selection_mode in ("expectancy_frontier", "elite_frontier"):
    # Geometric joint score: punish one-sided WR↑/RR↓ or RR↑/WR↓ trades.
    wr_ref = 0.60 if elite else 0.48
    rr_ref = 3.0 if elite else 2.4
    rr_cap = 4.5 if elite else 3.5
    wr_n = max(wr / wr_ref, 0.05)
    rr_n = max(min(rr, rr_cap) / rr_ref, 0.05)
    exp_n = max(expectancy / (0.80 if elite else 0.45), 0.05)
    joint = (wr_n * rr_n * exp_n) ** (1.0 / 3.0)
    s = s * (0.40 if elite else 0.55) + joint * (280 if elite else 220)
    if wr >= 0.48 and rr >= 2.3:
      s += 110
    elif wr >= 0.46 and rr >= 2.5:
      s += 80
    if wr < 0.44:
      s -= (0.44 - wr) * 260
    if rr < 2.1:
      s -= (2.1 - rr) * 140
    if elite:
      # Challenge bonuses: WR>60% × RR>3 (Total R may fall).
      if wr >= 0.55 and rr >= 2.8:
        s += 160
      if wr >= 0.58 and rr >= 3.0:
        s += 220
      if wr >= 0.60 and rr >= 3.0:
        s += 320
      if wr < 0.52:
        s -= (0.52 - wr) * 300
      if rr < 2.6:
        s -= (2.6 - rr) * 180
  return s


def _passes_best_gate(metrics: dict, selection_mode: str) -> bool:
  """Hard gate for the preferred genome; frontier mode is less WR-overfit."""
  wr = float(metrics.get("win_rate") or 0)
  rr = float(metrics.get("avg_rr") or 0)
  tr = float(metrics.get("total_r") or 0)
  if tr <= 0:
    return False
  if selection_mode == "elite_frontier":
    expectancy = wr * rr - (1.0 - wr)
    return (
      (wr >= 0.55 and rr >= 2.8 and expectancy >= 0.45)
      or (wr >= 0.58 and rr >= 2.6 and expectancy >= 0.50)
      or (wr >= 0.52 and rr >= 3.0 and expectancy >= 0.55)
      or (wr >= 0.60 and rr >= 2.5 and expectancy >= 0.50)
    )
  if selection_mode == "expectancy_frontier":
    expectancy = wr * rr - (1.0 - wr)
    return (
      (wr >= 0.46 and rr >= 2.2 and expectancy >= 0.30)
      or (wr >= 0.48 and rr >= 2.0 and expectancy >= 0.28)
      or (wr >= 0.44 and rr >= 2.6 and expectancy >= 0.35)
    )
  return wr >= 0.50 and rr >= 1.6


def calibrate_edge_surgery(
  fm, strat: MinedStrategy, train_start: int, train_end: int,
  *,
  min_hour_trades: int = 3,
  max_hour_wr: float = 0.42,
  dominant_side_ratio: float = 0.70,
  block_hours: bool = True,
) -> MinedStrategy:
  """Kill toxic broker-hours / weak side using TRAIN trades only (no OOS leak)."""
  if strat is None:
    return strat
  # Reset prior surgery so re-calibration is idempotent.
  strat.blocked_hours = ()
  strat.allow_long = True
  strat.allow_short = True

  signals = generate_signals_mined(fm, strat, train_start, train_end)
  trades = backtest_mined(fm, strat, signals, train_start, train_end, **_exec_cost_kwargs())
  if len(trades) < 5:
    return strat

  by_hour: dict[int, list[float]] = {}
  by_side: dict[int, list[float]] = {1: [], -1: []}
  for trade in trades:
    hour = int(pd.Timestamp(trade.entry_time).hour)
    by_hour.setdefault(hour, []).append(float(trade.r_multiple))
    by_side.setdefault(int(trade.direction), []).append(float(trade.r_multiple))

  blocked = []
  if block_hours:
    for hour, rs in by_hour.items():
      if len(rs) < min_hour_trades:
        continue
      wr = sum(1 for r in rs if r > 0) / len(rs)
      mean_r = sum(rs) / len(rs)
      # Only kill clearly toxic hours (avoid noisy 3-trade flukes).
      if len(rs) >= max(min_hour_trades, 5) and (wr <= max_hour_wr or mean_r < -0.15):
        blocked.append(hour)
      elif len(rs) >= min_hour_trades and wr <= min(max_hour_wr, 0.30) and mean_r < 0:
        blocked.append(hour)

  allow_long = True
  allow_short = True
  long_rs = by_side.get(1) or []
  short_rs = by_side.get(-1) or []
  n = max(len(trades), 1)
  long_exp = (sum(long_rs) / len(long_rs)) if long_rs else 0.0
  short_exp = (sum(short_rs) / len(short_rs)) if short_rs else 0.0
  long_share = len(long_rs) / n
  short_share = len(short_rs) / n

  # Classic both-sides sample gate
  if len(long_rs) >= 3 and len(short_rs) >= 3:
    if long_exp < 0 and short_exp > 0 and short_exp - long_exp >= 0.10:
      allow_long = False
    elif short_exp < 0 and long_exp > 0 and long_exp - short_exp >= 0.10:
      allow_short = False

  # Dominant-side gate: minority side with non-positive expectancy gets cut
  # even with 1–2 trades (common: book is ~99% SHORT).
  if short_share >= dominant_side_ratio and len(long_rs) >= 1 and long_exp <= 0:
    allow_long = False
  if long_share >= dominant_side_ratio and len(short_rs) >= 1 and short_exp <= 0:
    allow_short = False

  strat.blocked_hours = tuple(sorted(set(blocked)))
  strat.allow_long = allow_long
  strat.allow_short = allow_short
  if blocked or not allow_long or not allow_short:
    tag = []
    if blocked:
      tag.append("h" + ",".join(str(h) for h in strat.blocked_hours))
    if not allow_long:
      tag.append("noL")
    if not allow_short:
      tag.append("noS")
    base = strat.name.split("|surg:")[0]
    strat.name = f"{base}|surg:{'+'.join(tag)}"
  return strat


def apply_edge_surgery(
  fm, strat: MinedStrategy, train_start: int, train_end: int,
  space: MiningSearchSpace | None,
) -> MinedStrategy:
  """Shallow-copy + calibrate when ``space.edge_surgery`` is enabled."""
  import copy
  if strat is None:
    return strat
  space = space or MiningSearchSpace()
  out = copy.copy(strat)
  if not space.edge_surgery:
    return out
  return calibrate_edge_surgery(
    fm, out, train_start, train_end,
    min_hour_trades=int(space.edge_surgery_min_hour_trades),
    max_hour_wr=float(space.edge_surgery_max_hour_wr),
    dominant_side_ratio=float(getattr(space, "edge_surgery_dominant_side_ratio", 0.70)),
    block_hours=bool(getattr(space, "edge_surgery_hours", True)),
  )


def calibrate_anti_chase(
  fm, strat: MinedStrategy, train_start: int, train_end: int,
  *,
  rsi_caps: tuple[float, ...] = (60.0, 62.0, 65.0, 68.0, 100.0),
  vwap_caps: tuple[float, ...] = (99.0,),
  min_tpw: float = 5.0,
  selection_mode: str = "expectancy_frontier",
  target_tpw: float = TARGET_TRADES_PER_WEEK,
  drawdown_penalty: float = 0.0,
  loss_streak_penalty: float = 0.0,
) -> MinedStrategy:
  """Train-only RSI/VWAP exhaustion veto — kills chase-shorts that destroy WR.

  Empirically on M15 SHORT books: high RSI / high VWAP-extension entries print
  ~30% WR while low-RSI continuation shorts print ~65–70% at similar RR.
  """
  if strat is None:
    return strat
  import copy
  probe = copy.copy(strat)
  probe.anti_chase = False
  probe.anti_chase_rsi_short_max = 100.0
  probe.anti_chase_rsi_long_min = 0.0
  probe.anti_chase_vwap_short_max = 99.0

  signals = generate_signals_mined(fm, probe, train_start, train_end)
  trades = backtest_mined(fm, probe, signals, train_start, train_end, **_exec_cost_kwargs())
  weeks = _weeks_in_window(train_start, train_end)
  if len(trades) < 5:
    strat.anti_chase = True
    strat.anti_chase_rsi_short_max = 65.0
    strat.anti_chase_rsi_long_min = 35.0
    strat.anti_chase_vwap_short_max = 99.0
    return strat

  rsi_arr = fm.get("rsi")
  vwap_arr = fm.get("session_vwap_dist")
  best_score = -1e18
  best = (65.0, 99.0)

  def entry_feats(trade: Trade):
    ts = pd.Timestamp(trade.entry_time)
    i = int(fm.index.get_indexer([ts], method="pad")[0])
    if i < 0 or i >= fm.n:
      return None, None
    rsi = float(rsi_arr[i]) if rsi_arr is not None else float("nan")
    vwap = float(vwap_arr[i]) if vwap_arr is not None else float("nan")
    return rsi, vwap

  for rsi_cap in rsi_caps:
    for vwap_cap in vwap_caps:
      kept = []
      for trade in trades:
        rsi, vwap = entry_feats(trade)
        if trade.direction == -1:
          if np.isfinite(rsi) and rsi >= float(rsi_cap):
            continue
          if np.isfinite(vwap) and vwap >= float(vwap_cap):
            continue
        elif trade.direction == 1:
          long_min = max(0.0, 100.0 - float(rsi_cap)) if float(rsi_cap) < 100 else 0.0
          if np.isfinite(rsi) and rsi <= long_min:
            continue
        kept.append(trade)
      metrics = compute_metrics(kept)
      if metrics["n_trades"] < 3:
        continue
      tpw = metrics["n_trades"] / weeks
      s = score_strategy_metrics(
        metrics, weeks, target_tpw, drawdown_penalty, loss_streak_penalty,
        selection_mode,
      )
      # Soft frequency floor — allow quality books below 7 tpw.
      if tpw < min_tpw:
        s -= (min_tpw - tpw) * 55
      if s > best_score:
        best_score = s
        best = (float(rsi_cap), float(vwap_cap))

  rsi_cap, vwap_cap = best
  strat.anti_chase = True
  strat.anti_chase_rsi_short_max = rsi_cap
  strat.anti_chase_rsi_long_min = (
    max(0.0, 100.0 - rsi_cap) if rsi_cap < 100 else 0.0
  )
  strat.anti_chase_vwap_short_max = vwap_cap
  base = strat.name.split("|chase:")[0]
  strat.name = f"{base}|chase:rsi<{rsi_cap:g}+vwap<{vwap_cap:g}"
  return strat


def apply_anti_chase(
  fm, strat: MinedStrategy, train_start: int, train_end: int,
  space: MiningSearchSpace | None,
) -> MinedStrategy:
  import copy
  if strat is None:
    return strat
  space = space or MiningSearchSpace()
  out = copy.copy(strat)
  if not space.anti_chase:
    return out
  vwap_caps = (
    space.anti_chase_vwap_caps if space.anti_chase_use_vwap else (99.0,)
  )
  return calibrate_anti_chase(
    fm, out, train_start, train_end,
    rsi_caps=tuple(float(x) for x in space.anti_chase_rsi_caps),
    vwap_caps=tuple(float(x) for x in vwap_caps),
    min_tpw=float(space.anti_chase_min_tpw),
    selection_mode=str(space.selection_mode or "legacy"),
    target_tpw=float(space.target_trades_per_week),
    drawdown_penalty=float(space.drawdown_penalty),
    loss_streak_penalty=float(space.loss_streak_penalty),
  )


def apply_fixed_anti_chase(
  strat: MinedStrategy, space: MiningSearchSpace | None,
) -> MinedStrategy:
  """Attach a fixed RSI/VWAP veto without re-ranking genomes."""
  import copy
  if strat is None:
    return strat
  space = space or MiningSearchSpace()
  if not space.anti_chase:
    return strat
  out = copy.copy(strat)
  out.anti_chase = True
  rsi_cap = float(space.anti_chase_fixed_rsi)
  out.anti_chase_rsi_short_max = rsi_cap
  out.anti_chase_rsi_long_min = max(0.0, 100.0 - rsi_cap) if rsi_cap < 100 else 0.0
  out.anti_chase_vwap_short_max = (
    float(space.anti_chase_fixed_vwap) if space.anti_chase_use_vwap else 99.0
  )
  out.anti_chase_logic = str(getattr(space, "anti_chase_logic", "or") or "or")
  base = out.name.split("|chase:")[0]
  out.name = (
    f"{base}|chase:fixed_{out.anti_chase_logic}"
    f"_rsi<{out.anti_chase_rsi_short_max:g}"
    f"+vwap<{out.anti_chase_vwap_short_max:g}"
  )
  return out


def apply_breakthrough_filters(
  fm, strat: MinedStrategy, train_start: int, train_end: int,
  space: MiningSearchSpace | None,
  *,
  for_scoring: bool = False,
) -> MinedStrategy:
  """Compose opt-in post-mine filters (surgery → anti-chase).

  ``for_scoring=True`` skips fixed anti-chase so genome ranking stays stable;
  fixed gates are applied only on the final chosen strategy.
  """
  space = space or MiningSearchSpace()
  out = apply_edge_surgery(fm, strat, train_start, train_end, space)
  if space.anti_chase:
    mode = str(getattr(space, "anti_chase_mode", "calibrate") or "calibrate")
    if mode == "fixed":
      if for_scoring:
        # Rank genomes without the fixed veto; attach veto only on the final pick.
        out.anti_chase = False
        out.anti_chase_rsi_short_max = 100.0
        out.anti_chase_rsi_long_min = 0.0
        out.anti_chase_vwap_short_max = 99.0
      else:
        out = apply_fixed_anti_chase(out, space)
    else:
      out = apply_anti_chase(fm, out, train_start, train_end, space)
  mtd = int(getattr(space, "max_trades_per_day", 0) or 0)
  if mtd > 0:
    out.max_trades_per_day = mtd
  side = str(getattr(space, "force_side", "both") or "both").lower()
  if side == "short":
    out.allow_long = False
  elif side == "long":
    out.allow_short = False
  out.tp_ignores_spread_buffer = bool(getattr(space, "tp_ignores_spread_buffer", False))
  out.min_atr_spread_ratio = float(getattr(space, "min_atr_spread_ratio", 0.0) or 0.0)
  out.confirm_r = float(getattr(space, "confirm_r", 0.0) or 0.0)
  out.confirm_wait_bars = int(getattr(space, "confirm_wait_bars", 4) or 4)
  out.confirm_cancel_r = float(getattr(space, "confirm_cancel_r", 0.5) or 0.5)
  return out


def mine_strategy(
  fm, train_start, train_end, target_tpw=TARGET_TRADES_PER_WEEK,
  search_space: MiningSearchSpace | None = None,
):
  space = search_space or MiningSearchSpace(target_trades_per_week=target_tpw)
  with _LABEL_LOCK:
    if len(LABEL_CACHE) > 200:
      LABEL_CACHE.clear()

  span = train_end - train_start
  split = train_start + int(span * 0.65)
  weeks = _weeks_in_window(train_start, train_end)

  best = best_fallback = None
  best_score = best_fallback_score = -1e9

  exit_modes = _exit_modes_for_space(space)
  tp_geom = bool(getattr(space, "tp_ignores_spread_buffer", False))
  min_atr_r = float(getattr(space, "min_atr_spread_ratio", 0.0) or 0.0)
  label_rr = float(getattr(space, "label_rr", 0.0) or 0.0)
  confirm_r = float(getattr(space, "confirm_r", 0.0) or 0.0)
  confirm_wait = int(getattr(space, "confirm_wait_bars", 4) or 4)
  confirm_cancel = float(getattr(space, "confirm_cancel_r", 0.5) or 0.5)

  for rr in space.rr_ratios:
    for atr_m in space.atr_multipliers:
      for max_hold in space.max_hold_bars:
        long_wins, short_wins = _label_outcomes(
          fm, train_start, train_end, (label_rr if label_rr > 0 else rr), atr_m, max_hold,
          tp_ignores_spread_buffer=tp_geom,
        )

        ml = MLScorer()
        ml.fit(fm, train_start, train_end, long_wins, short_wins)

        long_rules, short_rules = [], []
        for feat in CONTINUOUS_FEATURES:
          long_rules.extend(_mine_threshold_rules(
            fm, feat, "long", long_wins, train_start, train_end, 2,
            space.min_feature_samples, space.min_threshold_samples,
          ))
          short_rules.extend(_mine_threshold_rules(
            fm, feat, "short", short_wins, train_start, train_end, 2,
            space.min_feature_samples, space.min_threshold_samples,
          ))
        extra_binary = SESSION_REGIME_BINARY if space.include_session_regime_rules else []
        long_rules.extend(_mine_binary_rules(
          fm, BINARY_LONG + extra_binary, "long", long_wins,
          train_start, train_end, space.min_binary_samples,
        ))
        short_rules.extend(_mine_binary_rules(
          fm, BINARY_SHORT + extra_binary, "short", short_wins,
          train_start, train_end, space.min_binary_samples,
        ))
        long_rules = sorted(long_rules, key=lambda r: r.weight, reverse=True)[:6]
        short_rules = sorted(short_rules, key=lambda r: r.weight, reverse=True)[:6]

        for name in ["sweep_low_fade", "pullback_long"]:
          if len(long_rules) < 2:
            long_rules.append(Rule(name, "long", "eq1", 0.5, weight=0.4))
        for name in ["sweep_high_fade", "pullback_short"]:
          if len(short_rules) < 2:
            short_rules.append(Rule(name, "short", "eq1", 0.5, weight=0.4))

        for exit_mode, exit_kw in exit_modes:
          for spacing in space.min_bars_between:
            for session_start, session_end in space.session_ranges:
              for session_filter in space.session_filters:
                for thr in space.score_thresholds:
                  for min_match in space.min_rules_matches:
                    for ml_thr in space.ml_probability_thresholds:
                      mtd = int(getattr(space, "max_trades_per_day", 0) or 0) or MAX_TRADES_PER_DAY
                      side = str(getattr(space, "force_side", "both") or "both").lower()
                      strat = MinedStrategy(
                        long_rules=long_rules, short_rules=short_rules,
                        score_threshold=thr, atr_mult_sl=atr_m, rr_ratio=rr,
                        max_hold_bars=max_hold, min_bars_between=spacing,
                        min_rules_match=min_match,
                        max_trades_per_day=mtd, ml_prob_min=ml_thr,
                        session_filter=session_filter,
                        session_start_hour=session_start, session_end_hour=session_end,
                        allow_long=side != "short",
                        allow_short=side != "long",
                        exit_mode=exit_mode, ml_scorer=ml,
                        tp_ignores_spread_buffer=tp_geom,
                        min_atr_spread_ratio=min_atr_r,
                        confirm_r=confirm_r,
                        confirm_wait_bars=confirm_wait,
                        confirm_cancel_r=confirm_cancel,
                        name=f"v3_{exit_mode}_rr{rr}",
                        **exit_kw,
                      )
                      sig = generate_signals_mined(fm, strat, train_start, train_end)
                      fit_trades = backtest_mined(fm, strat, sig, train_start, split, **_exec_cost_kwargs())
                      val_trades = backtest_mined(fm, strat, sig, split, train_end, **_exec_cost_kwargs())
                      comb = compute_metrics(fit_trades + val_trades)
                      val_m = compute_metrics(val_trades)

                      if comb["n_trades"] < 3:
                        continue

                      if space.selection_mode in ("expectancy_frontier", "elite_frontier"):
                        # Rank mostly on held-out train slice → less WR overfit.
                        val_weeks = max(weeks * 0.35, 0.5)
                        s_val = score_strategy_metrics(
                          val_m, val_weeks, space.target_trades_per_week,
                          space.drawdown_penalty, space.loss_streak_penalty,
                          space.selection_mode,
                        )
                        s_all = score_strategy_metrics(
                          comb, weeks, space.target_trades_per_week,
                          space.drawdown_penalty, space.loss_streak_penalty,
                          space.selection_mode,
                        )
                        s = 0.7 * s_val + 0.3 * s_all
                        gate_m = val_m if val_m["n_trades"] >= 2 else comb
                      else:
                        s = score_strategy_metrics(
                          comb, weeks, space.target_trades_per_week,
                          space.drawdown_penalty, space.loss_streak_penalty,
                          space.selection_mode,
                        )
                        gate_m = comb
                      if val_m["n_trades"] >= 2 and val_m["total_r"] < -4:
                        s -= 80

                      if s > best_fallback_score:
                        best_fallback_score, best_fallback = s, strat

                      if _passes_best_gate(gate_m, space.selection_mode):
                        if s > best_score:
                          best_score, best = s, strat

  chosen = best if best is not None else best_fallback
  if chosen is not None:
    chosen = apply_breakthrough_filters(
      fm, chosen, train_start, train_end, space, for_scoring=False,
    )
  return chosen
