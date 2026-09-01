"""Opt-in mining search-space presets for WR×RR experiments.

Defaults / existing Trade Models are untouched: callers must request a preset
explicitly (compare script, research optimizer, or model metadata).
"""
from __future__ import annotations

from copy import deepcopy

from strategy_miner import MiningSearchSpace, mining_search_space_to_dict


def _jsonable(space: dict) -> dict:
  """Normalize tuples → lists for model metadata / JSON."""
  out = {}
  for key, value in space.items():
    if isinstance(value, tuple):
      out[key] = [
        list(item) if isinstance(item, tuple) else item for item in value
      ]
    else:
      out[key] = value
  return out


BASELINE_SPACE = _jsonable(mining_search_space_to_dict(MiningSearchSpace()))

WR_RR_SNIPER = {
  **BASELINE_SPACE,
  "min_bars_between": [16],
  "session_ranges": [[8, 17]],
  "score_thresholds": [1.0, 1.6, 2.2],
  "min_rules_matches": [2],
  "ml_probability_thresholds": [0.40, 0.44, 0.48],
  "target_trades_per_week": 8.0,
  "drawdown_penalty": 1.5,
  "loss_streak_penalty": 2.0,
}

WR_RR_FRONTIER = {
  **WR_RR_SNIPER,
  "selection_mode": "expectancy_frontier",
}

WR_RR_LOCK = {
  **WR_RR_FRONTIER,
  "max_hold_bars": [64, 96],
  "atr_multipliers": [0.9, 1.05, 1.2],
}

# What actually drove the first win: joint WR×RR scoring + RR ladder (no surgery).
FRONTIER_RR = {
  **BASELINE_SPACE,
  "rr_ratios": [2.5, 3.0, 3.2],
  "selection_mode": "expectancy_frontier",
}

# Side-only surgery: cut sparse losing LONG/SHORT, do not touch hours.
EDGE_SIDE_ONLY = {
  **FRONTIER_RR,
  "edge_surgery": True,
  "edge_surgery_hours": False,
  "edge_surgery_dominant_side_ratio": 0.65,
}

# Gentle hours: only very toxic hours (n≥5) + side veto.
EDGE_GENTLE = {
  **FRONTIER_RR,
  "edge_surgery": True,
  "edge_surgery_hours": True,
  "edge_surgery_min_hour_trades": 5,
  "edge_surgery_max_hour_wr": 0.32,
  "edge_surgery_dominant_side_ratio": 0.65,
}

# Legacy aggressive surgery presets (kept for regression compares).
EDGE_SURGERY = {
  **BASELINE_SPACE,
  "edge_surgery": True,
  "edge_surgery_min_hour_trades": 3,
  "edge_surgery_max_hour_wr": 0.42,
  "edge_surgery_dominant_side_ratio": 0.70,
  "edge_surgery_hours": True,
}

EDGE_SURGERY_RR = {
  **EDGE_SURGERY,
  "rr_ratios": [2.5, 3.0, 3.2],
  "selection_mode": "expectancy_frontier",
}

EDGE_SURGERY_V2 = {
  **EDGE_SURGERY_RR,
  "edge_surgery_min_hour_trades": 3,
  "edge_surgery_max_hour_wr": 0.45,
  "edge_surgery_dominant_side_ratio": 0.65,
  "drawdown_penalty": 1.0,
  "loss_streak_penalty": 2.0,
  "target_trades_per_week": 9.0,
}

EDGE_SURGERY_V2_CLEAN = {
  **EDGE_SURGERY_V2,
  "score_thresholds": [1.0, 1.6, 2.2],
  "ml_probability_thresholds": [0.40, 0.44, 0.48],
  "min_rules_matches": [2],
}

FRONTIER_RR_HI = {
  **FRONTIER_RR,
  "rr_ratios": [2.8, 3.0, 3.2],
}

# Breakthrough: train-calibrated anti-chase (RSI exhaustion veto on shorts).
ANTI_CHASE = {
  **FRONTIER_RR,
  "anti_chase": True,
  "anti_chase_mode": "calibrate",
  "anti_chase_rsi_caps": [58.0, 60.0, 62.0, 65.0, 68.0, 100.0],
  "anti_chase_min_tpw": 5.0,
  "anti_chase_use_vwap": False,
  "target_trades_per_week": 7.0,
}

# Stricter quality: allow lower frequency for higher WR.
ANTI_CHASE_STRICT = {
  **ANTI_CHASE,
  "anti_chase_rsi_caps": [55.0, 58.0, 60.0, 62.0, 65.0],
  "anti_chase_min_tpw": 4.0,
  "target_trades_per_week": 6.0,
}

# Nova: anti-chase + VWAP extension veto + side-only surgery.
NOVA = {
  **ANTI_CHASE,
  "anti_chase_use_vwap": True,
  "anti_chase_vwap_caps": [1.5, 2.0, 2.5, 99.0],
  "edge_surgery": True,
  "edge_surgery_hours": False,
  "edge_surgery_dominant_side_ratio": 0.65,
}

# Fixed gates (same genomes as frontier_rr, veto only at entry) — true WR lever.
ANTI_CHASE_FIXED_62 = {
  **FRONTIER_RR,
  "anti_chase": True,
  "anti_chase_mode": "fixed",
  "anti_chase_fixed_rsi": 62.0,
  "anti_chase_use_vwap": False,
  "target_trades_per_week": 7.0,
}

ANTI_CHASE_FIXED_65 = {
  **ANTI_CHASE_FIXED_62,
  "anti_chase_fixed_rsi": 65.0,
}

ANTI_CHASE_FIXED_68 = {
  **ANTI_CHASE_FIXED_62,
  "anti_chase_fixed_rsi": 68.0,
}

ANTI_CHASE_FIXED_70 = {
  **ANTI_CHASE_FIXED_62,
  "anti_chase_fixed_rsi": 70.0,
}

# AND-void: only cancel when RSI and VWAP are both exhaustion (keeps more R).
ANTI_CHASE_AND_65_2 = {
  **FRONTIER_RR,
  "anti_chase": True,
  "anti_chase_mode": "fixed",
  "anti_chase_logic": "and",
  "anti_chase_fixed_rsi": 65.0,
  "anti_chase_use_vwap": True,
  "anti_chase_fixed_vwap": 2.0,
  "target_trades_per_week": 8.0,
}

ANTI_CHASE_AND_68_2 = {
  **ANTI_CHASE_AND_65_2,
  "anti_chase_fixed_rsi": 68.0,
}

ANTI_CHASE_AND_70_15 = {
  **ANTI_CHASE_AND_65_2,
  "anti_chase_fixed_rsi": 70.0,
  "anti_chase_fixed_vwap": 1.5,
}

NOVA_FIXED = {
  **ANTI_CHASE_FIXED_65,
  "anti_chase_use_vwap": True,
  "anti_chase_fixed_vwap": 2.0,
  "edge_surgery": True,
  "edge_surgery_hours": False,
  "edge_surgery_dominant_side_ratio": 0.65,
}

