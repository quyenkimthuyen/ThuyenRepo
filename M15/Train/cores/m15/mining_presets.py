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

# App-recommended direction (WR-first quality book; used by Settings default).
RECOMMENDED_PRESET = "elite_or_quality"

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
  "elite_or_quality": "Elite OR-quality (khuyến nghị)",
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
    "intent": "Ưu tiên WR/DD — hướng khuyến nghị app",
    "knobs": "void RSI≥58 OR VWAP≥1.5 · RR 3.2–4 · exit full · elite_frontier",
    "tradeoff": "WR/DD tốt · ít lệnh (~2/tuần) · Total R thấp hơn baseline",
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
}


def preset_label(name: str) -> str:
  label = PRESET_LABELS.get(name, name)
  if name in DEPRECATED_PRESETS:
    return f"{label} (deprecated)"
  return label


def preset_blurb(name: str) -> dict[str, str]:
  """Intent / knobs / tradeoff for a preset (empty dict if unknown)."""
  return dict(PRESET_BLURBS.get(name) or {})


def recommended_presets() -> list[str]:
  return [RECOMMENDED_PRESET]


def list_curated_presets() -> list[str]:
  """Presets offered in Settings UI (excludes deprecated losers)."""
  return [n for n in CURATED_PRESETS if n in PRESETS]


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
}


def list_presets() -> list[str]:
  return list(PRESETS.keys())


def get_preset(name: str) -> dict:
  if name not in PRESETS:
    raise KeyError(f"Unknown mining preset `{name}`. Known: {list_presets()}")
  return deepcopy(PRESETS[name])
