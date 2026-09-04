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

# EUR Bid/Ask fill: SL = ATR×mult + 1 spread, BUY at Ask. Elite RR 3.2–4.0
# put TP too far (densify WR peaked ~33%). Wider SL + closer TP vs old elites.
EUR_FILL_WIDE = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [2.0, 2.4, 2.8],
  "atr_multipliers": [1.15, 1.35],
  "anti_chase_fixed_rsi": 60.0,
  "anti_chase_fixed_vwap": 1.8,
  "target_trades_per_week": 4.5,
  "drawdown_penalty": 0.6,
  "loss_streak_penalty": 1.2,
}
EUR_FILL_BOOK = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [2.2, 2.6, 3.0],
  "atr_multipliers": [1.05, 1.25],
  "anti_chase_fixed_rsi": 60.0,
  "anti_chase_fixed_vwap": 1.8,
  "target_trades_per_week": 5.0,
  "drawdown_penalty": 0.6,
  "loss_streak_penalty": 1.2,
}
EUR_FILL_WR = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [2.0, 2.4, 2.6],
  "atr_multipliers": [1.10, 1.30],
  "score_thresholds": [1.0, 1.6, 2.2],
  "min_rules_matches": [2],
  "ml_probability_thresholds": [0.40, 0.44, 0.48],
  "anti_chase_fixed_rsi": 58.0,
  "anti_chase_fixed_vwap": 1.5,
  "target_trades_per_week": 3.5,
  "drawdown_penalty": 0.8,
  "loss_streak_penalty": 1.5,
}
EUR_FILL_FLOW = {
  **EDGE_GENTLE,
  "rr_ratios": [2.0, 2.4, 2.8],
  "atr_multipliers": [1.15, 1.35],
  "anti_chase": True,
  "anti_chase_mode": "fixed",
  "anti_chase_fixed_rsi": 65.0,
  "anti_chase_use_vwap": False,
  "exit_modes_full_only": True,
  "target_trades_per_week": 6.0,
  "drawdown_penalty": 0.8,
  "loss_streak_penalty": 1.5,
}

# Refine around filladapt winner (eur_fill_book WR38/+43R n=108): lift WR
# without sniper n-collapse. Do not widen SL further (eur_fill_wide lost).
EUR_FILL_SURG = {
  **EUR_FILL_BOOK,
  "edge_surgery": True,
  "edge_surgery_hours": True,
  "edge_surgery_min_hour_trades": 4,
  "edge_surgery_max_hour_wr": 0.36,
  "edge_surgery_dominant_side_ratio": 0.62,
}
EUR_FILL_RSI = {
  **EUR_FILL_BOOK,
  "anti_chase_fixed_rsi": 58.0,
  "anti_chase_fixed_vwap": 1.5,
}
EUR_FILL_CORE = {
  **EUR_FILL_BOOK,
  "rr_ratios": [2.4, 2.6, 2.8],
  "atr_multipliers": [1.00, 1.15],
}
EUR_FILL_SHORT = {
  **EUR_FILL_BOOK,
  "force_side": "short",
  "target_trades_per_week": 4.5,
}

# Fill geometry: SL keeps +1 spread (live Ask/Bid), TP no longer × that buffer.
# Book DNA already won RR/ATR search; this is the unused tax on the target.
EUR_FILL_GEOM = {
  **EUR_FILL_BOOK,
  "tp_ignores_spread_buffer": True,
}
EUR_FILL_REACH = {
  **EUR_FILL_GEOM,
  "rr_ratios": [2.6, 3.0, 3.4],
}
EUR_FILL_BANK = {
  **EUR_FILL_GEOM,
  "exit_modes_full_only": False,
  "exit_mode_lock": "hybrid",
  "trail_activate_r": 1.5,
  "trail_distance_r": 0.5,
}
EUR_FILL_VOL = {
  **EUR_FILL_GEOM,
  "min_atr_spread_ratio": 5.0,
}

# Surprise: learn follow-through (label 1.2R) + pending stop confirm. Not another RR grid.
EUR_FILL_SPARK = {
  **EUR_FILL_BOOK,
  "label_rr": 1.2,
  "include_session_regime_rules": True,
}
EUR_FILL_STOP = {
  **EUR_FILL_BOOK,
  "confirm_r": 0.20,
  "confirm_wait_bars": 4,
  "confirm_cancel_r": 0.50,
}
EUR_FILL_SPARKSTOP = {
  **EUR_FILL_STOP,
  "label_rr": 1.2,
  "include_session_regime_rules": True,
}
EUR_FILL_OVERLAP = {
  **EUR_FILL_BOOK,
  "session_ranges": [[13, 16]],
  "label_rr": 1.2,
  "include_session_regime_rules": True,
}