# Challenge: WR>60% × RR>3 (accept lower Total R).
# Math: loss drag ~1.15R ⇒ need avg_win ≥ ~3.5; quality void lifts WR.
ELITE_60_3 = {
  **BASELINE_SPACE,
  "rr_ratios": [3.5, 4.0],
  "selection_mode": "elite_frontier",
  "exit_modes_full_only": True,
  "anti_chase": True,
  "anti_chase_mode": "fixed",
  "anti_chase_fixed_rsi": 58.0,
  "anti_chase_use_vwap": False,
  "target_trades_per_week": 3.0,
  "drawdown_penalty": 0.5,
  "loss_streak_penalty": 1.0,
}

# Same + VWAP extension void (OR) — higher WR, fewer fills.
ELITE_60_3_VWAP = {
  **ELITE_60_3,
  "anti_chase_use_vwap": True,
  "anti_chase_fixed_vwap": 1.2,
  "anti_chase_logic": "or",
}

# Tighter RSI admit + RR 4.0 only.
ELITE_55_4 = {
  **ELITE_60_3,
  "rr_ratios": [4.0],
  "anti_chase_fixed_rsi": 55.0,
  "target_trades_per_week": 2.5,
}

# elite_55_4 + VWAP OR-void — WR↑ hơn elite_55_4 (ít lệnh hơn).
ELITE_55_4_VWAP = {
  **ELITE_55_4,
  "anti_chase_use_vwap": True,
  "anti_chase_fixed_vwap": 1.2,
  "anti_chase_logic": "or",
}

# Sweet-spot OR-void: RSI≥58 or VWAP≥1.5, RR ladder 3.2–4.0.
ELITE_OR_QUALITY = {
  **ELITE_60_3,
  "rr_ratios": [3.2, 3.5, 4.0],
  "anti_chase_fixed_rsi": 58.0,
  "anti_chase_use_vwap": True,
  "anti_chase_fixed_vwap": 1.5,
  "anti_chase_logic": "or",
  "target_trades_per_week": 3.5,
}

# Elite void + side surgery (nova lever) — bridge WR↑ elite và R↑ nova trên GBP.
_ELITE_SURGERY = {
  "edge_surgery": True,
  "edge_surgery_hours": False,
  "edge_surgery_dominant_side_ratio": 0.65,
}
ELITE_OR_SURGERY = {**ELITE_OR_QUALITY, **_ELITE_SURGERY}
ELITE_VWAP_SURGERY = {**ELITE_60_3_VWAP, **_ELITE_SURGERY}
ELITE_55_SURGERY = {**ELITE_55_4, **_ELITE_SURGERY}

# Conf-style: slightly looser RSI but still full+high RR.
ELITE_60_35 = {
  **ELITE_60_3,
  "rr_ratios": [3.5],
  "anti_chase_fixed_rsi": 60.0,
  "target_trades_per_week": 4.0,
}

# Post-fill GBP (SL = ATR×mult + 1 spread, entry-bar + ask): old RR 3.2–4.0
# puts TP too far. Modest RR>2 + more fills so OOS 2026 can clear R>80 at WR>50.
GBP_FILL_BOOK = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [2.4, 2.8, 3.2],
  "atr_multipliers": [0.85, 1.05],
  "anti_chase_fixed_rsi": 60.0,
  "anti_chase_fixed_vwap": 1.8,
  "target_trades_per_week": 5.0,
  "drawdown_penalty": 0.6,
  "loss_streak_penalty": 1.2,
}

GBP_FILL_SNIPER = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [2.5, 3.0, 3.5],
  "atr_multipliers": [0.9, 1.05],
  "anti_chase_fixed_rsi": 58.0,
  "anti_chase_fixed_vwap": 1.5,
  "target_trades_per_week": 4.0,
}

GBP_FILL_FLOW = {
  **NOVA_FIXED,
  "rr_ratios": [2.2, 2.5, 3.0],
  "exit_modes_full_only": True,
  "anti_chase_fixed_rsi": 62.0,
  "anti_chase_fixed_vwap": 2.0,
  "target_trades_per_week": 6.0,
  "drawdown_penalty": 0.8,
  "loss_streak_penalty": 1.5,
}

# Stricter WR hunt after realistic fills (London hours, higher ML/score, RSI 55).
GBP_FILL_WR = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [2.2, 2.5, 2.8],
  "atr_multipliers": [0.85, 1.0],
  "session_ranges": [[8, 17]],
  "score_thresholds": [1.6, 2.2, 2.8],
  "min_rules_matches": [2],
  "ml_probability_thresholds": [0.44, 0.48, 0.52],
  "min_bars_between": [16],
  "anti_chase_fixed_rsi": 55.0,
  "anti_chase_fixed_vwap": 1.2,
  "target_trades_per_week": 3.0,
  "drawdown_penalty": 0.8,
  "loss_streak_penalty": 1.5,
}

# Lift WR on the fill_book volume path: kill mediocre train-hours / weak side,
# keep expectancy_frontier so n stays large enough for R>80 on 2025–2026 OOS.
_GBP_WR50_BASE = {
  **GBP_FILL_BOOK,
  "selection_mode": "expectancy_frontier",
  "exit_modes_full_only": True,
  "edge_surgery": True,
  "edge_surgery_hours": True,
  "edge_surgery_min_hour_trades": 4,
  "edge_surgery_max_hour_wr": 0.48,
  "edge_surgery_dominant_side_ratio": 0.60,
  "anti_chase": True,
  "anti_chase_mode": "fixed",
  "anti_chase_fixed_rsi": 55.0,
  "anti_chase_use_vwap": True,
  "anti_chase_fixed_vwap": 1.5,
  "anti_chase_logic": "or",
  "target_trades_per_week": 4.5,
}
GBP_WR50_SURG = {**_GBP_WR50_BASE}
GBP_WR50_1TD = {**_GBP_WR50_BASE, "max_trades_per_day": 1}
GBP_WR50_SHORT = {**_GBP_WR50_BASE, "force_side": "short"}
GBP_WR50_LONDON = {
  **_GBP_WR50_BASE,
  "session_ranges": [[8, 16]],
}
GBP_WR50_ELITE = {
  **_GBP_WR50_BASE,
  "selection_mode": "elite_frontier",
  "target_trades_per_week": 3.5,
}
GBP_WR50_TIGHT = {
  **_GBP_WR50_BASE,
  "edge_surgery_min_hour_trades": 3,
  "edge_surgery_max_hour_wr": 0.50,
  "edge_surgery_dominant_side_ratio": 0.55,
  "anti_chase_fixed_rsi": 52.0,
  "anti_chase_fixed_vwap": 1.2,
  "score_thresholds": [1.0, 1.6, 2.2],
  "ml_probability_thresholds": [0.40, 0.44, 0.48],
}
GBP_WR50_SHORT_1TD = {
  **_GBP_WR50_BASE,
  "force_side": "short",
  "max_trades_per_day": 1,
}
GBP_WR50_SHORT_LONDON = {
  **GBP_WR50_LONDON,
  "force_side": "short",
}
GBP_WR50_LONDON_1TD = {
  **GBP_WR50_LONDON,
  "max_trades_per_day": 1,
}

