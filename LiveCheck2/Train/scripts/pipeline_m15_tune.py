#!/usr/bin/env python3
"""Tinh chỉnh M15 densify v3 (e21/g23): winners + week12 + edge_gentle.

Grid fine trước (elite_or / elite_55_4 / elite_60_3 / elite_60_3_vwap · 3–9w · ep1–4):
  - e21: elite_60_3_vwap WR67/+111R active; elite_60_3 +116R top-R
  - g23: elite_60_3 +55R tốt hơn vwap; elite_55_4 gần như không vào top
  - Chưa quét week 12; edge_gentle (high-R đã chứng minh) bị bỏ khỏi lưới đó

Densify v3 (~144 combo):
  - weeks: [3, 4, 6, 8, 9, 12]  (thêm 12; giữ 3 vì g23 thắng ở 3w)
  - presets: elite_60_3, elite_60_3_vwap, elite_or_quality, edge_gentle
    (bỏ elite_55_4; thêm lại edge_gentle)
  - epochs 1..3 · eras full+h2

Promote dual:
  - Quality: WR>48 / RR>2.3 / R>40 / DD<9
  - High-R book: R>70 / WR>40 / DD<16 / n>=80
  Active = #1 quality nếu có, else #1 high-R.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from desk_context import apply_desk_env  # noqa: E402

FINE_WEEKS = [3, 4, 6, 8, 9, 12]
FINE_PRESETS = [
  "elite_60_3",
  "elite_60_3_vwap",
  "elite_or_quality",
  "edge_gentle",
]
FINE_EPOCHS = 3
FINE_OBJECTIVE = "quality"
FINE_ERA_KEYS = ["2025-full", "2025-h2"]

# g23 boost: GBP quality ceiling ~WR53/+55; densify wasted half grid on era-full
# (top36 all h2) and dropped ep4 (source of +55). Focus h2 + ep1–4 + week5.
G23_BOOST_WEEKS = [3, 4, 5, 6, 8, 9, 12]
G23_BOOST_PRESETS = [
  "elite_or_quality",
  "elite_60_3",
  "elite_60_3_vwap",
  "anti_chase_fixed_70",
  "elite_55_4",
  "edge_gentle",
]
G23_BOOST_EPOCHS = 4
G23_BOOST_ERA_KEYS = ["2025-h2"]  # 7×6×4×1 = 168 combo

# g23 explore: presets NGOÀI curated (chưa từng chạy trên g23).
# Bỏ elite_60_3/vwap (đã quét nhiều). Ưu tiên nhánh WR↑ + hybrid R.
G23_EXPLORE_WEEKS = [3, 4, 5, 6, 9, 12]
G23_EXPLORE_PRESETS = [
  "anti_chase",           # calibrate RSI — WR↑
  "anti_chase_strict",    # calibrate chặt hơn
  "anti_chase_fixed_62",  # void RSI≥62 cố định
  "anti_chase_fixed_65",
  "anti_chase_and_70_15", # AND void — giữ R
  "elite_60_35",          # elite lỏng hơn curated elite
  "nova",                 # anti_chase+VWAP+side surgery
  "nova_fixed",
]
G23_EXPLORE_EPOCHS = 4
G23_EXPLORE_ERA_KEYS = ["2025-h2"]  # 6×8×4×1 = 192 combo

# g23 refine: densify quanh winner explore (nova / anti_chase*).
# Thêm week 7–8; giữ h2 + ep1–4. Mục tiêu vượt nova +110 / WR47.
G23_REFINE_WEEKS = [3, 4, 6, 7, 8, 9, 12]
G23_REFINE_PRESETS = [
  "nova",
  "nova_fixed",
  "anti_chase",
  "anti_chase_strict",
  "anti_chase_fixed_62",
  "anti_chase_fixed_65",
]
G23_REFINE_EPOCHS = 4
G23_REFINE_ERA_KEYS = ["2025-h2"]  # 7×6×4×1 = 168 combo
# Promote bar raised vs explore — beat current nova active.
FILTER_Q_G23_REFINE = {"wr_gt": 47.0, "rr_gt": 2.25, "total_r_gt": 85.0, "max_dd_lt": 9.0}

# g23 fullera: winner presets trên era 2025-full (e21 active dùng full; g23 chỉ quét h2).
G23_FULLERA_WEEKS = [3, 4, 6, 9, 12]
G23_FULLERA_PRESETS = [
  "nova",
  "nova_fixed",
  "anti_chase",
  "anti_chase_strict",
  "anti_chase_fixed_62",
  "anti_chase_fixed_65",
]
G23_FULLERA_EPOCHS = 4
G23_FULLERA_ERA_KEYS = ["2025-full"]  # 5×6×4×1 = 120 combo

# target60: WR>60% + Total R>100 (user bar). Elite densify quanh winner e21; g23 thử elite chặt.
FILTER_TARGET60 = {"wr_gt": 60.0, "rr_gt": 2.20, "total_r_gt": 100.0, "max_dd_lt": 12.0}
E21_TARGET60_WEEKS = [6, 8, 9, 12]
E21_TARGET60_PRESETS = ["elite_60_3", "elite_60_3_vwap", "elite_or_quality"]
E21_TARGET60_EPOCHS = 4
E21_TARGET60_ERA_KEYS = ["2025-full"]  # 4×3×4×1 = 48 combo
G23_TARGET60_WEEKS = [3, 4, 5, 6, 8, 9, 12]
G23_TARGET60_PRESETS = [
  "elite_60_3",
  "elite_60_3_vwap",
  "elite_55_4",
  "elite_55_4_vwap",
  "elite_or_quality",
]
G23_TARGET60_EPOCHS = 4
G23_TARGET60_ERA_KEYS = ["2025-h2", "2025-full"]  # 7×5×4×2 = 280 → trunc 200

# g23 hybrid: elite void + side surgery — bridge gap elite WR~52 vs nova R~110.
G23_HYBRID_WEEKS = [3, 4, 5, 6, 8, 9, 12]
G23_HYBRID_PRESETS = [
  "elite_or_surgery",
  "elite_vwap_surgery",
  "elite_55_surgery",
  "nova_fixed",
  "elite_or_quality",
]
G23_HYBRID_EPOCHS = 4
G23_HYBRID_ERA_KEYS = ["2025-h2"]  # 7×5×4×1 = 140 combo
# Promote nếu cải thiện nova; log thêm target60 hits.
FILTER_Q_G23_HYBRID = {"wr_gt": 48.0, "rr_gt": 2.25, "total_r_gt": 70.0, "max_dd_lt": 10.0}

# ooswalk: era 6m → OOS 6m kế tiếp (2024-h1→OOS h2'24, h2'24→OOS h1'25, h1'25→OOS h2'25).
OOSWALK_ERA_KEYS = ["2024-h1", "2024-h2", "2025-h1"]
OOSWALK_WEEKS = [3, 4, 6, 9, 12]
OOSWALK_EPOCHS = 3
E21_OOSWALK_PRESETS = ["elite_60_3", "elite_60_3_vwap", "elite_or_quality"]
G23_OOSWALK_PRESETS = ["nova", "nova_fixed", "elite_or_quality"]
# Bar 6 tháng OOS (~n nhỏ hơn 2026 full-year).
FILTER_Q_OOSWALK = {"wr_gt": 47.0, "rr_gt": 2.15, "total_r_gt": 28.0, "max_dd_lt": 11.0}
FILTER_R_OOSWALK = {"wr_gt": 40.0, "rr_gt": 2.05, "total_r_gt": 45.0, "max_dd_lt": 14.0, "n_ge": 50}

# Stricter than previous fine (WR45/RR2.2) — aim to beat live actives.
FILTER_Q = {"wr_gt": 48.0, "rr_gt": 2.30, "total_r_gt": 40.0, "max_dd_lt": 9.0}
# Softer for g23 boost/explore — historical best is ~WR53.5 / +55R.
FILTER_Q_G23 = {"wr_gt": 47.0, "rr_gt": 2.20, "total_r_gt": 38.0, "max_dd_lt": 10.0}
# Dense / high-R books that quality filter drops.
FILTER_R = {"wr_gt": 40.0, "rr_gt": 2.10, "total_r_gt": 70.0, "max_dd_lt": 16.0, "n_ge": 80}

# Post-fill GBP: WR>50 / RR>2 / Total R>80 on realistic SL (ATR+spread).
FILTER_FILLBOOK = {
  "wr_gt": 50.0, "rr_gt": 2.0, "total_r_gt": 80.0, "max_dd_lt": 16.0, "n_ge": 40,
}
FILTER_WR50 = {
  "wr_gt": 49.99, "rr_gt": 2.0, "total_r_gt": 80.0, "max_dd_lt": 24.0, "n_ge": 40,
}
# EUR M15 (e21) live bar: WR>55 / RR>2.5 / Total R>100.
# The three gates are not independent: clearing WR>55 at RR>2.5 already pins
# EV = 0.55×2.5 − 0.45 = 0.925R/trade, so Total R>100 reduces to exactly n≥108.
# On the 2026-only OOS (~35 weeks) that is ≥3.1 fills/week — see EUR_R100_HYPER.
# n_ge 50 costs nothing under this bar (n≥108 is implied) and still blocks the
# 6–23 trade snipers whose WR is inside a ±20 point confidence interval.
FILTER_WR55 = {
  "wr_gt": 54.99, "rr_gt": 2.5, "total_r_gt": 100.0, "max_dd_lt": 16.0, "n_ge": 50,
}
FILTER_WR55_SHORT_OOS = {
  "wr_gt": 54.99, "rr_gt": 2.5, "total_r_gt": 45.0, "max_dd_lt": 16.0, "n_ge": 25,
}
G23_FILLBOOK_ROUNDS = [
  {
    # Re-learn 2025-h2 on new fills, hunt WR>50 on 2026 OOS.
    "weeks": [4, 5, 6],
    "presets": ["gbp_fill_wr", "gbp_fill_book", "gbp_fill_sniper"],
    "epochs": 4,
    "era_keys": ["2025-h2"],
    "oos_from": "2026-01-01",
    "oos_to": "2026-08-28",
    "reset_kb": True,
  },
  {
    # Longer OOS to accumulate Total R>80 if WR already works.
    "weeks": [4, 5, 6],
    "presets": ["gbp_fill_wr", "gbp_fill_book", "gbp_fill_flow"],
    "epochs": 3,
    "era_keys": ["2024-h2"],
    "oos_from": "2025-01-01",
    "oos_to": "2026-08-28",
    "reset_kb": True,
    "catalog_eras": [
      {
        "key": "2024-h2",
        "label": "2024 (6 tháng cuối)",
        "learn_from": "2024-07-01",
        "learn_until": "2024-12-31",
        "kb_profile": "era_2024_h2",
        "oos_from": "2025-01-01",
        "oos_to": "2026-08-28",
      },
    ],
  },
  {
    # WR squeeze on the long-OOS book that already clears R>80 (~WR43).
    "weeks": [4, 5, 6],
    "presets": [
      "elite_or_surgery", "anti_chase_strict", "elite_60_3_vwap", "gbp_fill_wr",
    ],
    "epochs": 3,
    "era_keys": ["2024-h2"],
    "oos_from": "2025-01-01",
    "oos_to": "2026-08-28",
    "reset_kb": False,
    "catalog_eras": [
      {
        "key": "2024-h2",
        "label": "2024 (6 tháng cuối)",
        "learn_from": "2024-07-01",
        "learn_until": "2024-12-31",
        "kb_profile": "era_2024_h2",
        "oos_from": "2025-01-01",
        "oos_to": "2026-08-28",
      },
    ],
  },
]

_WR50_ERA_2024_H2 = {
  "key": "2024-h2",
  "label": "2024 (6 tháng cuối)",
  "learn_from": "2024-07-01",
  "learn_until": "2024-12-31",
  "kb_profile": "era_2024_h2",
  "oos_from": "2025-01-01",
  "oos_to": "2026-08-28",
}
_WR50_ERA_2024_H1 = {
  "key": "2024-h1",
  "label": "2024 (6 tháng đầu)",
  "learn_from": "2024-01-01",
  "learn_until": "2024-06-30",
  "kb_profile": "era_2024_h1",
  "oos_from": "2024-07-01",
  "oos_to": "2026-08-28",
}
G23_WR50_ROUNDS = [
  {
    "weeks": [4, 5, 6],
    "presets": ["gbp_wr50_surg", "gbp_wr50_1td", "gbp_wr50_short", "gbp_wr50_london"],
    "epochs": 3,
    "era_keys": ["2024-h2"],
    "oos_from": "2025-01-01",
    "oos_to": "2026-08-28",
    "reset_kb": False,
    "catalog_eras": [_WR50_ERA_2024_H2],
  },
  {
    "weeks": [4, 5, 6],
    "presets": ["gbp_wr50_tight", "gbp_wr50_elite", "gbp_wr50_short_1td", "gbp_wr50_short_london"],
    "epochs": 3,
    "era_keys": ["2024-h2"],
    "oos_from": "2025-01-01",
    "oos_to": "2026-08-28",
    "reset_kb": False,
    "catalog_eras": [_WR50_ERA_2024_H2],
  },
  {
    "weeks": [4, 5, 6],
    "presets": ["gbp_wr50_surg", "gbp_wr50_1td", "gbp_wr50_short", "gbp_wr50_london"],
    "epochs": 3,
    "era_keys": ["2024-h1"],
    "oos_from": "2024-07-01",
    "oos_to": "2026-08-28",
    "reset_kb": True,
    "catalog_eras": [_WR50_ERA_2024_H1],
  },
  {
    "weeks": [4, 5, 6],
    "presets": ["gbp_wr50_tight", "gbp_wr50_elite", "gbp_wr50_london_1td", "gbp_wr50_short_london"],
    "epochs": 3,
    "era_keys": ["2024-h1"],
    "oos_from": "2024-07-01",
    "oos_to": "2026-08-28",
    "reset_kb": False,
    "catalog_eras": [_WR50_ERA_2024_H1],
  },
]

# e21 wr50: live bar WR>55 / RR>2.5 / Total R>100 after fill-like SL.
# Verify on 2026 only — the window closest to live conditions. Consequence to keep
# in mind when reading results: WR>55 at RR>2.5 fixes EV at 0.55×2.5 − 0.45 =
# 0.925R/trade, so Total R>100 is exactly n≥108. The 2026 OOS is ~34 weeks, hence
# it needs ≥3.17 fills/week sustained — only the three high-frequency branches are
# allowed to trade that often.
#
# Two learn windows, deliberately sharing one OOS window (oos_by_profile keys the
# OOS per kb_profile, so this has to be stated on each era). Same OOS means the
# only thing that varies is how much history the KB saw, which is the whole
# question: 12 months carries more samples, 6 months sits closer to the 2026
# regime and drags in less stale structure. Comparing them under different OOS
# windows would confound length with period and answer neither.
_E21_ERA_2025_FULL = {
  "key": "2025-full",
  "label": "2025 (12 tháng)",
  "learn_from": "2025-01-01",
  "learn_until": "2025-12-31",
  "kb_profile": "era_2025_full",
  "oos_from": "2026-01-01",
  "oos_to": "2026-08-28",
}
_E21_ERA_2025_H2 = {
  "key": "2025-h2",
  "label": "2025 (6 tháng cuối)",
  "learn_from": "2025-07-01",
  "learn_until": "2025-12-31",
  "kb_profile": "era_2025_h2",
  "oos_from": "2026-01-01",
  "oos_to": "2026-08-28",
}
# Retired as a grid axis on 2026-08-31: three independent draws all failed in
# sample (-0.28 / -2.29 / -3.98 R at epoch 2, 29-46 trades), with zero overlap
# against the 6-month era's 12 epoch results (worst +4.07 R, 138-159 trades). A
# rule set that cannot fit the window it learned has no mechanism to work out of
# sample, so spending 16 combos on it measures nothing. Kept in the catalog so
# the finding stays reproducible via scripts/measure_kb_draws.py.
_E21_ERA_2025_Q4 = {
  "key": "2025-q4",
  "label": "2025 (3 tháng cuối)",
  "learn_from": "2025-10-01",
  "learn_until": "2025-12-31",
  "kb_profile": "era_2025_q4",
  "oos_from": "2026-01-01",
  "oos_to": "2026-08-28",
}
# Third point on the era-length curve, replacing the 3-month era. The curve is
# not monotone: 12 months lost every combo to 6 months, but 3 months cannot even
# fit its own window, so the optimum sits between 6 and 12 and that gap is what
# needs sampling. Learn window still ends 2025-12-31 so the OOS stays identical
# and length remains the only variable.
_E21_ERA_2025_9M = {
  "key": "2025-9m",
  "label": "2025 (9 tháng cuối)",
  "learn_from": "2025-04-01",
  "learn_until": "2025-12-31",
  "kb_profile": "era_2025_9m",
  "oos_from": "2026-01-01",
  "oos_to": "2026-08-28",
}
# One round only. The 2026-08-31 mining-space audit cut the lineup 8 → 4 after
# proving the rest redundant by set containment (scripts/audit_mining_space.py), and
# with 4 presets a second round would just re-run the same spaces on shifted
# train weeks. The four span the knobs the miner reads as single values and so
# cannot scan inside one preset: expectancy vs elite ranking, veto width, and the
# frequency block. Everything scannable (RR, ATR, score, ML gate, rule breadth,
# spacing, and now both session windows) is explored inside each preset.
E21_WR50_ROUNDS = [
  {
    # 4 and 8 only: 6 and 9 sat between them without probing a different regime,
    # and dropping the pair halves the round to 32 combos.
    "weeks": [4, 8],
    "presets": [
      "eur_r100_hyper", "eur_r100_hyper_elite", "eur_r100_wide", "eur_r100_core",
    ],
    # Across the 324 combos already measured, OOS quality falls monotonically
    # with KB epoch (median R +1.07 / +0.07 / -0.32 / -0.59 for epochs 1-4; best
    # R 24.1 → 13.7). Deeper evolution just overfits the learn window, so cap at
    # 2: halves the grid and drops the worse half.
    "epochs": 2,
    # Grid = weeks × presets × (kb_profiles × epochs), so the second era doubles
    # the round to 32 combos and adds a second KB to learn up front.
    # 2025-full dropped: it lost every one of its 16 combos to the 6-month era.
    # 2025-q4 dropped: negative in sample on all three draws (see its comment).
    # 2025-h2 stays as the in-run control so the 9-month era is measured against a
    # result produced under identical presets, weeks, epochs and OOS.
    "era_keys": ["2025-h2", "2025-9m"],
    "oos_from": "2026-01-01",
    "oos_to": "2026-08-28",
    # False so the grid runs on the KB learned by the separate --kb-only pass and
    # audited on 2026-08-31. Reset would discard it and re-evolve new genomes.
    "reset_kb": False,
    "catalog_eras": [
      _E21_ERA_2025_FULL, _E21_ERA_2025_H2, _E21_ERA_2025_Q4, _E21_ERA_2025_9M,
    ],
    "filter_q": FILTER_WR55,
  },
]
# Deliberately no legacy eur_wr55_* round here: that family ranks genomes with
# anti_chase_score_with_veto=False and carries no trades/week floor, which is the
# measured cause of the ~24R/year ceiling (89 signal candidates → 2 fills). Re-
# running it would only re-confirm a known dead end.

# Runtime mode set by main() / run_desk().
_MODE = "densify"
_FILLBOOK_ROUND = 1
# ooswalk: era keys thực tế sau lọc theo data coverage.
_OOSWALK_ACTIVE_KEYS: list[str] = list(OOSWALK_ERA_KEYS)


def _round_table(desk: str | None = None) -> list[dict]:
  if _MODE == "wr50" and desk == "e21":
    return E21_WR50_ROUNDS
  return G23_WR50_ROUNDS if _MODE == "wr50" else G23_FILLBOOK_ROUNDS


def _round_filter(desk: str | None = None) -> dict:
  if _MODE == "wr50" and desk == "e21":
    rounds = _round_table(desk)
    idx = max(0, min(int(_FILLBOOK_ROUND) - 1, len(rounds) - 1))
    return dict(rounds[idx].get("filter_q") or FILTER_WR55)
  return dict(FILTER_WR50 if _MODE == "wr50" else FILTER_FILLBOOK)


def _purge() -> None:
  for name in list(sys.modules):
    if name in (
      "run_backtest", "knowledge_base", "config", "app_paths",
      "data_loader", "kb_profiles", "optimizer",
    ) or name.startswith("gui.") or name.startswith("mt5_bridge"):
      sys.modules.pop(name, None)


def _bind(desk: str) -> dict:
  cfg = apply_desk_env(desk)
  _purge()
  for p in (str(ROOT), str(cfg["core_root"])):
    if p in sys.path:
      sys.path.remove(p)
    sys.path.insert(0, p)
  return cfg


def _log(desk: str, msg: str) -> None:
  line = f"[{datetime.now().isoformat(timespec='seconds')}] [{desk}] {msg}"
  try:
    print(line, flush=True)
  except UnicodeEncodeError:
    print(line.encode("ascii", "replace").decode("ascii"), flush=True)
  log_dir = Path(os.environ["TRAINAPP_RUNTIME"]) / "results"
  log_dir.mkdir(parents=True, exist_ok=True)
  with open(log_dir / "pipeline_m15_tune.log", "a", encoding="utf-8") as f:
    f.write(line + "\n")


def _clear_stale_jobs(desk: str) -> None:
  jobs = Path(os.environ["TRAINAPP_RUNTIME"]) / "results" / "jobs" / "long_task_state.json"
  if not jobs.exists():
    return
  try:
    state = json.loads(jobs.read_text(encoding="utf-8"))
  except Exception:
    return
  if state.get("status") in ("running", "interrupted"):
    state["status"] = "cancelled"
    state["error"] = "Cleared by pipeline_m15_tune before re-run"
    state["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    state["updated_at"] = state["finished_at"]
    jobs.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _log(desk, f"cleared stale job {state.get('job_id')}")


def _profile_for(desk: str) -> dict:
  """Return weeks/presets/epochs/eras for current mode + desk."""
  if desk == "g23" and _MODE == "boost":
    return {
      "label": "g23 boost",
      "weeks": list(G23_BOOST_WEEKS),
      "presets": list(G23_BOOST_PRESETS),
      "epochs": int(G23_BOOST_EPOCHS),
      "era_keys": list(G23_BOOST_ERA_KEYS),
      "filter_q": dict(FILTER_Q_G23),
    }
  if desk == "g23" and _MODE == "explore":
    return {
      "label": "g23 explore non-curated",
      "weeks": list(G23_EXPLORE_WEEKS),
      "presets": list(G23_EXPLORE_PRESETS),
      "epochs": int(G23_EXPLORE_EPOCHS),
      "era_keys": list(G23_EXPLORE_ERA_KEYS),
      "filter_q": dict(FILTER_Q_G23),
    }
  if desk == "g23" and _MODE == "refine":
    return {
      "label": "g23 refine winners",
      "weeks": list(G23_REFINE_WEEKS),
      "presets": list(G23_REFINE_PRESETS),
      "epochs": int(G23_REFINE_EPOCHS),
      "era_keys": list(G23_REFINE_ERA_KEYS),
      "filter_q": dict(FILTER_Q_G23_REFINE),
    }
  if desk == "g23" and _MODE == "fullera":
    return {
      "label": "g23 full-era winners",
      "weeks": list(G23_FULLERA_WEEKS),
      "presets": list(G23_FULLERA_PRESETS),
      "epochs": int(G23_FULLERA_EPOCHS),
      "era_keys": list(G23_FULLERA_ERA_KEYS),
      "filter_q": dict(FILTER_Q_G23),
    }
  if desk == "g23" and _MODE == "hybrid":
    return {
      "label": "g23 elite+surgery hybrid",
      "weeks": list(G23_HYBRID_WEEKS),
      "presets": list(G23_HYBRID_PRESETS),
      "epochs": int(G23_HYBRID_EPOCHS),
      "era_keys": list(G23_HYBRID_ERA_KEYS),
      "filter_q": dict(FILTER_Q_G23_HYBRID),
    }
  if _MODE == "ooswalk":
    presets = list(E21_OOSWALK_PRESETS) if desk == "e21" else list(G23_OOSWALK_PRESETS)
    return {
      "label": f"{desk} OOS walk 6m→6m",
      "weeks": list(OOSWALK_WEEKS),
      "presets": presets,
      "epochs": int(OOSWALK_EPOCHS),
      "era_keys": list(_OOSWALK_ACTIVE_KEYS),
      "filter_q": dict(FILTER_Q_OOSWALK),
    }
  if (_MODE == "wr50" and desk in ("e21", "g23")) or (_MODE == "fillbook" and desk == "g23"):
    rounds = _round_table(desk)
    idx = max(0, min(int(_FILLBOOK_ROUND) - 1, len(rounds) - 1))
    rnd = rounds[idx]
    return {
      "label": f"{desk} {_MODE} r{idx + 1}",
      "weeks": list(rnd["weeks"]),
      "presets": list(rnd["presets"]),
      "epochs": int(rnd["epochs"]),
      "era_keys": list(rnd["era_keys"]),
        "filter_q": _round_filter(desk),
    }
  if _MODE == "target60":
    if desk == "e21":
      return {
        "label": "e21 target WR60 R100",
        "weeks": list(E21_TARGET60_WEEKS),
        "presets": list(E21_TARGET60_PRESETS),
        "epochs": int(E21_TARGET60_EPOCHS),
        "era_keys": list(E21_TARGET60_ERA_KEYS),
        "filter_q": dict(FILTER_TARGET60),
      }
    return {
      "label": "g23 target WR60 R100",
      "weeks": list(G23_TARGET60_WEEKS),
      "presets": list(G23_TARGET60_PRESETS),
      "epochs": int(G23_TARGET60_EPOCHS),
      "era_keys": list(G23_TARGET60_ERA_KEYS),
      "filter_q": dict(FILTER_TARGET60),
    }
  return {
    "label": "m15 densify v3",
    "weeks": list(FINE_WEEKS),
    "presets": list(FINE_PRESETS),
    "epochs": int(FINE_EPOCHS),
    "era_keys": list(FINE_ERA_KEYS),
    "filter_q": dict(FILTER_Q),
  }


def _apply_fine_settings(desk: str) -> dict:
  from gui.app_settings import load_settings, save_settings, TRAIN_WEEK_OPTIONS

  if _MODE == "ooswalk":
    _ensure_ooswalk_setup(desk)
  prof = _profile_for(desk)
  s = load_settings()
  allowed = set(TRAIN_WEEK_OPTIONS) if TRAIN_WEEK_OPTIONS else set(prof["weeks"])
  s["strategy_train_weeks"] = [w for w in prof["weeks"] if w in allowed] or list(prof["weeks"])
  s["mining_presets"] = list(prof["presets"])
  s["grid_objective"] = FINE_OBJECTIVE
  s["learning_era_keys"] = list(prof["era_keys"])
  s["learning_loops"] = int(prof["epochs"])
  if _MODE in ("fillbook", "wr50"):
    rounds = _round_table(desk)
    idx = max(0, min(int(_FILLBOOK_ROUND) - 1, len(rounds) - 1))
    rnd = rounds[idx]
    s["backtest_from"] = str(rnd.get("oos_from") or "2026-01-01")
    s["backtest_to"] = str(rnd.get("oos_to") or "2026-08-28")
    extra = rnd.get("catalog_eras") or []
    if extra:
      from gui.app_settings import merge_learning_eras_into_catalog
      merge_learning_eras_into_catalog(list(extra), active_keys=list(rnd["era_keys"]))
      s = load_settings()
      s["strategy_train_weeks"] = [w for w in prof["weeks"] if w in allowed] or list(prof["weeks"])
      s["mining_presets"] = list(prof["presets"])
      s["grid_objective"] = FINE_OBJECTIVE
      s["learning_era_keys"] = list(prof["era_keys"])
      s["learning_loops"] = int(prof["epochs"])
      s["backtest_from"] = str(rnd.get("oos_from") or s.get("backtest_from"))
      s["backtest_to"] = str(rnd.get("oos_to") or s.get("backtest_to"))
  save_settings(s)
  _log(
    desk,
    f"{prof['label']} weeks={s['strategy_train_weeks']} presets={s['mining_presets']} "
    f"epochs=1..{s['learning_loops']} obj={s['grid_objective']} eras={s['learning_era_keys']}",
  )
  return s


def _ensure_ooswalk_setup(desk: str) -> None:
  """Đăng ký 3 era walk-forward + lọc era theo data có sẵn."""
  global _OOSWALK_ACTIVE_KEYS
  from gui.app_settings import OOS_WALKFORWARD_ERAS, merge_learning_eras_into_catalog

  active: list[str] = []
  try:
    import pandas as pd
    from data_loader import load_eurusd_m15
    df = load_eurusd_m15()
    d0, d1 = df.index.min(), df.index.max()
    for e in OOS_WALKFORWARD_ERAS:
      need_from = pd.Timestamp(e["learn_from"])
      need_to = pd.Timestamp(e.get("oos_to") or e["learn_until"])
      if d0 <= need_from + pd.Timedelta(days=21) and d1 >= need_to - pd.Timedelta(days=21):
        active.append(e["key"])
      else:
        _log(
          desk,
          f"skip era {e['key']} — data {d0.date()}..{d1.date()} "
          f"không phủ học {need_from.date()}..{need_to.date()}",
        )
    if not active:
      raise RuntimeError(
        f"{desk}: không có era ooswalk nào khớp data {d0.date()}..{d1.date()}. "
        "Sync ForgeBridge history về 2024-01-01."
      )
    _OOSWALK_ACTIVE_KEYS = active
    _log(desk, f"ooswalk eras active: {active}")
  except RuntimeError:
    raise
  except Exception as exc:
    _log(desk, f"WARN era filter: {exc} — dùng full {OOSWALK_ERA_KEYS}")
    _OOSWALK_ACTIVE_KEYS = list(OOSWALK_ERA_KEYS)

  merge_learning_eras_into_catalog(
    [dict(e) for e in OOS_WALKFORWARD_ERAS],
    active_keys=list(_OOSWALK_ACTIVE_KEYS),
  )
  try:
    from mt5_bridge.history_sync import get_data_start_broker, set_data_start_broker
    cur = str(get_data_start_broker())[:10]
    if cur > "2024-01-01":
      _log(desk, f"data_start {cur} → 2024-01-01 (sync MT5 nếu Bridge đang chạy)")
      set_data_start_broker("2024-01-01 00:00", sync=True)
  except Exception as exc:
    _log(desk, f"WARN data_start: {exc}")


def _ensure_kb(desk: str, *, reset: bool) -> dict:
  from gui.app_settings import load_settings, resolve_learning_eras
  from gui.era_compare import ensure_profile_learned

  s = load_settings()
  eras = resolve_learning_eras(s)
  loops = int(s.get("learning_loops") or 4)
  learned, skipped = [], []
  for era in eras:
    label = era.get("label") or era["kb_profile"]
    _log(desk, f"KB ensure · {label} · target {loops} epochs · reset={reset}")
    spec = {
      "kb_profile": era["kb_profile"],
      "kb_name": era.get("label") or era["kb_profile"],
      "learn_from": era["learn_from"],
      "learn_until": era["learn_until"],
    }
    out = ensure_profile_learned(spec, epochs=loops, reset=reset)
    if out.get("skipped"):
      skipped.append(era["kb_profile"])
      _log(desk, f"KB skip (đã đủ) · {era['kb_profile']} epochs={out.get('epochs')}")
    else:
      learned.append(era["kb_profile"])
      _log(desk, f"KB learned · {era['kb_profile']}")
  return {"learned": learned, "skipped": skipped}


def _n(row: dict) -> int:
  try:
    return int(row.get("n_trades") or 0)
  except Exception:
    return 0


def _passes_q(row: dict, filt: dict | None = None) -> bool:
  f = filt or FILTER_Q
  if row.get("error"):
    return False
  try:
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    dd = float(row.get("max_drawdown_r") or 999)
  except Exception:
    return False
  return (
    wr > f["wr_gt"]
    and rr > f["rr_gt"]
    and tot > f["total_r_gt"]
    and dd < f["max_dd_lt"]
    and _n(row) >= int(f.get("n_ge") or 20)
  )


def _passes_r(row: dict) -> bool:
  filt = FILTER_R_OOSWALK if _MODE == "ooswalk" else FILTER_R
  if row.get("error"):
    return False
  try:
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    dd = float(row.get("max_drawdown_r") or 999)
  except Exception:
    return False
  return (
    wr > filt["wr_gt"]
    and rr > filt["rr_gt"]
    and tot > filt["total_r_gt"]
    and dd < filt["max_dd_lt"]
    and _n(row) >= int(filt["n_ge"])
  )


def _run_grid(desk: str, *, workers: int) -> dict:
  from gui.app_settings import load_settings
  from gui.grid_search_engine import (
    build_grid_from_settings, grid_readiness, run_grid, save_grid_run, _score,
  )
  from config import DEFAULT_TF

  s = load_settings()
  ready = grid_readiness(s)
  _log(
    desk,
    f"KB readiness kb_complete={ready.get('kb_complete')} "
    f"expected={ready.get('expected_combos')} ready={ready.get('ready_combos')}",
  )
  if not ready.get("kb_complete"):
    raise RuntimeError(f"{desk}: KB chưa đủ — {ready}")

  specs, config = build_grid_from_settings(s)
  if len(specs) > 200:
    _log(desk, f"WARN truncating grid {len(specs)} → 200")
    specs = specs[:200]
  objective = str(s.get("grid_objective") or FINE_OBJECTIVE)
  _log(desk, f"Grid start: {len(specs)} combo · objective={objective} · workers={workers}")
  t0 = time.time()

  def on_prog(done, total, label):
    if done == 0 or done == 1 or done == total or done % 5 == 0:
      _log(desk, f"Grid {done}/{total}: {label}")

  rows = run_grid(specs, objective=objective, on_progress=on_prog, workers=workers)
  prof = _profile_for(desk)
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": DEFAULT_TF,
      "filter_quality": prof["filter_q"],
      "filter_high_r": FILTER_R,
      "source": "pipeline_m15_tune",
      "mode": _MODE,
      "fine_tune": {
        "weeks": prof["weeks"],
        "presets": prof["presets"],
        "epochs": prof["epochs"],
        "era_keys": prof["era_keys"],
        "objective": FINE_OBJECTIVE,
        "label": prof["label"],
      },
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  _log(desk, f"Grid done {rid}: {len(ok)}/{len(rows)} OK in {time.time() - t0:.0f}s")

  ranked = sorted(ok, key=lambda r: _score(r, objective), reverse=True)
  for r in ranked[:8]:
    _log(
      desk,
      f"topQ WR={float(r.get('win_rate_pct') or 0):.1f} RR={float(r.get('avg_rr') or 0):.2f} "
      f"R={float(r.get('total_r') or 0):.1f} DD={float(r.get('max_drawdown_r') or 0):.1f} "
      f"n={r.get('n_trades')} · {r.get('label')}",
    )
  ranked_r = sorted(ok, key=lambda r: float(r.get("total_r") or -1e9), reverse=True)
  for r in ranked_r[:5]:
    _log(
      desk,
      f"topR R={float(r.get('total_r') or 0):.1f} WR={float(r.get('win_rate_pct') or 0):.1f} "
      f"DD={float(r.get('max_drawdown_r') or 0):.1f} n={r.get('n_trades')} · {r.get('label')}",
    )
  return {"run_id": rid, "rows": rows, "objective": objective}


def _promote(desk: str, run: dict, *, max_quality: int = 4, max_high_r: int = 3) -> list[dict]:
  from gui.grid_search_engine import _score
  from gui.trade_model import create_trade_model

  rows = [r for r in (run.get("rows") or []) if not r.get("error")]
  objective = str(run.get("objective") or FINE_OBJECTIVE)
  prof = _profile_for(desk)
  fq = prof["filter_q"]

  q_hits = [r for r in rows if _passes_q(r, fq)]
  # g23 boost/explore: among quality floor, prefer higher Total R to close gap vs e21.
  if _MODE in ("target60", "ooswalk", "fillbook", "wr50") or desk == "g23" and _MODE in (
    "boost", "explore", "refine", "fullera", "hybrid",
  ):
    q_hits.sort(
      key=lambda r: (float(r.get("total_r") or 0), float(r.get("win_rate_pct") or 0)),
      reverse=True,
    )
  else:
    q_hits.sort(key=lambda r: _score(r, objective), reverse=True)
  _log(
    desk,
    f"Quality hits WR>{fq['wr_gt']}/RR>{fq['rr_gt']}/"
    f"R>{fq['total_r_gt']}/DD<{fq['max_dd_lt']}: {len(q_hits)}",
  )

  if not q_hits and _MODE == "target60":
    _log(desk, "No hits WR>60/R>100 — không promote (bar target60)")
  if not q_hits and _MODE in ("fillbook", "wr50"):
    f = _round_filter(desk)
    _log(
      desk,
      f"No hits WR>{f['wr_gt']}/RR>{f['rr_gt']}/R>{f['total_r_gt']} — không promote",
    )
  if not q_hits and _MODE == "ooswalk":
    _log(desk, "No strict quality — ooswalk soft fallback WR>45 RR>2.1 R>22 DD<12")
    q_hits = [
      r for r in rows
      if float(r.get("win_rate_pct") or 0) > 45.0
      and float(r.get("avg_rr") or 0) > 2.1
      and float(r.get("total_r") or 0) > 22.0
      and float(r.get("max_drawdown_r") or 999) < 12.0
      and _n(r) >= 15
    ]
    q_hits.sort(
      key=lambda r: (float(r.get("total_r") or 0), float(r.get("win_rate_pct") or 0)),
      reverse=True,
    )
  if not q_hits and _MODE not in ("target60", "ooswalk", "fillbook", "wr50"):
    _log(desk, "No strict quality — soft fallback WR>45 RR>2.2 R>35 DD<12")
    q_hits = [
      r for r in rows
      if float(r.get("win_rate_pct") or 0) > 45.0
      and float(r.get("avg_rr") or 0) > 2.2
      and float(r.get("total_r") or 0) > 35.0
      and float(r.get("max_drawdown_r") or 999) < 12.0
      and _n(r) >= 20
    ]
    if _MODE == "target60" or desk == "g23" and _MODE in (
      "boost", "explore", "refine", "fullera", "hybrid", "ooswalk",
    ):
      q_hits.sort(
        key=lambda r: (float(r.get("total_r") or 0), float(r.get("win_rate_pct") or 0)),
        reverse=True,
      )
    else:
      q_hits.sort(key=lambda r: _score(r, objective), reverse=True)

  r_filt = FILTER_R_OOSWALK if _MODE == "ooswalk" else FILTER_R
  r_hits = [] if _MODE in ("target60", "fillbook", "wr50") else [r for r in rows if _passes_r(r)]
  r_hits.sort(key=lambda r: float(r.get("total_r") or -1e9), reverse=True)
  # Dedup vs quality picks by grid key
  q_keys = {r.get("key") for r in q_hits[:max_quality]}
  r_hits = [r for r in r_hits if r.get("key") not in q_keys]
  _log(
    desk,
    f"High-R hits R>{r_filt['total_r_gt']}/WR>{r_filt['wr_gt']}/"
    f"DD<{r_filt['max_dd_lt']}/n>={r_filt['n_ge']}: {len(r_hits)} (after dedup)",
  )

  created = []
  active_set = False
  cur_r = cur_wr = None
  if _MODE in ("refine", "fullera", "hybrid", "target60", "fillbook", "wr50"):
    try:
      from gui.trade_model import get_active_trade_model
      cur = get_active_trade_model() or {}
      cur_r = float(cur.get("total_r") or 0)
      cur_wr = float(cur.get("win_rate_pct") or 0)
      _log(desk, f"{_MODE} keep-bar vs active R={cur_r:.1f} WR={cur_wr:.1f}")
    except Exception:
      cur_r = cur_wr = None

  def _add(row: dict, *, track: str, set_active: bool) -> None:
    nonlocal active_set
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    preset = row.get("mining_preset") or "?"
    oos_tag = ""
    if _MODE == "ooswalk":
      of = str(row.get("oos_from") or "")[:7]
      ot = str(row.get("oos_to") or "")[:7]
      if of and ot:
        oos_tag = f" OOS{of}→{ot}"
    if _MODE == "ooswalk":
      prefix = "OOSW"
    elif _MODE in ("fillbook", "wr50"):
      prefix = "EUR" if desk == "e21" else "GBP"
    else:
      prefix = "M15Q" if track == "quality" else "M15R"
    label = f"{prefix} {preset} WR{wr:.0f} RR{rr:.2f} +{tot:.0f}R{oos_tag}"
    # refine/fullera/target60: only flip active if strictly improves (R, then WR) vs current.
    do_active = set_active and _MODE != "ooswalk"
    if do_active and cur_r is not None:
      better = (tot > cur_r + 0.5) or (tot >= cur_r - 0.5 and wr > cur_wr + 0.5)
      if not better:
        _log(desk, f"skip active (not better than current): {label}")
        do_active = False
    model = create_trade_model(
      row,
      run_id=run.get("run_id"),
      label=label,
      set_active=do_active,
    )
    created.append(model)
    if do_active:
      active_set = True
    _log(
      desk,
      f"Promoted[{track}] {model.get('id')} · {label} · dd={row.get('max_drawdown_r')} "
      f"n={row.get('n_trades')} active={do_active}",
    )

  for i, row in enumerate(q_hits[:max_quality]):
    _add(row, track="quality", set_active=(i == 0))
  for i, row in enumerate(r_hits[:max_high_r]):
    _add(row, track="high_r", set_active=(not active_set and i == 0))

  if not created:
    _log(desk, "Không promote được model nào")
  return created


def _promote_missed_from_latest(desk: str) -> list[dict]:
  """Quick win: dual-promote high-R books already in latest grid (pre-new-run)."""
  from gui.grid_search_engine import load_latest_grid_run

  run = load_latest_grid_run() or {}
  if not run.get("rows"):
    _log(desk, "No latest grid to salvage")
    return []
  _log(desk, f"Salvage dual-promote from latest run_id={run.get('run_id')}")
  # Only high-R track here so we don't reshuffle quality active before new grid.
  from gui.trade_model import create_trade_model, get_active_trade_model

  active = get_active_trade_model()
  active_id = (active or {}).get("id")
  rows = [r for r in (run.get("rows") or []) if _passes_r(r)]
  rows.sort(key=lambda r: float(r.get("total_r") or -1e9), reverse=True)
  created = []
  for row in rows[:3]:
    wr = float(row.get("win_rate_pct") or 0)
    rr = float(row.get("avg_rr") or 0)
    tot = float(row.get("total_r") or 0)
    preset = row.get("mining_preset") or "?"
    label = f"M15R {preset} WR{wr:.0f} RR{rr:.2f} +{tot:.0f}R"
    model = create_trade_model(
      row,
      run_id=run.get("run_id"),
      label=label,
      set_active=False,
    )
    created.append(model)
    _log(desk, f"Salvaged {model.get('id')} · {label} · keep active={active_id}")
  # Ensure previous active stays
  if active_id:
    try:
      from gui.trade_model import set_active_trade_model
      set_active_trade_model(active_id)
    except Exception:
      pass
  return created


def _log_closest(desk: str, rows: list[dict], *, n: int = 8) -> None:
  ok = [r for r in rows if not r.get("error")]
  filt = _round_filter(desk)
  def _gap(r):
    wr = float(r.get("win_rate_pct") or 0)
    rr = float(r.get("avg_rr") or 0)
    tot = float(r.get("total_r") or 0)
    return (
      max(0.0, filt["wr_gt"] - wr)
      + max(0.0, filt["rr_gt"] - rr) * 20.0
      + max(0.0, filt["total_r_gt"] - tot) * 0.15
    )
  closest = sorted(ok, key=_gap)[:n]
  for r in closest:
    _log(
      desk,
      f"closest WR={float(r.get('win_rate_pct') or 0):.1f} "
      f"RR={float(r.get('avg_rr') or 0):.2f} "
      f"R={float(r.get('total_r') or 0):.1f} n={r.get('n_trades')} "
      f"· {r.get('mining_preset')} · {r.get('label')}",
    )


def roster_aggregate(
  rows: list[dict], filt: dict, *, max_models: int = 4, leg_n_ge: int = 25,
) -> dict:
  """Aggregate the best roster of distinct models into one combined book.

  A single walk-forward book on EUR M15 tops out near 40–60 trades even at the
  eur_r100_* fill rate, so Total R>100 can be out of reach per model while a
  live roster of distinct models reaches it — that is how the bridge actually
  runs. WR and Total R aggregate exactly from per-row n and wins; RR is derived
  from the summed expectancy; DD is the worst case (sum) because grid rows carry
  no trade timestamps to interleave.

  ``leg_n_ge`` is deliberately below ``filt["n_ge"]``: a roster leg is allowed to
  be a smaller book because the combined n carries the statistics.
  """
  eligible = [
    r for r in rows
    if not r.get("error")
    and float(r.get("win_rate_pct") or 0) > filt["wr_gt"]
    and float(r.get("avg_rr") or 0) > filt["rr_gt"]
    and int(r.get("n_trades") or 0) >= int(leg_n_ge)
  ]
  if not eligible:
    return {"picks": [], "ok": False}
  # One model per preset: the same preset across train_weeks/epoch trades the
  # same setups, so stacking those would double-count a single edge.
  by_preset: dict[str, dict] = {}
  for r in sorted(eligible, key=lambda x: float(x.get("total_r") or 0), reverse=True):
    by_preset.setdefault(str(r.get("mining_preset") or "?"), r)
  picks = list(by_preset.values())[:max_models]

  n_sum = sum(int(r.get("n_trades") or 0) for r in picks)
  wins = sum(
    round(float(r.get("win_rate_pct") or 0) / 100.0 * int(r.get("n_trades") or 0))
    for r in picks
  )
  r_sum = sum(float(r.get("total_r") or 0) for r in picks)
  losses = max(n_sum - wins, 0)
  wr = (wins / n_sum * 100.0) if n_sum else 0.0
  avg_win_r = (r_sum + losses) / max(wins, 1)
  return {
    "picks": picks,
    "n_trades": n_sum,
    "win_rate_pct": wr,
    "avg_rr": avg_win_r,
    "total_r": r_sum,
    "max_drawdown_r": sum(float(r.get("max_drawdown_r") or 0) for r in picks),
    "ok": bool(
      wr > filt["wr_gt"] and avg_win_r > filt["rr_gt"] and r_sum > filt["total_r_gt"]
    ),
  }


def _log_roster_stack(desk: str, rows: list[dict], *, max_models: int = 4) -> None:
  filt = _round_filter(desk)
  agg = roster_aggregate(rows, filt, max_models=max_models)
  if not agg["picks"]:
    _log(desk, "roster: không có combo nào đạt WR/RR đủ để gộp")
    return
  _log(
    desk,
    f"roster x{len(agg['picks'])} {'ĐẠT' if agg['ok'] else 'chưa đạt'} "
    f"WR={agg['win_rate_pct']:.1f} RR≈{agg['avg_rr']:.2f} R={agg['total_r']:.1f} "
    f"n={agg['n_trades']} DD≤{agg['max_drawdown_r']:.1f} "
    f"· {', '.join(str(r.get('mining_preset')) for r in agg['picks'])}",
  )
  for r in agg["picks"]:
    _log(
      desk,
      f"  roster leg WR={float(r.get('win_rate_pct') or 0):.1f} "
      f"RR={float(r.get('avg_rr') or 0):.2f} R={float(r.get('total_r') or 0):.1f} "
      f"n={r.get('n_trades')} · {r.get('mining_preset')} · {r.get('label')}",
    )


def run_desk(
  desk: str,
  *,
  reset_kb: bool,
  workers: int,
  skip_grid: bool,
  salvage: bool,
  mode: str = "densify",
  kb_only: bool = False,
) -> dict:
  global _MODE, _FILLBOOK_ROUND
  _MODE = mode
  if desk not in ("e21", "g23"):
    raise ValueError(f"pipeline_m15_tune chỉ hỗ trợ e21,g23 — nhận {desk!r}")
  if mode in ("boost", "explore", "refine", "fullera", "hybrid", "fillbook") and desk != "g23":
    raise ValueError(f"--mode {mode} chỉ hỗ trợ desk g23")
  if mode == "wr50" and desk not in ("e21", "g23"):
    raise ValueError("--mode wr50 chỉ hỗ trợ e21,g23")
  if mode == "target60" and desk not in ("e21", "g23"):
    raise ValueError("--mode target60 chỉ hỗ trợ e21,g23")
  if mode == "ooswalk" and desk not in ("e21", "g23"):
    raise ValueError("--mode ooswalk chỉ hỗ trợ e21,g23")
  cfg = _bind(desk)
  _log(desk, f"start pair={cfg.get('pair')} tf={cfg.get('tf')} mode={mode}")
  _clear_stale_jobs(desk)
  salvaged = (
    _promote_missed_from_latest(desk)
    if salvage and mode not in ("ooswalk", "fillbook", "wr50") else []
  )
  if mode in ("fillbook", "wr50"):
    start = max(1, int(os.environ.get("FILLBOOK_START_ROUND", "1")))
    last_run = {"run_id": None, "rows": []}
    created: list[dict] = []
    kb = {"learned": [], "skipped": []}
    rounds = _round_table(desk)
    for i, rnd in enumerate(rounds):
      if i + 1 < start:
        continue
      _FILLBOOK_ROUND = i + 1
      filt = _round_filter(desk)
      _apply_fine_settings(desk)
      round_kb = _ensure_kb(desk, reset=bool(rnd.get("reset_kb")))
      # Rounds can share eras, so union instead of overwrite.
      for key in ("learned", "skipped"):
        kb[key] = list(dict.fromkeys(kb[key] + round_kb[key]))
      if kb_only:
        _log(desk, f"{mode} round {i + 1}: --kb-only, dừng trước grid")
        continue
      last_run = _run_grid(desk, workers=workers)
      hits = [r for r in (last_run.get("rows") or []) if _passes_q(r, filt)]
      _log(desk, f"{mode} round {i + 1} hits={len(hits)}")
      if not hits:
        _log_closest(desk, last_run.get("rows") or [])
        _log_roster_stack(desk, last_run.get("rows") or [])
        continue
      created = _promote(desk, last_run, max_quality=3, max_high_r=0)
      break
    if kb_only:
      return {
        "desk": desk,
        "mode": mode,
        "kb_only": True,
        "kb": kb,
        "rounds": len(rounds) - start + 1,
      }
    if not created:
      f = _round_filter(desk)
      _log(
        desk,
        f"{mode}: chưa đạt WR>{f['wr_gt']} RR>{f['rr_gt']} R>{f['total_r_gt']} sau mọi round",
      )
    return {
      "desk": desk,
      "mode": mode,
      "kb": kb,
      "run_id": last_run.get("run_id"),
      "n_combos": len(last_run.get("rows") or []),
      "salvaged": 0,
      "promoted": len(created),
      "models": [m.get("id") for m in created],
      "round": int(_FILLBOOK_ROUND),
    }
  _apply_fine_settings(desk)
  kb = _ensure_kb(desk, reset=reset_kb)
  if kb_only:
    return {"desk": desk, "mode": mode, "kb_only": True, "kb": kb}
  if skip_grid:
    from gui.grid_search_engine import load_latest_grid_run
    run = load_latest_grid_run() or {}
    created = _promote(desk, run)
    return {
      "desk": desk, "kb": kb, "run_id": run.get("run_id"),
      "mode": mode, "salvaged": len(salvaged),
      "promoted": len(created), "models": [m.get("id") for m in created],
    }
  run = _run_grid(desk, workers=workers)
  created = _promote(desk, run)
  return {
    "desk": desk,
    "mode": mode,
    "kb": kb,
    "run_id": run.get("run_id"),
    "n_combos": len(run.get("rows") or []),
    "salvaged": len(salvaged),
    "promoted": len(created),
    "models": [m.get("id") for m in created],
  }


def main() -> int:
  if hasattr(sys.stdout, "reconfigure"):
    try:
      sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass
  ap = argparse.ArgumentParser(description=__doc__)
  ap.add_argument("--desks", default="e21,g23")
  ap.add_argument("--mode", choices=(
    "densify", "boost", "explore", "refine", "fullera", "hybrid",
    "target60", "ooswalk", "fillbook", "wr50",
  ), default="densify",
                  help="wr50 e21=WR>55 RR>2.5 R>90; g23=WR>50 R>80 RR>2; fillbook=g23; target60=WR>60+R>100")
  ap.add_argument("--reset-kb", action="store_true")
  ap.add_argument("--workers", type=int, default=2,
                  help="Keep low while M5 tune shares the machine (default 2)")
  ap.add_argument("--promote-only", action="store_true")
  ap.add_argument("--kb-only", action="store_true",
                  help="Học KB cho mọi era rồi dừng trước Grid (dùng khi muốn "
                       "tách hai pha để kiểm tra KB trước)")
  ap.add_argument("--no-salvage", action="store_true",
                  help="Skip promoting high-R books from previous latest grid")
  args = ap.parse_args()
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  if args.mode in ("boost", "explore", "refine", "fullera", "hybrid", "fillbook"):
    desks = [d for d in desks if d == "g23"] or ["g23"]
  elif args.mode == "wr50":
    desks = [d for d in desks if d in ("e21", "g23")] or ["e21"]
  summary = []
  rc = 0
  for desk in desks:
    try:
      summary.append(run_desk(
        desk,
        reset_kb=bool(args.reset_kb),
        workers=max(1, int(args.workers)),
        skip_grid=bool(args.promote_only),
        salvage=not bool(args.no_salvage),
        mode=str(args.mode),
        kb_only=bool(args.kb_only),
      ))
    except Exception as exc:
      rc = 1
      try:
        _bind(desk)
        _log(desk, f"FAILED: {exc}")
      except Exception:
        print(f"FAILED {desk}: {exc}", flush=True)
      summary.append({"desk": desk, "error": str(exc)})
  print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
  return rc


if __name__ == "__main__":
  raise SystemExit(main())