# Densify sparkstop (WR50 +38R n=44): more fills for R, keep confirm quality.
EUR_FILL_SS_MORE = {
  **EUR_FILL_SPARKSTOP,
  "confirm_r": 0.15,
  "confirm_wait_bars": 6,
  "confirm_cancel_r": 0.60,
  "target_trades_per_week": 6.0,
}
EUR_FILL_SS_WAIT = {
  **EUR_FILL_SPARKSTOP,
  "confirm_r": 0.18,
  "confirm_wait_bars": 8,
  "confirm_cancel_r": 0.55,
}
EUR_FILL_SS_LAB = {
  **EUR_FILL_SPARKSTOP,
  "label_rr": 1.0,
  "confirm_r": 0.16,
  "confirm_wait_bars": 5,
  "target_trades_per_week": 5.5,
}
EUR_FILL_SS_WR = {
  **EUR_FILL_SPARKSTOP,
  "confirm_r": 0.24,
  "confirm_wait_bars": 3,
  "confirm_cancel_r": 0.42,
  "target_trades_per_week": 4.0,
}
# WR-hold R↑: same confirm as ss_more (0.15/6). Do not loosen fill — that dropped WR 56→53.5.
EUR_FILL_SS_PLUS = {
  **EUR_FILL_SS_MORE,
  "min_bars_between": [8],
  "max_hold_bars": [128],
  "target_trades_per_week": 7.5,
}
EUR_FILL_SS_RUN = {
  **EUR_FILL_SS_MORE,
  "rr_ratios": [2.6, 3.0, 3.4],
  "max_hold_bars": [128],
  "target_trades_per_week": 6.5,
}
EUR_FILL_SS_LAB_PLUS = {
  **EUR_FILL_SS_LAB,
  "min_bars_between": [8],
  "max_hold_bars": [128],
  "target_trades_per_week": 7.0,
}
# Late trail AFTER mine (same entries as ss_more). Activate near genome TP
# so giveback/timeout convert to wins without remine. 6m OOS 2026-h1:
# WR 51.9→56.4, R +49.5→+56.5 vs full TP.
EUR_FILL_SS_MORE_HYB24 = {
  **EUR_FILL_SS_MORE,
  "oos_exit_mode": "hybrid",
  "oos_trail_activate_r": 2.4,
  "oos_trail_distance_r": 0.40,
}
# Hold longer only — same confirm as ss_more (timeout winners may reach TP).
EUR_FILL_SS_MORE_HOLD = {
  **EUR_FILL_SS_MORE,
  "max_hold_bars": [128],
}
# Later / wider trail than hyb24 — less clip winner, still catch giveback.
EUR_FILL_SS_MORE_HYB28 = {
  **EUR_FILL_SS_MORE,
  "oos_exit_mode": "hybrid",
  "oos_trail_activate_r": 2.8,
  "oos_trail_distance_r": 0.55,
}
EUR_FILL_SS_BANK = {
  **EUR_FILL_SS_MORE,
  "exit_modes_full_only": False,
  "exit_mode_lock": "hybrid",
  "trail_activate_r": 1.3,
  "trail_distance_r": 0.45,
}
# Closer TP (ATR×RR, SL still +spread) so more 2.2–3.0R hits on Bid/Ask.
EUR_FILL_SS_CLIP = {
  **EUR_FILL_SS_MORE,
  "tp_ignores_spread_buffer": True,
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

# GBP Bid/Ask: fill_book on 4–6w printed WR15–29, n=17–26, R<0 (gs_20260902_095825).
# Same EUR lesson — not more RR. Label easier + stop confirm; SL must clear 2.3 spread.
GBP_FILL_SPARKSTOP = {
  **GBP_FILL_BOOK,
  "rr_ratios": [2.2, 2.6, 3.0],
  "atr_multipliers": [1.05, 1.25],
  "label_rr": 1.2,
  "confirm_r": 0.20,
  "confirm_wait_bars": 4,
  "confirm_cancel_r": 0.50,
  "include_session_regime_rules": True,
  "target_trades_per_week": 5.5,
}
GBP_FILL_SS_LAB = {
  **GBP_FILL_SPARKSTOP,
  "label_rr": 1.0,
  "confirm_r": 0.16,
  "confirm_wait_bars": 5,
  "target_trades_per_week": 6.0,
}
GBP_FILL_SS_MORE = {
  **GBP_FILL_SPARKSTOP,
  "confirm_r": 0.15,
  "confirm_wait_bars": 6,
  "confirm_cancel_r": 0.60,
  "target_trades_per_week": 6.5,
}
# ss_more 8w ep2: WR56 +16R PF3 n=16 — quality needs n≥40. Loosen fill rate, keep confirm.
GBP_FILL_SS_VOL = {
  **GBP_FILL_SS_MORE,
  "label_rr": 1.0,
  "confirm_r": 0.12,
  "confirm_wait_bars": 8,
  "confirm_cancel_r": 0.70,
  "min_bars_between": [8],
  "target_trades_per_week": 8.0,
}
GBP_FILL_SS_WAIT = {
  **GBP_FILL_SS_MORE,
  "label_rr": 1.0,
  "confirm_r": 0.14,
  "confirm_wait_bars": 8,
  "confirm_cancel_r": 0.65,
  "min_bars_between": [8],
  "target_trades_per_week": 7.5,
}
# Around ss_vol 6w h2 ep1 WR50 +36.8R n=42: slightly tighter confirm, hunt WR>50 with n still ≥40.
GBP_FILL_SS_TIGHT = {
  **GBP_FILL_SS_VOL,
  "confirm_r": 0.13,
  "confirm_wait_bars": 6,
  "confirm_cancel_r": 0.58,
  "min_bars_between": [8],
  "target_trades_per_week": 7.0,
}
GBP_FILL_SS_TIGHT_HYB24 = {
  **GBP_FILL_SS_TIGHT,
  "oos_exit_mode": "hybrid",
  "oos_trail_activate_r": 2.4,
  "oos_trail_distance_r": 0.40,
}
# Keep ss_tight confirm (WR55 +40.6R n=38). Gap/hold only — denser n on 2026.
GBP_FILL_SS_TIGHT_N = {
  **GBP_FILL_SS_TIGHT,
  "min_bars_between": [6],
  "max_hold_bars": [128],
  "target_trades_per_week": 8.5,
}
# Looser than ss_vol — more fills / a second DNA if n is the bottleneck on 2024 eras.
GBP_FILL_SS_DENSE = {
  **GBP_FILL_SS_VOL,
  "confirm_r": 0.10,
  "confirm_wait_bars": 10,
  "confirm_cancel_r": 0.78,
  "min_bars_between": [6],
  "target_trades_per_week": 9.0,
}
# WR-hold R↑: same confirm as ss_vol (0.12/8). Gap/hold only — do not loosen confirm.
GBP_FILL_SS_PLUS = {
  **GBP_FILL_SS_VOL,
  "min_bars_between": [6],
  "max_hold_bars": [128],
  "target_trades_per_week": 9.0,
}
GBP_FILL_SS_RUN = {
  **GBP_FILL_SS_VOL,
  "rr_ratios": [2.6, 3.0, 3.4],
  "max_hold_bars": [128],
  "target_trades_per_week": 8.0,
}
GBP_FILL_SS_BANK = {
  **GBP_FILL_SS_VOL,
  "exit_modes_full_only": False,
  "exit_mode_lock": "hybrid",
  "trail_activate_r": 1.3,
  "trail_distance_r": 0.45,
}
GBP_FILL_SS_CLIP = {
  **GBP_FILL_SS_VOL,
  "tp_ignores_spread_buffer": True,
}

# App-recommended direction after Bid/Ask fills (BUY Ask / SELL Bid).
# Elite OR-quality (RR 3.2–4) was fit on half-spread lab fills — do not
# re-offer it as the EUR default.
RECOMMENDED_PRESET = "eur_fill_ss_lab"

# EUR Settings: ss_more = Reset/chạy lại 6m; lab/sparkstop vẫn trong catalog.
EUR_FILL_CURATED: tuple[str, ...] = (
  "eur_fill_ss_more",
  "eur_fill_ss_lab",
  "eur_fill_sparkstop",
)

# GBP Settings: tight = Reset/chạy lại 6m; lab/vol vẫn trong catalog.
GBP_FILL_CURATED: tuple[str, ...] = (
  "gbp_fill_ss_tight",
  "gbp_fill_ss_lab",
  "gbp_fill_ss_vol",
)

# Default Settings UI list (no desk / EUR).
CURATED_PRESETS: tuple[str, ...] = EUR_FILL_CURATED

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
  # Failed n/WR A/Bs after Bid/Ask + sparkstop (keep in PRESETS for old TMs).
  "eur_fill_ss_lab_plus",
  "eur_fill_ss_plus",
  "eur_fill_ss_run",
  "eur_fill_ss_bank",
  "eur_fill_ss_more_hyb24",
  "eur_fill_ss_more_hold",
  "eur_fill_ss_more_hyb28",
  "eur_fill_ss_clip",
  "eur_fill_ss_wr",
  "eur_fill_book",
  "gbp_fill_ss_more",
  "gbp_fill_ss_plus",
  "gbp_fill_ss_run",
  "gbp_fill_ss_bank",
  "gbp_fill_ss_clip",
  "gbp_fill_ss_tight_hyb24",
  "gbp_fill_ss_tight_n",
  "gbp_fill_ss_dense",
  "gbp_fill_ss_wait",
  "gbp_fill_sparkstop",
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
  "elite_or_quality": "Elite OR-quality (fill cũ — không dùng EUR Bid/Ask)",
  "elite_60_35": "Elite RSI60 · RR3.5",
  "eur_fill_wide": "EUR fill · SL rộng TP gần",
  "eur_fill_book": "EUR fill-aware · RR 2.2–3",
  "eur_fill_wr": "EUR fill WR-first",
  "eur_fill_flow": "EUR fill flow · volume",
  "eur_fill_surg": "EUR fill · cắt giờ độc",
  "eur_fill_rsi": "EUR fill · RSI58 VWAP1.5",
  "eur_fill_core": "EUR fill · ATR 1.0–1.15",
  "eur_fill_short": "EUR fill · SHORT only",
  "eur_fill_geom": "EUR fill · TP không nhân spread",
  "eur_fill_reach": "EUR fill · TP ATR×RR 2.6–3.4",
  "eur_fill_bank": "EUR fill · hybrid bank 1.5R",
  "eur_fill_vol": "EUR fill · ATR≥5×spread",
  "eur_fill_spark": "EUR fill · label 1.2R + session",
  "eur_fill_stop": "EUR fill · stop confirm 0.2R",
  "eur_fill_sparkstop": "EUR fill · label 1.2R + stop",
  "eur_fill_overlap": "EUR fill · overlap 13–16",
  "eur_fill_ss_more": "EUR sparkstop · confirm 0.15 wait6",
  "eur_fill_ss_plus": "EUR ss_more · gap 8 + hold 128 (R↑ giữ WR)",
  "eur_fill_ss_run": "EUR ss_more · RR 2.6–3.4 hold 128",
  "eur_fill_ss_bank": "EUR ss_more · hybrid bank 1.3R (R↑ giữ WR)",
  "eur_fill_ss_more_hyb24": "EUR ss_more · trail muộn 2.4R (cùng entry)",
  "eur_fill_ss_clip": "EUR ss_more · TP ATR×RR (không nhân spread)",
  "eur_fill_ss_lab": "EUR Bid/Ask · label 1.0R + stop (khuyến nghị)",
  "eur_fill_ss_lab_plus": "EUR ss_lab · gap 8 + hold 128 (R↑ giữ WR)",
  "eur_fill_ss_wr": "EUR sparkstop · confirm 0.24",
  "gbp_fill_book": "GBP fill-aware · WR>50 R>80",
  "gbp_fill_sparkstop": "GBP Bid/Ask · label 1.2R + stop",
  "gbp_fill_ss_lab": "GBP Bid/Ask · label 1.0R + stop (khuyến nghị)",
  "gbp_fill_ss_more": "GBP sparkstop · confirm 0.15 wait6",
  "gbp_fill_ss_vol": "GBP sparkstop · nới confirm + 8 lệnh/tuần",
  "gbp_fill_ss_plus": "GBP ss_vol · gap 6 + hold 128 (R↑ giữ WR)",
  "gbp_fill_ss_run": "GBP ss_vol · RR 2.6–3.4 hold 128",
  "gbp_fill_ss_bank": "GBP ss_vol · hybrid bank 1.3R (R↑ giữ WR)",
  "gbp_fill_ss_clip": "GBP ss_vol · TP ATR×RR (không nhân spread)",
  "gbp_fill_ss_tight": "GBP sparkstop · confirm 0.13 wait6 (săn WR)",
  "gbp_fill_ss_tight_hyb24": "GBP ss_tight · trail muộn 2.4R (cùng entry)",
  "gbp_fill_ss_tight_n": "GBP ss_tight · gap 6 + hold 128 (thêm n)",
  "gbp_fill_ss_dense": "GBP sparkstop · confirm 0.10 wait10 (thêm n)",
  "gbp_fill_ss_wait": "GBP sparkstop · wait 8 nến",
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
    "intent": "Lab fill cũ (nửa spread) — RR 3.2–4 sụp trên BUY Ask / SELL Bid",
    "knobs": "void RSI≥58 OR VWAP≥1.5 · RR 3.2–4 · exit full · elite_frontier",
    "tradeoff": "OOS lạc quan WR~62 · remine fill mới đỉnh ~WR33 — không khuyến nghị EUR",
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
  "eur_fill_wide": {
    "intent": "EUR sau fill Bid/Ask — nới SL, kéo TP gần",
    "knobs": "RR 2.0–2.8 · ATR 1.15/1.35 · RSI<60 OR VWAP<1.8 · exit full",
    "tradeoff": "WR↑ vs elite RR3.5+ trên fill thật · RR thấp hơn sách cũ",
  },
  "eur_fill_book": {
    "intent": "EUR fill-aware, cân WR và Total R",
    "knobs": "RR 2.2–3.0 · ATR 1.05/1.25 · RSI<60 OR VWAP<1.8 · TPW 5",
    "tradeoff": "TP gần hơn elite cũ · nhiều lệnh hơn sniper",
  },
  "eur_fill_wr": {
    "intent": "EUR fill-aware, ưu tiên WR",
    "knobs": "RR 2.0–2.6 · ATR 1.10/1.30 · ML/score siết · TPW 3.5",
    "tradeoff": "Ít lệnh hơn fill_book · WR cao hơn nếu filter OOS giống train",
  },
  "eur_fill_flow": {
    "intent": "EUR fill-aware, gom R bằng tần suất + surgery",
    "knobs": "edge_gentle + RR 2.0–2.8 · ATR 1.15/1.35 · RSI<65 · TPW 6",
    "tradeoff": "Nhiều lệnh hơn elite · WR có thể thấp hơn fill_wr",
  },
  "eur_fill_surg": {
    "intent": "Nâng WR trên sách fill_book — cắt giờ/side độc trên train",
    "knobs": "hour WR≤36% n≥4 · side 62% · RR 2.2–3.0 · ATR 1.05/1.25",
    "tradeoff": "Ít lệnh hơn fill_book · WR↑ nếu giờ độc OOS giống train",
  },
  "eur_fill_rsi": {
    "intent": "Siết chase trên geometry fill_book",
    "knobs": "RSI<58 OR VWAP<1.5 · giữ RR/ATR fill_book",
    "tradeoff": "WR↑ nếu chase là loser · n↓ vừa",
  },
  "eur_fill_core": {
    "intent": "SL vừa + RR giữa — tránh ATR 1.25 làm TP xa",
    "knobs": "RR 2.4–2.8 · ATR 1.00/1.15 · RSI<60 OR VWAP<1.8",
    "tradeoff": "TP gần hơn fill_book · SL hẹp hơn wide",
  },
  "eur_fill_short": {
    "intent": "EUR fill-aware SHORT-only — book OOS gần như hết short",
    "knobs": "force_side=short · RR 2.2–3.0 · ATR 1.05/1.25",
    "tradeoff": "Mất long · n có thể ↓ · WR/R↑ nếu long là nhiễu",
  },
  "eur_fill_geom": {
    "intent": "EUR Bid/Ask — TP không bị nhân buffer spread của SL",
    "knobs": "SL = ATR×mult+1 spread · TP = ATR×mult×RR · DNA fill_book",
    "tradeoff": "TP gần hơn book hiện tại · RR báo cáo có thể < RR danh nghĩa",
  },
  "eur_fill_reach": {
    "intent": "Geom + RR ATR 2.6–3.4 — khôi phục tầm TP cũ",
    "knobs": "tp_ignores_spread_buffer · RR 2.6/3.0/3.4 · ATR 1.05/1.25",
    "tradeoff": "Winner lớn hơn geom · WR có thể thấp hơn nếu TP lại xa",
  },
  "eur_fill_bank": {
    "intent": "Geom + hybrid — chốt khi đi được 1.5R rồi trail",
    "knobs": "exit hybrid 1.5/0.5 · TP ATR-only · DNA fill_book",
    "tradeoff": "WR↑ nếu loser có MFE · RR clip so với full TP",
  },
  "eur_fill_vol": {
    "intent": "Geom + bỏ nến ATR nhỏ so với spread",
    "knobs": "min ATR ≥ 5×spread · TP ATR-only · DNA fill_book",
    "tradeoff": "Ít lệnh Asia yên · WR↑ nếu spread chiếm SL",
  },
  "eur_fill_spark": {
    "intent": "Học follow-through 1.2R, vào vẫn RR book — rules giàu hơn trên fill",
    "knobs": "label_rr=1.2 · session/regime binaries · DNA fill_book",
    "tradeoff": "Nhiều label dương · có thể bắn setup yếu hơn full TP",
  },
  "eur_fill_stop": {
    "intent": "BUY/SELL stop: chỉ fill khi giá xác nhận 0.2R, hủy nếu chết 0.5R",
    "knobs": "confirm 0.2R · wait 4 nến · cancel 0.5R · DNA fill_book",
    "tradeoff": "Bỏ giả / lệnh không chạy · n↓ · miss winner không pullback",
  },
  "eur_fill_sparkstop": {
    "intent": "Label 1.2R + stop confirm — chọn hướng rồi đợi xác nhận",
    "knobs": "label_rr=1.2 · confirm 0.2R · session/regime",
    "tradeoff": "Ít lệnh hơn spark · WR↑ nếu fake là loser",
  },
  "eur_fill_overlap": {
    "intent": "Chỉ overlap London/NY 13–16 + label 1.2R",
    "knobs": "session 13–16 · label_rr=1.2 · regime binaries",
    "tradeoff": "Bỏ Asia/London open · n thấp",
  },
  "eur_fill_ss_more": {
    "intent": "Nới confirm — thêm lệnh quanh sparkstop WR50",
    "knobs": "confirm 0.15 · wait 6 · cancel 0.60 · TPW 6 · label 1.2",
    "tradeoff": "n↑ Total R↑ · WR có thể thấp hơn 50",
  },
  "eur_fill_ss_plus": {
    "intent": "Giữ confirm ss_more — thêm lệnh + hold lâu hơn, không nới fill",
    "knobs": "confirm 0.15 wait6 · gap 8 · hold 128 · TPW 7.5 · RR 2.2–3.0",
    "tradeoff": "n↑ R↑ nếu lệnh thêm cùng chất · WR tụt nếu gap 8 kéo setup yếu",
  },
  "eur_fill_ss_run": {
    "intent": "Giữ confirm ss_more — TP xa hơn, winner chạy hết",
    "knobs": "confirm 0.15 wait6 · RR 2.6–3.4 · hold 128",
    "tradeoff": "R/lệnh↑ · WR có thể tụt nếu TP 3.4 quá xa trên Bid/Ask",
  },
  "eur_fill_ss_bank": {
    "intent": "R>80 WR>50 — chốt 1.3R rồi trail, không nới confirm",
    "knobs": "confirm 0.15 wait6 · hybrid 1.3/0.45",
    "tradeoff": "WR↑ nếu timeout là giveback · R/lệnh có thể thấp hơn full TP",
  },
  "eur_fill_ss_more_hyb24": {
    "intent": "Cùng entry ss_more — trail muộn 2.4R sau khi mine full TP",
    "knobs": "confirm 0.15 wait6 · OOS hybrid 2.4/0.40 · miner vẫn exit:full",
    "tradeoff": "WR↑ khi giveback thành trail win · R/win có thể thấp hơn TP đầy",
  },
  "eur_fill_ss_clip": {
    "intent": "R>80 WR>50 — TP = ATR×RR, SL vẫn +1 spread",
    "knobs": "confirm 0.15 wait6 · TP:ATRxRR",
    "tradeoff": "Nhiều TP hơn · R/win nhỏ hơn book đã +spread vào TP",
  },
  "eur_fill_ss_lab_plus": {
    "intent": "Giữ confirm ss_lab WR56 — thêm n và hold để nâng R",
    "knobs": "confirm 0.16 wait5 · gap 8 · hold 128 · TPW 7",
    "tradeoff": "n↑ quanh DNA WR56 · WR tụt nếu gap 8 kéo setup yếu",
  },
  "eur_fill_ss_wait": {
    "intent": "Chờ confirm lâu hơn — bắt lệnh chậm",
    "knobs": "confirm 0.18 · wait 8 nến · cancel 0.55",
    "tradeoff": "n↑ nếu confirm trễ · giữ WR nếu fake chết sớm",
  },
  "eur_fill_ss_lab": {
    "intent": "EUR Bid/Ask — hướng khuyến nghị: label 1.0R + stop confirm",
    "knobs": "label_rr=1.0 · confirm 0.16 · wait 5 · RR 2.2–3.0 · ATR 1.05/1.25",
    "tradeoff": "Lab fill mới WR56 +43R n=41 · confirm là pending (chưa market nến sau)",
  },
  "eur_fill_ss_wr": {
    "intent": "Siết confirm — săn WR>50",
    "knobs": "confirm 0.24 · wait 3 · cancel 0.42 · TPW 4",
    "tradeoff": "n↓ · WR↑ · R có thể thấp hơn sparkstop",
  },
  "gbp_fill_book": {
    "intent": "GBP sau fill thật — WR>50 và Total R>80",
    "knobs": "RR 2.4–3.2 · ATR 0.85/1.05 · RSI<60 OR VWAP<1.8 · TPW 5 · exit full",
    "tradeoff": "TP gần hơn elite cũ (SL đã +spread) · nhiều lệnh hơn sniper",
  },
  "gbp_fill_sparkstop": {
    "intent": "GBP Bid/Ask — label 1.2R rồi đợi giá xác nhận, không market Ask nến tín hiệu",
    "knobs": "label_rr=1.2 · confirm 0.2R · wait 4 · RR 2.2–3.0 · ATR 1.05/1.25",
    "tradeoff": "Bỏ giả / lệnh không chạy · n↓ vs fill_book nếu confirm siết",
  },
  "gbp_fill_ss_lab": {
    "intent": "GBP Bid/Ask — hướng khuyến nghị: cùng DNA EUR ss_lab, SL đủ lớn hơn spread 2.3",
    "knobs": "label_rr=1.0 · confirm 0.16 · wait 5 · RR 2.2–3.0 · ATR 1.05/1.25 · TPW 6",
    "tradeoff": "Confirm là pending (chưa market nến sau) · n có thể mỏng trên OOS ngắn",
  },
  "gbp_fill_ss_more": {
    "intent": "Nới confirm — thêm lệnh quanh ss_lab khi n GBP quá mỏng",
    "knobs": "confirm 0.15 · wait 6 · cancel 0.60 · TPW 6.5 · label 1.2",
    "tradeoff": "n↑ · WR có thể thấp hơn ss_lab",
  },
  "gbp_fill_ss_vol": {
    "intent": "Đẩy n về cổng quality (≥40) từ ss_more WR56 n=16",
    "knobs": "label 1.0 · confirm 0.12 · wait 8 · cancel 0.70 · gap 8 nến · TPW 8",
    "tradeoff": "n↑ mạnh · WR có thể tụt dưới 50 nếu confirm quá lỏng",
  },
  "gbp_fill_ss_plus": {
    "intent": "Giữ confirm ss_vol WR50 — gap/hold để nâng R, không nới fill",
    "knobs": "confirm 0.12 wait8 · gap 6 · hold 128 · TPW 9",
    "tradeoff": "n↑ R↑ · WR tụt nếu gap 6 kéo setup yếu",
  },
  "gbp_fill_ss_run": {
    "intent": "Giữ confirm ss_vol WR50 — TP xa hơn",
    "knobs": "confirm 0.12 wait8 · RR 2.6–3.4 · hold 128",
    "tradeoff": "R/lệnh↑ · WR có thể tụt nếu TP 3.4 quá xa",
  },
  "gbp_fill_ss_bank": {
    "intent": "R>80 WR>50 — chốt 1.3R rồi trail trên DNA ss_vol",
    "knobs": "confirm 0.12 wait8 · hybrid 1.3/0.45",
    "tradeoff": "WR↑ nếu timeout giveback · R/lệnh có thể thấp hơn full TP",
  },
  "gbp_fill_ss_clip": {
    "intent": "R>80 WR>50 — TP ATR×RR trên DNA ss_vol",
    "knobs": "confirm 0.12 wait8 · TP:ATRxRR",
    "tradeoff": "Nhiều TP hơn · R/win nhỏ hơn nếu spread đã nằm trong TP",
  },
  "gbp_fill_ss_wait": {
    "intent": "Chờ confirm lâu hơn — bắt lệnh chậm, giữ WR ss_more",
    "knobs": "label 1.0 · confirm 0.14 · wait 8 · cancel 0.65 · gap 8 · TPW 7.5",
    "tradeoff": "n↑ nếu confirm trễ · miss nếu fake chết sớm",
  },
  "gbp_fill_ss_tight": {
    "intent": "Siết nhẹ ss_vol — săn WR>50 khi n đã đạt cổng 40",
    "knobs": "label 1.0 · confirm 0.13 · wait 6 · cancel 0.58 · gap 8 · TPW 7",
    "tradeoff": "n có thể tụt dưới 40 · WR↑ nếu fake chết trong 6 nến",
  },
  "gbp_fill_ss_tight_hyb24": {
    "intent": "Cùng entry ss_tight — trail muộn 2.4R sau khi mine full TP",
    "knobs": "confirm 0.13 wait6 · OOS hybrid 2.4/0.40 · miner vẫn exit:full",
    "tradeoff": "WR/R↑ nếu winner giveback · GBP 6m có thể không cộng R như EUR",
  },
  "gbp_fill_ss_tight_n": {
    "intent": "R>80 WR>50 — thêm n trên DNA ss_tight, không nới confirm",
    "knobs": "confirm 0.13 wait6 · gap 6 · hold 128 · TPW 8.5",
    "tradeoff": "n↑ · WR có thể tụt nếu lệnh chen sát nhau",
  },
  "gbp_fill_ss_dense": {
    "intent": "Nới hơn ss_vol — thêm DNA khi era 2024 n mỏng",
    "knobs": "label 1.0 · confirm 0.10 · wait 10 · cancel 0.78 · gap 6 · TPW 9",
    "tradeoff": "n↑ · WR có thể tụt dưới 50 nếu confirm quá lỏng",
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
}


def preset_label(name: str) -> str:
  label = PRESET_LABELS.get(name, name)
  if name in DEPRECATED_PRESETS:
    return f"{label} (deprecated)"
  return label


def preset_blurb(name: str) -> dict[str, str]:
  """Intent / knobs / tradeoff for a preset (empty dict if unknown)."""
  return dict(PRESET_BLURBS.get(name) or {})


def _desk_id() -> str:
  import os
  return (os.environ.get("TRAINAPP_DESK") or "").strip().lower()


def recommended_preset() -> str:
  """Desk-aware default mining direction (EUR Bid/Ask vs GBP fill)."""
  desk = _desk_id()
  if desk.startswith("g"):
    return "gbp_fill_ss_lab"
  return RECOMMENDED_PRESET


def recommended_presets() -> list[str]:
  return [recommended_preset()]


def list_curated_presets() -> list[str]:
  """Presets offered in Settings UI (excludes deprecated losers)."""
  desk = _desk_id()
  names = GBP_FILL_CURATED if desk.startswith("g") else EUR_FILL_CURATED
  return [n for n in names if n in PRESETS]


def list_active_presets() -> list[str]:
  """All non-deprecated presets (CLI / advanced)."""
  return [n for n in PRESETS if n not in DEPRECATED_PRESETS]


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
  if ss.get("tp_ignores_spread_buffer"):
    bits.append("TP:ATRxRR")
  if float(ss.get("min_atr_spread_ratio") or 0) > 0:
    bits.append(f"ATRmin×{ss.get('min_atr_spread_ratio')}")
  lock = str(ss.get("exit_mode_lock") or "")
  if lock:
    bits.append(f"exit:{lock}")
  elif ss.get("exit_modes_full_only"):
    bits.append("exit:full")
  oos_ex = str(ss.get("oos_exit_mode") or "").strip()
  if oos_ex:
    act = ss.get("oos_trail_activate_r")
    bits.append(f"oos:{oos_ex}{act if act else ''}")
  if float(ss.get("label_rr") or 0) > 0:
    bits.append(f"labelRR{ss.get('label_rr')}")
  if float(ss.get("confirm_r") or 0) > 0:
    bits.append(f"stop{ss.get('confirm_r')}R")
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
  "eur_fill_wide": deepcopy(EUR_FILL_WIDE),
  "eur_fill_book": deepcopy(EUR_FILL_BOOK),
  "eur_fill_wr": deepcopy(EUR_FILL_WR),
  "eur_fill_flow": deepcopy(EUR_FILL_FLOW),
  "eur_fill_surg": deepcopy(EUR_FILL_SURG),
  "eur_fill_rsi": deepcopy(EUR_FILL_RSI),
  "eur_fill_core": deepcopy(EUR_FILL_CORE),
  "eur_fill_short": deepcopy(EUR_FILL_SHORT),
  "eur_fill_geom": deepcopy(EUR_FILL_GEOM),
  "eur_fill_reach": deepcopy(EUR_FILL_REACH),
  "eur_fill_bank": deepcopy(EUR_FILL_BANK),
  "eur_fill_vol": deepcopy(EUR_FILL_VOL),
  "eur_fill_spark": deepcopy(EUR_FILL_SPARK),
  "eur_fill_stop": deepcopy(EUR_FILL_STOP),
  "eur_fill_sparkstop": deepcopy(EUR_FILL_SPARKSTOP),
  "eur_fill_overlap": deepcopy(EUR_FILL_OVERLAP),
  "eur_fill_ss_more": deepcopy(EUR_FILL_SS_MORE),
  "eur_fill_ss_plus": deepcopy(EUR_FILL_SS_PLUS),
  "eur_fill_ss_run": deepcopy(EUR_FILL_SS_RUN),
  "eur_fill_ss_wait": deepcopy(EUR_FILL_SS_WAIT),
  "eur_fill_ss_lab": deepcopy(EUR_FILL_SS_LAB),
  "eur_fill_ss_lab_plus": deepcopy(EUR_FILL_SS_LAB_PLUS),
  "eur_fill_ss_bank": deepcopy(EUR_FILL_SS_BANK),
  "eur_fill_ss_more_hyb24": deepcopy(EUR_FILL_SS_MORE_HYB24),
  "eur_fill_ss_more_hold": deepcopy(EUR_FILL_SS_MORE_HOLD),
  "eur_fill_ss_more_hyb28": deepcopy(EUR_FILL_SS_MORE_HYB28),
  "eur_fill_ss_clip": deepcopy(EUR_FILL_SS_CLIP),
  "eur_fill_ss_wr": deepcopy(EUR_FILL_SS_WR),
  "gbp_fill_book": deepcopy(GBP_FILL_BOOK),
  "gbp_fill_sparkstop": deepcopy(GBP_FILL_SPARKSTOP),
  "gbp_fill_ss_lab": deepcopy(GBP_FILL_SS_LAB),
  "gbp_fill_ss_more": deepcopy(GBP_FILL_SS_MORE),
  "gbp_fill_ss_vol": deepcopy(GBP_FILL_SS_VOL),
  "gbp_fill_ss_plus": deepcopy(GBP_FILL_SS_PLUS),
  "gbp_fill_ss_run": deepcopy(GBP_FILL_SS_RUN),
  "gbp_fill_ss_bank": deepcopy(GBP_FILL_SS_BANK),
  "gbp_fill_ss_clip": deepcopy(GBP_FILL_SS_CLIP),
  "gbp_fill_ss_tight": deepcopy(GBP_FILL_SS_TIGHT),
  "gbp_fill_ss_tight_hyb24": deepcopy(GBP_FILL_SS_TIGHT_HYB24),
  "gbp_fill_ss_tight_n": deepcopy(GBP_FILL_SS_TIGHT_N),
  "gbp_fill_ss_dense": deepcopy(GBP_FILL_SS_DENSE),
  "gbp_fill_ss_wait": deepcopy(GBP_FILL_SS_WAIT),
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
}


def list_presets() -> list[str]:
  return list(PRESETS.keys())


def get_preset(name: str) -> dict:
  if name not in PRESETS:
    raise KeyError(f"Unknown mining preset `{name}`. Known: {list_presets()}")
  return deepcopy(PRESETS[name])