# EUR M15 after SL = ATR×mult + 1 spread and entry-bar Ask check.
# Elite RR 3.5–4.0 put TP ~15–20 pip → OOS WR collapsed to ~13%.
# Bar WR>55 / R>90 / RR>2.5: EV at WR55×RR2.6 ≈ 0.98R/trade → ~90 trades on 2026 OOS.
# Floor RR at 2.6 so avg_rr stays strictly above the 2.5 filter. ATR ≥ 1.05 so
# SL still has room after +1.9 pip spread.
_EUR_WR55_BASE = {
  **_GBP_WR50_BASE,
  "rr_ratios": [2.6, 2.8, 3.2],
  "atr_multipliers": [1.05, 1.2, 1.35],
  "session_ranges": [[8, 17]],
  "score_thresholds": [1.0, 1.6, 2.2],
  "min_rules_matches": [2],
  "ml_probability_thresholds": [0.40, 0.44, 0.48],
  "anti_chase_fixed_rsi": 55.0,
  "anti_chase_fixed_vwap": 1.5,
  "target_trades_per_week": 4.5,
  "drawdown_penalty": 0.7,
  "loss_streak_penalty": 1.2,
}
EUR_WR55_LONDON = {**_EUR_WR55_BASE}
EUR_WR55_SURG = {
  **_EUR_WR55_BASE,
  "edge_surgery_min_hour_trades": 3,
  "edge_surgery_max_hour_wr": 0.50,
  "edge_surgery_dominant_side_ratio": 0.55,
  "anti_chase_fixed_rsi": 52.0,
  "anti_chase_fixed_vwap": 1.2,
}
EUR_WR55_SNIPER = {
  **_EUR_WR55_BASE,
  "rr_ratios": [2.8, 3.2],
  "atr_multipliers": [1.2, 1.35],
  "score_thresholds": [1.6, 2.2, 2.8],
  "ml_probability_thresholds": [0.44, 0.48, 0.52],
  "min_bars_between": [16],
  "selection_mode": "elite_frontier",
  "target_trades_per_week": 3.5,
  "anti_chase_fixed_rsi": 55.0,
  "anti_chase_fixed_vwap": 1.2,
}
EUR_WR55_1TD = {**_EUR_WR55_BASE, "max_trades_per_day": 1}
# 1td printed WR55/RR2.85 at n=18 R=20 — Total R is the gap. 2td London with
# milder hour/side cuts and a lower score floor so days with a second setup fill.
EUR_WR55_2TD = {
  **_EUR_WR55_BASE,
  "max_trades_per_day": 2,
  "target_trades_per_week": 6.5,
  "edge_surgery_min_hour_trades": 6,
  "edge_surgery_max_hour_wr": 0.40,
  "edge_surgery_dominant_side_ratio": 0.70,
  "min_rules_matches": [1, 2],
  "score_thresholds": [0.6, 1.0, 1.6],
  "min_bars_between": [8, 12],
}
# 2td is at most ~2× vs 1td; R>90 needs ~4× n. Third London fill/day with 8-bar
# spacing so a day can actually take 3. RR floor stays 2.6 (filter WR/RR unchanged).
EUR_WR55_3TD = {
  **EUR_WR55_2TD,
  "max_trades_per_day": 3,
  "target_trades_per_week": 8.5,
  "min_bars_between": [8],
}
EUR_WR55_FLOW = {
  **_EUR_WR55_BASE,
  "rr_ratios": [2.6, 2.8, 3.0],
  "atr_multipliers": [1.05, 1.2],
  "session_ranges": [[7, 20]],
  "min_rules_matches": [1, 2],
  "score_thresholds": [0.6, 1.0, 1.6],
  "target_trades_per_week": 5.5,
  "drawdown_penalty": 0.5,
}
# Lift realized avg_rr above 2.5 (fill-aware books printed ~2.3 on 2025–2026).
EUR_WR55_RR3 = {
  **EUR_WR55_1TD,
  "rr_ratios": [3.0, 3.5],
  "atr_multipliers": [1.2, 1.35],
  "selection_mode": "elite_frontier",
  "target_trades_per_week": 3.5,
}
EUR_WR55_SHORT = {**EUR_WR55_LONDON, "force_side": "short"}
EUR_WR55_LONG = {**EUR_WR55_LONDON, "force_side": "long"}
# 1td+LONG on 2025 printed WR~56 / RR~2.8 / R~20 at n=18. Need ~4× fills for R>90.
EUR_WR55_1TD_LONG = {**EUR_WR55_1TD, "force_side": "long"}
EUR_WR55_QTY = {
  **EUR_WR55_1TD_LONG,
  "max_trades_per_day": 2,
  "target_trades_per_week": 6.5,
  "score_thresholds": [0.6, 1.0, 1.6],
  "ml_probability_thresholds": [0.36, 0.40, 0.44],
  "min_rules_matches": [1, 2],
  "session_ranges": [[7, 18]],
  "rr_ratios": [2.8, 3.2],
  "min_bars_between": [8, 16],
}

