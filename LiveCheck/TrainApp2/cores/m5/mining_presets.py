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
  "min_bars_between": [24],
  "max_hold_bars": [192],
  "session_ranges": [[8, 17]],
  "score_thresholds": [1.0, 1.6, 2.2],
  "min_rules_matches": [2],
  "ml_probability_thresholds": [0.40, 0.44, 0.48],
  "target_trades_per_week": 20.0,
  "drawdown_penalty": 1.5,
  "loss_streak_penalty": 2.0,
}

WR_RR_FRONTIER = {
  **WR_RR_SNIPER,
  "selection_mode": "expectancy_frontier",
}

WR_RR_LOCK = {
  **WR_RR_FRONTIER,
  "max_hold_bars": [144, 192],
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
  "target_trades_per_week": 22.0,
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
  "target_trades_per_week": 17.0,
}

# Stricter quality: allow lower frequency for higher WR.
ANTI_CHASE_STRICT = {
  **ANTI_CHASE,
  "anti_chase_rsi_caps": [55.0, 58.0, 60.0, 62.0, 65.0],
  "anti_chase_min_tpw": 4.0,
  "target_trades_per_week": 14.0,
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
  "target_trades_per_week": 17.0,
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
  "target_trades_per_week": 20.0,
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

# Challenge: WR>60% × RR>3 (accept lower Total R) — same sniper density as M15.
# Wall-clock parity: 36×M5 ≈ 12×M15 (3h spacing); 288×M5 ≈ 96×M15 (24h hold).
ELITE_60_3 = {
  **BASELINE_SPACE,
  "rr_ratios": [3.5, 4.0],
  "selection_mode": "elite_frontier",
  "exit_modes_full_only": True,
  "anti_chase": True,
  "anti_chase_mode": "fixed",
  "anti_chase_fixed_rsi": 58.0,
  "anti_chase_use_vwap": False,
  "max_hold_bars": [288],
  "min_bars_between": [36],
  "max_trades_per_day": 2,
  "target_trades_per_week": 3.0,
  "anti_chase_min_tpw": 3.0,
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

# Round-2 WR push: drop weak admits (score 0.6 / ML 0.36 / 1-rule) that
# kept E31 at 56% WR. Tighter void + RR 3.5–4 + hour surgery.
ELITE_WR60 = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [3.5, 4.0],
  "score_thresholds": [1.0, 1.6, 2.2],
  "min_rules_matches": [2],
  "ml_probability_thresholds": [0.40, 0.44, 0.48],
  "anti_chase_fixed_rsi": 55.0,
  "anti_chase_fixed_vwap": 1.2,
  "anti_chase_logic": "or",
  "target_trades_per_week": 2.5,
  "anti_chase_min_tpw": 2.0,
  "edge_surgery": True,
  "edge_surgery_hours": True,
}

# Same + London–NY overlap only (helps GBP more than Asia hours).
ELITE_WR60_LDN = {
  **ELITE_WR60,
  "session_ranges": [[8, 17]],
}

# GBP M5: wr60 stacked too many gates (n=4–8). Keep OR-quality admits,
# add London session + hour surgery only.
ELITE_GBP_LDN = {
  **ELITE_OR_QUALITY,
  "session_ranges": [[8, 17]],
  "edge_surgery": True,
  "edge_surgery_hours": True,
}

# Round-1 G33 winner family (elite_55_4) + London + hour surgery.
ELITE_GBP_RR4 = {
  **ELITE_55_4,
  "session_ranges": [[8, 17]],
  "edge_surgery": True,
  "edge_surgery_hours": True,
}

# M5 stretch: denser than elite_or but keep anti-chase + high RR (era5 sweet spot ~11 tpw).
ELITE_M5_BALANCED = {
  **ELITE_OR_QUALITY,
  "rr_ratios": [3.0, 3.5, 4.0],
  "anti_chase_fixed_rsi": 60.0,
  "anti_chase_fixed_vwap": 1.5,
  "min_bars_between": [16],
  "max_hold_bars": [192],
  "max_trades_per_day": 5,
  "target_trades_per_week": 16.0,
  "anti_chase_min_tpw": 8.0,
  "score_thresholds": [1.0, 1.6, 2.2],
  "min_rules_matches": [2],
}

# Conf-style: slightly looser RSI but still full+high RR.
ELITE_60_35 = {
  **ELITE_60_3,
  "rr_ratios": [3.5],
  "anti_chase_fixed_rsi": 60.0,
  "target_trades_per_week": 4.0,
}

# App-recommended direction (WR-first quality book; used by Settings default).
RECOMMENDED_PRESET = "elite_or_quality"

# Shown in Settings UI — trimmed 2026-08-10 (drop near-duplicate elite / frontier).
# Keep: default quality · R-balance · gentle edge · niche elite · baseline neo.
# See docs/mining_space_audit.md.
CURATED_PRESETS: tuple[str, ...] = (
  "elite_or_quality",
  "elite_m5_balanced",
  "anti_chase_fixed_70",
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
  "elite_or_quality": "Elite OR-quality · M15 parity WR",
  "elite_wr60": "Elite WR60 · siết admit",
  "elite_wr60_ldn": "Elite WR60 · phiên London",
  "elite_gbp_ldn": "Elite GBP · London OR-quality",
  "elite_gbp_rr4": "Elite GBP · London RR4",
  "elite_m5_balanced": "Elite M5 balanced (R↑ giữ DD)",
  "elite_60_35": "Elite RSI60 · RR3.5",
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
    "intent": "Ưu tiên WR/DD kiểu M15 — hướng khuyến nghị app",
    "knobs": "void RSI≥58 OR VWAP≥1.5 · RR 3.2–4 · TPW 3.5 · giãn 3h · max 2/ngày · exit full",
    "tradeoff": "WR/DD tốt · ít lệnh (~2/tuần) · Total R thấp hơn baseline dày",
  },
  "elite_wr60": {
    "intent": "Đẩy WR lên 60%+ sau khi đã có sách thưa M15-parity",
    "knobs": "score≥1.0 · ML≥0.40 · 2 rules · RSI≥55 OR VWAP≥1.2 · RR 3.5–4 · edge_surgery",
    "tradeoff": "WR cao hơn elite_or · ít lệnh hơn (~1.5–2.5/tuần) · Total R thấp hơn",
  },
  "elite_wr60_ldn": {
    "intent": "WR60 + chỉ phiên 8–17h (cắt Asia)",
    "knobs": "giống elite_wr60 · session 8–17",
    "tradeoff": "Ít lệnh hơn nữa · có thể giúp GBP",
  },
  "elite_gbp_ldn": {
    "intent": "GBP M5: London-only, giữ admit OR-quality (không siết score/ML)",
    "knobs": "session 8–17 · void RSI≥58 OR VWAP≥1.5 · RR 3.2–4 · hour surgery",
    "tradeoff": "Cắt Asia · giữ đủ lệnh hơn wr60 · WR có thể tăng nhẹ vs elite_or",
  },
  "elite_gbp_rr4": {
    "intent": "GBP M5: họ elite_55_4 (best G33 vòng 1) + London + surgery",
    "knobs": "session 8–17 · RSI≥55 · RR 4.0 · hour surgery",
    "tradeoff": "Ít lệnh hơn OR-quality · RR cao hơn · WR hướng 45–50%",
  },
  "elite_m5_balanced": {
    "intent": "M5 stretch: gần BestBalance (~11–16 tpw) giữ anti-chase",
    "knobs": "void RSI≥60 OR VWAP≥1.5 · RR 3–4 · TPW 16 · exit full",
    "tradeoff": "R↑ hơn elite_or · DD vẫn thấp hơn baseline denser",
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
  "elite_or_quality": deepcopy(ELITE_OR_QUALITY),
  "elite_wr60": deepcopy(ELITE_WR60),
  "elite_wr60_ldn": deepcopy(ELITE_WR60_LDN),
  "elite_gbp_ldn": deepcopy(ELITE_GBP_LDN),
  "elite_gbp_rr4": deepcopy(ELITE_GBP_RR4),
  "elite_m5_balanced": deepcopy(ELITE_M5_BALANCED),
  "elite_60_35": deepcopy(ELITE_60_35),
}


def list_presets() -> list[str]:
  return list(PRESETS.keys())


def get_preset(name: str) -> dict:
  if name not in PRESETS:
    raise KeyError(f"Unknown mining preset `{name}`. Known: {list_presets()}")
  return deepcopy(PRESETS[name])