# Total R ceiling on the eur_wr55 family was ~24R/year because Total R = n × EV
# and n stalled at 18–28 per year. Measured cause (scripts/diag_e21_fillrate.py):
# genomes were ranked WITHOUT the fixed anti-chase veto, so the miner preferred
# dip/fade long rules that fire at RSI ≤ 45 — exactly what the veto then deletes
# (89 candidates/8.9w → 2 fills). Ranking with the veto lifts OOS fills ~7–12×.
# The frequency floor stops the other half of the problem: a genome could clear
# the miner with 3 trades per 6-week window, which wins on sample noise and then
# never fires OOS.
#
# Axis placement (audit 2026-08-31, scripts/audit_mining_space.py): the miner scans
# every list key below, but reads selection_mode / anti_chase_fixed_rsi / vwap /
# max_trades_per_day / min_trades_per_week as single values. So a knob that is a
# list here needs no preset of its own, and a scalar knob can only be explored by
# adding a preset. session_ranges is scanned (strategy_miner ~L1372), hence London
# 8–17 lives here as a second range instead of a separate eur_r100_london — the
# miner picks the better window per genome. Paid for by dropping the middle ML
# gate: 0.38/0.42/0.46 was a narrow band, and bracketing it costs less resolution
# than losing a trading-hours axis.
_EUR_R100_BASE = {
  **_EUR_WR55_BASE,
  "anti_chase_score_with_veto": True,
  "min_trades_per_week": 1.5,
  "min_rules_matches": [1, 2],
  "score_thresholds": [0.6, 1.0, 1.6],
  "ml_probability_thresholds": [0.38, 0.46],
  "session_ranges": [[7, 19], [8, 17]],
  "max_trades_per_day": 2,
  "min_bars_between": [8, 12],
  "target_trades_per_week": 6.0,
}
# --- Active e21 lineup: 4 presets, one per non-scannable axis -----------------
# WR>55 at RR>2.5 pins EV at 0.55×2.5 − 0.45 = 0.925R/trade, so Total R>100 is
# exactly n≥108. On the 34.1-week 2026 OOS that is tpw≥3.17, so three of the four
# share one frequency block set at the smallest floor that still guarantees the
# bar. Deliberately not higher: a floor of 4.0 would reject a genome sustaining
# 3.5 fills/week, which clears n≥108 comfortably. Fixing the block this way
# leaves the three free to differ only in what they hunt, so the grid measures
# the ranking/veto axes instead of re-measuring frequency three times.
_EUR_R100_FAST = {
  "min_trades_per_week": 3.2,
  "max_trades_per_day": 4,
  "min_bars_between": [4, 8],
  "target_trades_per_week": 12.0,
}
# 1. Expectancy ranking at the required frequency — the primary candidate.
EUR_R100_HYPER = {
  **_EUR_R100_BASE,
  **_EUR_R100_FAST,
}
# 2. Same frequency block, elite_frontier ranking (WR×RR near 60/3.0). Isolates
# selection_mode — a scalar, so it cannot be scanned inside one preset. Placed at
# passing frequency on purpose: the old eur_r100_elite tested it at a 1.5 floor,
# where no result clears R>100 whichever way it ranks.
EUR_R100_HYPER_ELITE = {
  **_EUR_R100_BASE,
  **_EUR_R100_FAST,
  "selection_mode": "elite_frontier",
}
# 3. Veto width. fixed_rsi splits the sides: long needs rsi > 100-cap, short needs
# rsi < cap. 62 widens the overlap band, which adds fills — the direction that
# helps reach the tpw floor, unlike RSI 50 (stricter → fewer fills). Now that
# ranking sees the veto, this cap's value is finally learnable.
EUR_R100_WIDE = {
  **_EUR_R100_BASE,
  **_EUR_R100_FAST,
  "anti_chase_fixed_rsi": 62.0,
  "anti_chase_fixed_vwap": 2.0,
}
# 4. Low-frequency control at 2 fills/day. Cannot clear R>100; it is here to show
# whether WR>55 only survives when trading rarely. If it does, the R shortfall is
# a window-length problem, not a rule-quality one.
EUR_R100_CORE = {**_EUR_R100_BASE}

# --- Retired by the 2026-08-31 audit; kept for CLI / regression reproducibility.
# Two distinct reasons, worth keeping apart (scripts/audit_mining_space.py):
#
# (a) Redundant. Same ranking + veto identity as a survivor, and their scanned
#     space is contained in it, so the survivor's run already visits it. What is
#     left over is a lower trades/week floor, i.e. permission to accept genomes
#     sparser than tpw 3.17 — precisely the region that cannot reach Total R>100.
#       elite     → hyper_elite : identical scanned space, floor 1.5
#       elite_rr3 → hyper_elite : rr [2.8,3.2] ⊂ [2.6,2.8,3.2], atr ⊂, floor 1.2
#       dense     → hyper       : min_bars_between [8] ⊂ [4,8], cap 3 ≤ 4, floor 3.0
#       london    → all four    : differed only by session_ranges, now scanned
#
# (b) Dropped by choice, not redundancy. trend explores a real axis point no
#     survivor covers (RSI 50), but 50 is the strictest veto and therefore the
#     fewest-fills direction — it pulls against the tpw≥3.17 the bar demands.
#     Bring it back if the wide/RSI-62 branch shows veto width drives WR.
EUR_R100_ELITE = {
  **_EUR_R100_BASE,
  "selection_mode": "elite_frontier",
  "target_trades_per_week": 5.0,
}
EUR_R100_ELITE_RR3 = {
  **EUR_R100_ELITE,
  "rr_ratios": [2.8, 3.2],
  "atr_multipliers": [1.2, 1.35],
  "min_trades_per_week": 1.2,
  "target_trades_per_week": 4.0,
}
EUR_R100_LONDON = {
  **_EUR_R100_BASE,
  "session_ranges": [[8, 17]],
  "min_trades_per_week": 1.2,
}
EUR_R100_DENSE = {
  **_EUR_R100_BASE,
  "min_trades_per_week": 3.0,
  "max_trades_per_day": 3,
  "min_bars_between": [8],
  "target_trades_per_week": 9.0,
}
EUR_R100_TREND = {
  **_EUR_R100_BASE,
  "anti_chase_fixed_rsi": 50.0,
  "min_trades_per_week": 1.2,
}

# Generic / g23 fallback. e21 uses E21_RECOMMENDED_PRESET after live-like fills.
RECOMMENDED_PRESET = "elite_or_quality"
E21_RECOMMENDED_PRESET = "eur_r100_hyper"
E21_DEFAULT_PRESETS: tuple[str, ...] = ("eur_r100_hyper", "eur_r100_core")

# Shown in Settings UI — trimmed 2026-08-10 (drop near-duplicate elite / frontier).
# Keep: default quality · R-balance · gentle edge · niche elite · baseline neo.
# See docs/mining_space_audit.md.
CURATED_PRESETS: tuple[str, ...] = (
  "elite_or_quality",
  "anti_chase_fixed_70",
  "edge_gentle",
  "elite_55_4",
  "baseline",
)
# e21 after SL+spread: hide elite RR 3.2–4 (OOS WR collapsed ~13%).
# eur_r100_* lead: the eur_wr55_* family tops out near 24R/year on fill-aware
# books because the anti-chase veto deletes most mined signals post-ranking.
# Cut 8 → 4 by the 2026-08-31 audit: three high-frequency branches spanning the
# scalar axes (expectancy / elite ranking / wide veto) plus one slow control.
E21_CURATED_PRESETS: tuple[str, ...] = (
  "eur_r100_hyper",
  "eur_r100_hyper_elite",
  "eur_r100_wide",
  "eur_r100_core",
)

# Lost A/B vs baseline / redundant vs curated — hidden from Settings.
# Still in PRESETS for CLI / regression / old Trade Models.
DEPRECATED_PRESETS: tuple[str, ...] = (
  "wr_rr_frontier",
  "wr_rr_sniper",
  "wr_rr_lock",
  "edge_surgery_v2_clean",
  "edge_surgery_rr",
  "edge_side_only",
  "edge_surgery_v2",
  "frontier_rr",
  "edge_surgery",
  "anti_chase_fixed_68",
  "elite_60_35",
  "anti_chase",
  "anti_chase_and_70_15",
  # Redundant with curated (2026-08-10)
  "elite_60_3",
  "elite_60_3_vwap",
  "frontier_rr_hi",
  "nova",
  "nova_fixed",
  "anti_chase_fixed_62",
  "anti_chase_fixed_65",
  "anti_chase_strict",
  "anti_chase_and_65_2",
  "anti_chase_and_68_2",
  # Redundant by set containment / wrong frequency block (2026-08-31 audit)
  "eur_r100_elite",
  "eur_r100_elite_rr3",
  "eur_r100_london",
  "eur_r100_dense",
  "eur_r100_trend",
)

# Compact labels for Settings / Grid UI (unknown keys fall back to raw name).
PRESET_LABELS: dict[str, str] = {
  "baseline": "Baseline (mặc định miner)",
  "frontier_rr": "Frontier + RR ladder",
  "frontier_rr_hi": "Frontier RR hi",
  "edge_gentle": "Edge gentle (R↑ DD↓)",
  "anti_chase": "Anti-chase calibrate",
  "anti_chase_fixed_70": "Anti-chase RSI<70 (cân bằng R)",
  "anti_chase_and_70_15": "Anti-chase AND RSI∨VWAP",
  "elite_60_3": "Elite WR60 · RR3.5–4",
  "elite_60_3_vwap": "Elite WR60 · VWAP",
  "elite_55_4": "Elite WR60 · RR4 (ít lệnh)",
  "elite_or_quality": "Elite OR-quality",
  "eur_wr55_london": "EUR WR55 · London (khuyến nghị e21)",
  "elite_60_35": "Elite RSI60 · RR3.5",
  "gbp_fill_book": "GBP fill-aware · WR>50 R>80",
  "gbp_fill_sniper": "GBP fill sniper · WR-first",
  "gbp_fill_flow": "GBP fill flow · volume + RR>2",
  "gbp_fill_wr": "GBP fill WR-first · London",
  "gbp_wr50_surg": "GBP WR50 · hour/side surgery",
  "gbp_wr50_1td": "GBP WR50 · 1 lệnh/ngày",
  "gbp_wr50_short": "GBP WR50 · SHORT only",
  "gbp_wr50_london": "GBP WR50 · London 8–16",
  "gbp_wr50_elite": "GBP WR50 · elite frontier",
  "gbp_wr50_tight": "GBP WR50 · RSI52 + hour≤50%",
  "gbp_wr50_short_1td": "GBP WR50 · SHORT + 1td",
  "gbp_wr50_short_london": "GBP WR50 · SHORT London",
  "gbp_wr50_london_1td": "GBP WR50 · London 1td",
  "eur_wr55_surg": "EUR WR55 · hour/side surgery",
  "eur_wr55_sniper": "EUR WR55 · elite sniper",
  "eur_wr55_1td": "EUR WR55 · 1 lệnh/ngày",
  "eur_wr55_2td": "EUR WR55 · 2 lệnh/ngày London",
  "eur_wr55_3td": "EUR WR55 · 3 lệnh/ngày London",
  "eur_wr55_flow": "EUR WR55 · volume + RR>2.5",
  "eur_wr55_rr3": "EUR WR55 · RR≥3 1td",
  "eur_wr55_short": "EUR WR55 · SHORT London",
  "eur_wr55_long": "EUR WR55 · LONG London",
  "eur_r100_hyper": "EUR R100 · đủ tần suất cho R>100 (khuyến nghị e21)",
  "eur_r100_hyper_elite": "EUR R100 · tần suất + elite WR×RR",
  "eur_r100_wide": "EUR R100 · tần suất + veto rộng RSI 62",
  "eur_r100_core": "EUR R100 · đối chứng 2 lệnh/ngày",
  "eur_r100_elite": "EUR R100 · elite WR×RR",
  "eur_r100_elite_rr3": "EUR R100 · elite RR 2.8–3.2",
  "eur_r100_london": "EUR R100 · London 8–17",
  "eur_r100_dense": "EUR R100 · 3 lệnh/ngày (Total R↑)",
  "eur_r100_trend": "EUR R100 · trend RSI 50",
}

# Single source for Settings catalog + Trade Model direction line.
# intent = dùng khi nào; knobs = đòn bẩy chính; tradeoff = cái đổi lấy được.
PRESET_BLURBS: dict[str, dict[str, str]] = {
  "baseline": {
    "intent": "So sánh công bằng / hành vi miner cũ",
    "knobs": "RR 2.5–3 · exit full/hybrid/partial · legacy score",
    "tradeoff": "~9 lệnh/tuần · WR thấp hơn Elite · Total R cao hơn",
  },
  "frontier_rr_hi": {
    "intent": "Chấm joint WR×RR nhẹ, gần giữ Total R",
    "knobs": "RR ladder cao hơn · expectancy_frontier",
    "tradeoff": "Gần baseline về tần suất; lift nhẹ chất lượng",
  },
  "edge_gentle": {
    "intent": "Cắt giờ/side độc trên train; giữ gần tần suất baseline",
    "knobs": "edge_surgery nhẹ · frontier RR",
    "tradeoff": "R↑ DD↓ so với baseline; vẫn nhiều lệnh",
  },
  "anti_chase": {
    "intent": "Void đuổi giá — RSI/VWAP calibrate trên train",
    "knobs": "anti_chase calibrate · ngưỡng học từ train",
    "tradeoff": "WR↑ · tần suất vừa (~5 lệnh/tuần)",
  },
  "anti_chase_fixed_70": {
    "intent": "Cân bằng WR + Total R (void RSI≥70 cố định)",
    "knobs": "anti_chase fixed RSI<70 · không re-rank genome",
    "tradeoff": "WR↑ nhẹ và Total R↑; gần tần suất baseline",
  },
  "anti_chase_and_70_15": {
    "intent": "Void chỉ khi RSI và VWAP đều chase (AND)",
    "knobs": "fixed RSI∨VWAP · logic AND",
    "tradeoff": "Ít void hơn OR · gần giữ Total R",
  },
  "elite_or_quality": {
    "intent": "Ưu tiên WR/DD — mặc định desk không phải e21",
    "knobs": "void RSI≥58 OR VWAP≥1.5 · RR 3.2–4 · exit full · elite_frontier",
    "tradeoff": "WR/DD tốt trước fill; sau SL+spread TP xa → WR OOS sụp",
  },
  "elite_60_3": {
    "intent": "Elite WR-first, chỉ RSI void (không VWAP)",
    "knobs": "RSI≥58 fixed · RR 3.5–4 · exit full · elite_frontier",
    "tradeoff": "WR cao · ít lệnh hơn baseline",
  },
  "elite_60_3_vwap": {
    "intent": "Elite siết hơn bằng VWAP OR",
    "knobs": "RSI≥58 OR VWAP≥1.2 · RR 3.5–4 · exit full",
    "tradeoff": "WR cao hơn elite_60_3 · fill ít hơn",
  },
  "elite_55_4": {
    "intent": "Niche WR>60 & RR>3 — rất chọn lọc",
    "knobs": "RSI≥55 · RR 4.0 only · exit full",
    "tradeoff": "RR cao · rất ít lệnh (~1/tuần)",
  },
  "elite_60_35": {
    "intent": "Elite dự phòng — RSI lỏng hơn một chút",
    "knobs": "RSI≥60 · RR 3.5 · exit full",
    "tradeoff": "Cân bằng hơn elite chặt; vẫn chất lượng > tần suất",
  },
  "gbp_fill_book": {
    "intent": "GBP sau fill thật — WR>50 và Total R>80",
    "knobs": "RR 2.4–3.2 · ATR 0.85/1.05 · RSI<60 OR VWAP<1.8 · TPW 5 · exit full",
    "tradeoff": "TP gần hơn elite cũ (SL đã +spread) · nhiều lệnh hơn sniper",
  },
  "gbp_fill_sniper": {
    "intent": "GBP fill-aware, ưu tiên WR",
    "knobs": "RR 2.5–3.5 · RSI<58 OR VWAP<1.5 · TPW 4 · exit full",
    "tradeoff": "Ít lệnh hơn fill_book · WR cao hơn, R có thể thấp hơn",
  },
  "gbp_fill_flow": {
    "intent": "GBP fill-aware, gom R bằng tần suất",
    "knobs": "nova_fixed + RR 2.2–3 · exit full · TPW 6",
    "tradeoff": "Nhiều lệnh hơn elite · WR có thể thấp hơn fill_book",
  },
  "gbp_fill_wr": {
    "intent": "GBP fill-aware, săn WR>50",
    "knobs": "London 8–17 · RR 2.2–2.8 · RSI<55 OR VWAP<1.2 · ML≥0.44 · TPW 3",
    "tradeoff": "Rất ít lệnh · WR cao hơn fill_book",
  },
  "gbp_wr50_surg": {
    "intent": "Nâng WR trên sách R cao — cắt giờ/side độc trên train",
    "knobs": "hour WR≤48% · side veto · RSI<55 OR VWAP<1.5 · RR 2.4–3.2",
    "tradeoff": "Ít lệnh hơn fill_book · WR↑ nếu giờ độc OOS giống train",
  },
  "gbp_wr50_1td": {
    "intent": "Chỉ lệnh đầu ngày — bỏ re-entry sau SL",
    "knobs": "max 1 lệnh/ngày + surgery WR50",
    "tradeoff": "n↓ · WR↑ nếu lệnh 2 trong ngày là loser",
  },
  "gbp_wr50_short": {
    "intent": "GBP SHORT-only sau fill thật",
    "knobs": "force_side=short + surgery WR50",
    "tradeoff": "Mất long · WR↑ nếu long là bên yếu",
  },
  "gbp_wr50_london": {
    "intent": "Chỉ London 8–16 + surgery WR50",
    "knobs": "session 8–16 · hour/side surgery",
    "tradeoff": "Bỏ Asia/NY close",
  },
  "gbp_wr50_elite": {
    "intent": "Chọn genome WR-first trên sách fill",
    "knobs": "elite_frontier + surgery + RSI<55",
    "tradeoff": "Ít lệnh hơn expectancy · WR↑ nếu frontier không drift",
  },
  "gbp_wr50_tight": {
    "intent": "Siết giờ độc + RSI 52 trên sách R",
    "knobs": "hour WR≤50% n≥3 · side 55% · RSI<52 OR VWAP<1.2",
    "tradeoff": "n↓ mạnh · WR↑ nếu chase/giờ độc là loser",
  },
  "gbp_wr50_short_1td": {
    "intent": "SHORT + 1 lệnh/ngày",
    "knobs": "force_side=short · max_trades_per_day=1",
    "tradeoff": "n thấp · cần OOS dài để R>80",
  },
  "gbp_wr50_short_london": {
    "intent": "SHORT trong London",
    "knobs": "force_side=short · session 8–16",
    "tradeoff": "Bỏ long + Asia/NY",
  },
  "gbp_wr50_london_1td": {
    "intent": "London + 1 lệnh/ngày",
    "knobs": "session 8–16 · max_trades_per_day=1",
    "tradeoff": "n thấp · WR↑ nếu lệnh 2 là loser",
  },
  "eur_wr55_london": {
    "intent": "EUR M15 sau fill thật — WR>55 RR>2.5 (khuyến nghị e21)",
    "knobs": "London 8–17 · RR 2.6–3.2 · ATR 1.05–1.35 · RSI<55 OR VWAP · TPW 4.5",
    "tradeoff": "TP gần hơn elite RR4 (SL đã +spread) · nhiều lệnh hơn sniper",
  },
  "eur_wr55_surg": {
    "intent": "Siết giờ/side độc trên sách EUR fill",
    "knobs": "hour WR≤50% · side 55% · RSI<52 OR VWAP<1.2",
    "tradeoff": "n↓ · WR↑ nếu giờ độc OOS giống train",
  },
  "eur_wr55_sniper": {
    "intent": "EUR WR-first trên fill — elite frontier",
    "knobs": "RR 2.8–3.2 · ATR 1.2–1.35 · ML≥0.44 · elite_frontier · TPW 3.5",
    "tradeoff": "Ít lệnh hơn london · WR↑, R có thể thấp hơn",
  },
  "eur_wr55_1td": {
    "intent": "Chỉ lệnh đầu ngày — bỏ re-entry sau SL",
    "knobs": "max 1 lệnh/ngày + London fill WR55",
    "tradeoff": "n↓ · WR↑ nếu lệnh 2 trong ngày là loser",
  },
  "eur_wr55_2td": {
    "intent": "Gom Total R khi 1td kẹt n≈18 R≈20, vẫn WR>55 RR>2.5",
    "knobs": "max 2 lệnh/ngày · London 8–17 · surgery nhẹ (hour n≥6 WR≤40%)",
    "tradeoff": "n↑ vs 1td · WR có thể thấp hơn nếu lệnh 2 yếu",
  },
  "eur_wr55_3td": {
    "intent": "Backup volume khi 2td vẫn thiếu n cho R>90",
    "knobs": "max 3 lệnh/ngày · London 8–17 · spacing 8 bar · surgery nhẹ",
    "tradeoff": "n↑ vs 2td · WR có thể thấp hơn nếu lệnh 3 yếu",
  },
  "eur_wr55_flow": {
    "intent": "Gom R bằng tần suất, vẫn RR>2.5",
    "knobs": "session 7–20 · RR 2.6–3.0 · TPW 5.5 · min_rules 1–2",
    "tradeoff": "Nhiều lệnh hơn london · WR có thể thấp hơn sniper",
  },
  "eur_r100_core": {
    "intent": "Đối chứng chậm: kiểm tra xem WR>55 có chỉ sống khi giao dịch thưa",
    "knobs": "2 lệnh/ngày · sàn 1.5 lệnh/tuần · veto-aware · session 7–19 & 8–17",
    "tradeoff": "Không thể chạm R>100 trên 35 tuần · dùng để chẩn đoán, không để chọn",
  },
  "eur_r100_hyper_elite": {
    "intent": "Cùng khối tần suất với hyper nhưng xếp hạng elite WR×RR (60/3.0)",
    "knobs": "elite_frontier · 4 lệnh/ngày · sàn 3.2 lệnh/tuần",
    "tradeoff": "Tách riêng trục selection_mode · WR mục tiêu cao hơn nên n có thể hụt sàn",
  },
  "eur_r100_elite": {
    "intent": "Giữ WR>55 × RR>2.5 trong khi n đủ lớn cho R>100",
    "knobs": "elite_frontier (WR60×RR3) + veto-aware + sàn 1.5 lệnh/tuần",
    "tradeoff": "Ít lệnh hơn dense · cần OOS dài để tích R",
  },
  "eur_r100_elite_rr3": {
    "intent": "Nâng avg_rr thực tế vượt 2.5 sau phí fill",
    "knobs": "RR 2.8–3.2 · ATR 1.2–1.35 · sàn 1.2 lệnh/tuần",
    "tradeoff": "TP xa hơn → WR thấp hơn eur_r100_elite",
  },
  "eur_r100_london": {
    "intent": "Chỉ giờ London, giữ chất lượng vào lệnh",
    "knobs": "session 8–17 · veto-aware · sàn 1.2 lệnh/tuần",
    "tradeoff": "Ít lệnh hơn core → cần OOS ≥18 tháng cho R>100",
  },
  "eur_r100_dense": {
    "intent": "Khi WR còn dư trên mốc 55 mà Total R vẫn thiếu",
    "knobs": "3 lệnh/ngày · spacing 8 bar · sàn 3 lệnh/tuần",
    "tradeoff": "R tăng nhanh nhất · DD và rủi ro WR cao nhất nhóm",
  },
  "eur_r100_hyper": {
    "intent": "Cửa sổ OOS ngắn (~34 tuần): WR>55+RR>2.5 ép EV=0.925R nên R>100 cần n≥108, tức ≥3.17 lệnh/tuần",
    "knobs": "4 lệnh/ngày · spacing 4–8 bar · sàn 3.2 lệnh/tuần · xếp hạng theo kỳ vọng",
    "tradeoff": "Đủ tần suất chạm 100R trong 8 tháng · rủi ro WR tụt dưới 55 cao hơn nhóm chậm",
  },
  "eur_r100_trend": {
    "intent": "Chỉ vào thuận xu hướng: long khi RSI>50, short khi RSI<50",
    "knobs": "anti_chase RSI 50 · veto-aware · sàn 1.2 lệnh/tuần",
    "tradeoff": "Ít lệnh hơn core · WR thường cao nhất nhóm",
  },
  "eur_r100_wide": {
    "intent": "Nới veto để lấy thêm lệnh — hướng duy nhất của trục RSI giúp đạt sàn tần suất",
    "knobs": "anti_chase RSI 62 · VWAP 2.0 · 4 lệnh/ngày · sàn 3.2 lệnh/tuần",
    "tradeoff": "n cao nhất nhóm · WR thấp hơn hyper vì lọc vào lệnh lỏng hơn",
  },
}


def preset_label(name: str) -> str:
  label = PRESET_LABELS.get(name, name)
  if name in DEPRECATED_PRESETS:
    return f"{label} (deprecated)"
  return label


def preset_blurb(name: str) -> dict[str, str]:
  """Intent / knobs / tradeoff for a preset (empty dict if unknown)."""
  return dict(PRESET_BLURBS.get(name) or {})


def _active_desk(desk: str | None = None) -> str:
  if desk:
    return str(desk).strip().lower()
  import os
  return str(os.environ.get("TRAINAPP_DESK") or "").strip().lower()


def recommended_preset(desk: str | None = None) -> str:
  """Settings / Grid default preset for the active desk."""
  if _active_desk(desk) == "e21":
    return E21_RECOMMENDED_PRESET
  return RECOMMENDED_PRESET


def recommended_presets(desk: str | None = None) -> list[str]:
  if _active_desk(desk) == "e21":
    return [n for n in E21_DEFAULT_PRESETS if n in PRESETS]
  return [RECOMMENDED_PRESET]


def list_curated_presets(desk: str | None = None) -> list[str]:
  """Presets offered in Settings UI (excludes deprecated losers)."""
  names = E21_CURATED_PRESETS if _active_desk(desk) == "e21" else CURATED_PRESETS
  return [n for n in names if n in PRESETS]


def list_active_presets() -> list[str]:
  """All non-deprecated presets (CLI / advanced)."""
  return [n for n in PRESETS if n not in DEPRECATED_PRESETS]


def recommended_direction_help(desk: str | None = None) -> str:
  """Help text for the Settings mining picker, built from the preset itself.

  Kept data-derived on purpose. This text used to be two hardcoded branches in
  settings_page keyed on a preset name, and it drifted twice: after the desk moved
  to eur_r100_*, the UI still described "Elite OR-quality · RSI≥58 · RR 3.2–4.0",
  knobs no offered preset actually used. Reading the blurb means the tooltip can
  only ever describe a preset that is really in the list.
  """
  name = recommended_preset(desk)
  blurb = preset_blurb(name)
  knobs = blurb.get("knobs") or _summarize_space_knobs(PRESETS.get(name) or {})
  return (
    f"Hướng **{preset_label(name)}**: {knobs}. "
    "Bỏ trống = miner baseline cũ."
  )


def curated_presets_line(desk: str | None = None) -> str:
  """One line naming the presets Settings currently offers, for guide/glossary."""
  names = list_curated_presets(desk)
  if not names:
    return "—"
  return " · ".join(f"`{n}`" for n in names)


def curated_preset_catalog() -> list[dict[str, str]]:
  """Rows for Settings expander table (curated only)."""
  rows: list[dict[str, str]] = []
  for name in list_curated_presets():
    blurb = preset_blurb(name)
    rows.append({
      "Preset": preset_label(name),
      "Ý định": blurb.get("intent") or "—",
      "Knobs chính": blurb.get("knobs") or _summarize_space_knobs(PRESETS.get(name) or {}),
      "Trade-off": blurb.get("tradeoff") or "—",
    })
  return rows


def _normalize_space_dict(space: dict | None) -> dict:
  """JSON-comparable form (lists, sorted keys) for preset matching."""
  if not space:
    return {}
  return _jsonable(dict(space))


def match_preset_name(space: dict | None) -> str | None:
  """Best-effort: which named preset equals this stored search space."""
  target = _normalize_space_dict(space)
  if not target:
    return None
  for name, preset in PRESETS.items():
    if _normalize_space_dict(preset) == target:
      return name
  return None


def space_direction_line(
  space: dict | None,
  *,
  preset_name: str | None = None,
) -> str:
  """One-line direction for Trade Model / banners."""
  name = preset_name or match_preset_name(space)
  if name:
    blurb = preset_blurb(name)
    intent = blurb.get("intent") or ""
    label = preset_label(name)
    if intent:
      return f"**{label}** — {intent}"
    return f"**{label}**"
  if not space:
    return "**Baseline miner** — không gắn preset (search space mặc định)"
  return (
    f"Space tùy chỉnh · {_summarize_space_knobs(space)}"
  )


def _summarize_space_knobs(space: dict | None) -> str:
  ss = space or {}
  bits: list[str] = []
  mode = ss.get("selection_mode") or "legacy"
  if mode != "legacy":
    bits.append(str(mode))
  if ss.get("rr_ratios") is not None:
    bits.append(f"RR{list(ss.get('rr_ratios'))}")
  if ss.get("anti_chase"):
    rsi = ss.get("anti_chase_fixed_rsi", "?")
    part = f"chase RSI<{rsi}"
    if ss.get("anti_chase_use_vwap"):
      logic = "OR" if ss.get("anti_chase_logic") == "or" else "AND"
      part += f" {logic} VWAP<{ss.get('anti_chase_fixed_vwap', '?')}"
    bits.append(part)
  if ss.get("edge_surgery"):
    bits.append("edge_surgery")
  if ss.get("exit_modes_full_only"):
    bits.append("exit:full")
  return " · ".join(bits) if bits else "baseline knobs"


PRESETS: dict[str, dict] = {
  "baseline": deepcopy(BASELINE_SPACE),
  "wr_rr_sniper": deepcopy(WR_RR_SNIPER),
  "wr_rr_frontier": deepcopy(WR_RR_FRONTIER),
  "wr_rr_lock": deepcopy(WR_RR_LOCK),
  "frontier_rr": deepcopy(FRONTIER_RR),
  "frontier_rr_hi": deepcopy(FRONTIER_RR_HI),
  "edge_side_only": deepcopy(EDGE_SIDE_ONLY),
  "edge_gentle": deepcopy(EDGE_GENTLE),
  "edge_surgery": deepcopy(EDGE_SURGERY),
  "edge_surgery_rr": deepcopy(EDGE_SURGERY_RR),
  "edge_surgery_v2": deepcopy(EDGE_SURGERY_V2),
  "edge_surgery_v2_clean": deepcopy(EDGE_SURGERY_V2_CLEAN),
  "anti_chase": deepcopy(ANTI_CHASE),
  "anti_chase_strict": deepcopy(ANTI_CHASE_STRICT),
  "nova": deepcopy(NOVA),
  "anti_chase_fixed_62": deepcopy(ANTI_CHASE_FIXED_62),
  "anti_chase_fixed_65": deepcopy(ANTI_CHASE_FIXED_65),
  "anti_chase_fixed_68": deepcopy(ANTI_CHASE_FIXED_68),
  "anti_chase_fixed_70": deepcopy(ANTI_CHASE_FIXED_70),
  "anti_chase_and_65_2": deepcopy(ANTI_CHASE_AND_65_2),
  "anti_chase_and_68_2": deepcopy(ANTI_CHASE_AND_68_2),
  "anti_chase_and_70_15": deepcopy(ANTI_CHASE_AND_70_15),
  "nova_fixed": deepcopy(NOVA_FIXED),
  "elite_60_3": deepcopy(ELITE_60_3),
  "elite_60_3_vwap": deepcopy(ELITE_60_3_VWAP),
  "elite_55_4": deepcopy(ELITE_55_4),
  "elite_55_4_vwap": deepcopy(ELITE_55_4_VWAP),
  "elite_or_surgery": deepcopy(ELITE_OR_SURGERY),
  "elite_vwap_surgery": deepcopy(ELITE_VWAP_SURGERY),
  "elite_55_surgery": deepcopy(ELITE_55_SURGERY),
  "elite_or_quality": deepcopy(ELITE_OR_QUALITY),
  "elite_60_35": deepcopy(ELITE_60_35),
  "gbp_fill_book": deepcopy(GBP_FILL_BOOK),
  "gbp_fill_sniper": deepcopy(GBP_FILL_SNIPER),
  "gbp_fill_flow": deepcopy(GBP_FILL_FLOW),
  "gbp_fill_wr": deepcopy(GBP_FILL_WR),
  "gbp_wr50_surg": deepcopy(GBP_WR50_SURG),
  "gbp_wr50_1td": deepcopy(GBP_WR50_1TD),
  "gbp_wr50_short": deepcopy(GBP_WR50_SHORT),
  "gbp_wr50_london": deepcopy(GBP_WR50_LONDON),
  "gbp_wr50_elite": deepcopy(GBP_WR50_ELITE),
  "gbp_wr50_tight": deepcopy(GBP_WR50_TIGHT),
  "gbp_wr50_short_1td": deepcopy(GBP_WR50_SHORT_1TD),
  "gbp_wr50_short_london": deepcopy(GBP_WR50_SHORT_LONDON),
  "gbp_wr50_london_1td": deepcopy(GBP_WR50_LONDON_1TD),
  "eur_wr55_surg": deepcopy(EUR_WR55_SURG),
  "eur_wr55_london": deepcopy(EUR_WR55_LONDON),
  "eur_wr55_sniper": deepcopy(EUR_WR55_SNIPER),
  "eur_wr55_1td": deepcopy(EUR_WR55_1TD),
  "eur_wr55_2td": deepcopy(EUR_WR55_2TD),
  "eur_wr55_3td": deepcopy(EUR_WR55_3TD),
  "eur_wr55_flow": deepcopy(EUR_WR55_FLOW),
  "eur_wr55_rr3": deepcopy(EUR_WR55_RR3),
  "eur_wr55_short": deepcopy(EUR_WR55_SHORT),
  "eur_wr55_long": deepcopy(EUR_WR55_LONG),
  "eur_wr55_1td_long": deepcopy(EUR_WR55_1TD_LONG),
  "eur_wr55_qty": deepcopy(EUR_WR55_QTY),
  "eur_r100_core": deepcopy(EUR_R100_CORE),
  "eur_r100_elite": deepcopy(EUR_R100_ELITE),
  "eur_r100_elite_rr3": deepcopy(EUR_R100_ELITE_RR3),
  "eur_r100_london": deepcopy(EUR_R100_LONDON),
  "eur_r100_dense": deepcopy(EUR_R100_DENSE),
  "eur_r100_trend": deepcopy(EUR_R100_TREND),
  "eur_r100_wide": deepcopy(EUR_R100_WIDE),
  "eur_r100_hyper": deepcopy(EUR_R100_HYPER),
  "eur_r100_hyper_elite": deepcopy(EUR_R100_HYPER_ELITE),
}


def list_presets() -> list[str]:
  return list(PRESETS.keys())


def get_preset(name: str) -> dict:
  if name not in PRESETS:
    raise KeyError(f"Unknown mining preset `{name}`. Known: {list_presets()}")
  return deepcopy(PRESETS[name])
