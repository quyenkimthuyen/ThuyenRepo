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

# e21 filladapt: Bid/Ask geometry — wider SL, closer TP. 3×4×3×2 = 72 combo.
# Densify on elite RR3.2–4 peaked WR33; do not swap Active unless quality hits.
E21_FILLADAPT_WEEKS = [6, 8, 12]
E21_FILLADAPT_PRESETS = [
  "eur_fill_wide",
  "eur_fill_book",
  "eur_fill_wr",
  "eur_fill_flow",
]
E21_FILLADAPT_EPOCHS = 3
E21_FILLADAPT_ERA_KEYS = ["2025-full", "2025-h2"]
FILTER_FILLADAPT = {
  "wr_gt": 40.0, "rr_gt": 2.0, "total_r_gt": 35.0, "max_dd_lt": 12.0,
}

# e21 fillrefine: densify around filladapt winner (book WR38/+43R). 2×4×3×2 = 48.
# No KB reset — profiles already Bid/Ask. Do not swap Active unless quality hits.
E21_FILLREFINE_WEEKS = [8, 12]
E21_FILLREFINE_PRESETS = [
  "eur_fill_surg",
  "eur_fill_rsi",
  "eur_fill_core",
  "eur_fill_short",
]
E21_FILLREFINE_EPOCHS = 3
E21_FILLREFINE_ERA_KEYS = ["2025-full", "2025-h2"]

# e21 fillkeep: old-era skeleton + fill-aware RR/ATR. 2×2×3×3 = 36 combo.
# Restore 2025-h1 (elite +139R KB source); OOS all 2026; only reset h1 KB.
E21_FILLKEEP_WEEKS = [8, 12]
E21_FILLKEEP_PRESETS = ["eur_fill_book", "eur_fill_core"]
E21_FILLKEEP_EPOCHS = 3
E21_FILLKEEP_ERA_KEYS = ["2025-full", "2025-h1", "2025-h2"]

# e21 fillgeom: TP no longer × SL spread buffer. Book DNA + 4 geometry knobs.
# 2×4×3×2 = 48. Do not swap Active unless quality hits.
E21_FILLGEOM_WEEKS = [8, 12]
E21_FILLGEOM_PRESETS = [
  "eur_fill_geom",
  "eur_fill_reach",
  "eur_fill_bank",
  "eur_fill_vol",
]
E21_FILLGEOM_EPOCHS = 3
E21_FILLGEOM_ERA_KEYS = ["2025-full", "2025-h2"]

_FILL_E21_MODES = ("filladapt", "fillrefine", "fillkeep", "fillgeom")

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

# Runtime mode set by main() / run_desk().
_MODE = "densify"
_FILLBOOK_ROUND = 1
# ooswalk: era keys thực tế sau lọc theo data coverage.
_OOSWALK_ACTIVE_KEYS: list[str] = list(OOSWALK_ERA_KEYS)


def _round_table() -> list[dict]:
  return G23_WR50_ROUNDS if _MODE == "wr50" else G23_FILLBOOK_ROUNDS


def _round_filter() -> dict:
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
  if desk == "g23" and _MODE in ("fillbook", "wr50"):
    rounds = _round_table()
    idx = max(0, min(int(_FILLBOOK_ROUND) - 1, len(rounds) - 1))
    rnd = rounds[idx]
    return {
      "label": f"g23 {_MODE} r{idx + 1}",
      "weeks": list(rnd["weeks"]),
      "presets": list(rnd["presets"]),
      "epochs": int(rnd["epochs"]),
      "era_keys": list(rnd["era_keys"]),
      "filter_q": _round_filter(),
    }
  if desk == "e21" and _MODE == "filladapt":
    return {
      "label": "e21 filladapt Bid/Ask",
      "weeks": list(E21_FILLADAPT_WEEKS),
      "presets": list(E21_FILLADAPT_PRESETS),
      "epochs": int(E21_FILLADAPT_EPOCHS),
      "era_keys": list(E21_FILLADAPT_ERA_KEYS),
      "filter_q": dict(FILTER_FILLADAPT),
    }
  if desk == "e21" and _MODE == "fillrefine":
    return {
      "label": "e21 fillrefine WR/R",
      "weeks": list(E21_FILLREFINE_WEEKS),
      "presets": list(E21_FILLREFINE_PRESETS),
      "epochs": int(E21_FILLREFINE_EPOCHS),
      "era_keys": list(E21_FILLREFINE_ERA_KEYS),
      "filter_q": dict(FILTER_FILLADAPT),
    }
  if desk == "e21" and _MODE == "fillkeep":
    return {
      "label": "e21 fillkeep old-eras + new fill",
      "weeks": list(E21_FILLKEEP_WEEKS),
      "presets": list(E21_FILLKEEP_PRESETS),
      "epochs": int(E21_FILLKEEP_EPOCHS),
      "era_keys": list(E21_FILLKEEP_ERA_KEYS),
      "filter_q": dict(FILTER_FILLADAPT),
    }
  if desk == "e21" and _MODE == "fillgeom":
    return {
      "label": "e21 fillgeom TP không nhân spread",
      "weeks": list(E21_FILLGEOM_WEEKS),
      "presets": list(E21_FILLGEOM_PRESETS),
      "epochs": int(E21_FILLGEOM_EPOCHS),
      "era_keys": list(E21_FILLGEOM_ERA_KEYS),
      "filter_q": dict(FILTER_FILLADAPT),
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
  if _MODE == "fillkeep":
    # Old elite_60_3 used h1 KB + OOS 2026. Catalog h1 still has ooswalk H2'25 —
    # strip so grid_build_kwargs does not divert h1 combos off 2026.
    eras = []
    for e in list(s.get("learning_eras") or []):
      e = dict(e)
      if e.get("key") == "2025-h1":
        e.pop("oos_from", None)
        e.pop("oos_to", None)
      eras.append(e)
    s["learning_eras"] = eras
    s["backtest_from"] = "2026-01-01"
    s["backtest_to"] = "2026-12-31"
  if _MODE in ("fillbook", "wr50"):
    rounds = _round_table()
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
    era_reset = bool(reset)
    if _MODE == "fillkeep" and not reset:
      era_reset = era.get("key") == "2025-h1" or era.get("kb_profile") == "era_2025_h1"
    _log(desk, f"KB ensure · {label} · target {loops} epochs · reset={era_reset}")
    spec = {
      "kb_profile": era["kb_profile"],
      "kb_name": era.get("label") or era["kb_profile"],
      "learn_from": era["learn_from"],
      "learn_until": era["learn_until"],
    }
    out = ensure_profile_learned(spec, epochs=loops, reset=era_reset)
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
    if done == 1 or done == total or done % 5 == 0:
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
  if _MODE in ("target60", "ooswalk", "fillbook", "wr50") + _FILL_E21_MODES or desk == "g23" and _MODE in (
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
    _log(desk, "No hits WR>50/RR>2/R>80 — không promote")
  if not q_hits and _MODE in _FILL_E21_MODES:
    _log(desk, "No hits WR>40/RR>2/R>35/DD<12 — không promote (giữ roster cũ)")
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
  if not q_hits and _MODE not in ("target60", "ooswalk", "fillbook", "wr50") + _FILL_E21_MODES:
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
  r_hits = [] if _MODE in ("target60", "fillbook", "wr50") + _FILL_E21_MODES else [r for r in rows if _passes_r(r)]
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
      prefix = "GBP"
    else:
      prefix = "M15Q" if track == "quality" else "M15R"
    label = f"{prefix} {preset} WR{wr:.0f} RR{rr:.2f} +{tot:.0f}R{oos_tag}"
    # refine/fullera/target60: only flip active if strictly improves (R, then WR) vs current.
    do_active = set_active and _MODE not in ("ooswalk",) + _FILL_E21_MODES
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
  filt = dict(_profile_for(desk).get("filter_q") or _round_filter())
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


def run_desk(
  desk: str,
  *,
  reset_kb: bool,
  workers: int,
  skip_grid: bool,
  salvage: bool,
  mode: str = "densify",
) -> dict:
  global _MODE, _FILLBOOK_ROUND
  _MODE = mode
  if desk not in ("e21", "g23"):
    raise ValueError(f"pipeline_m15_tune chỉ hỗ trợ e21,g23 — nhận {desk!r}")
  if mode in ("boost", "explore", "refine", "fullera", "hybrid", "fillbook", "wr50") and desk != "g23":
    raise ValueError(f"--mode {mode} chỉ hỗ trợ desk g23")
  if mode in _FILL_E21_MODES and desk != "e21":
    raise ValueError(f"--mode {mode} chỉ hỗ trợ desk e21")
  if mode == "target60" and desk not in ("e21", "g23"):
    raise ValueError("--mode target60 chỉ hỗ trợ e21,g23")
  if mode == "ooswalk" and desk not in ("e21", "g23"):
    raise ValueError("--mode ooswalk chỉ hỗ trợ e21,g23")
  cfg = _bind(desk)
  _log(desk, f"start pair={cfg.get('pair')} tf={cfg.get('tf')} mode={mode}")
  _clear_stale_jobs(desk)
  salvaged = (
    _promote_missed_from_latest(desk)
    if salvage and mode not in ("ooswalk", "fillbook", "wr50") + _FILL_E21_MODES else []
  )
  if mode in ("fillbook", "wr50"):
    start = max(1, int(os.environ.get("FILLBOOK_START_ROUND", "1")))
    last_run = {"run_id": None, "rows": []}
    created: list[dict] = []
    kb = {"learned": [], "skipped": []}
    rounds = _round_table()
    filt = _round_filter()
    for i, rnd in enumerate(rounds):
      if i + 1 < start:
        continue
      _FILLBOOK_ROUND = i + 1
      _apply_fine_settings(desk)
      kb = _ensure_kb(desk, reset=bool(rnd.get("reset_kb")))
      last_run = _run_grid(desk, workers=workers)
      hits = [r for r in (last_run.get("rows") or []) if _passes_q(r, filt)]
      _log(desk, f"{mode} round {i + 1} hits={len(hits)}")
      if not hits:
        _log_closest(desk, last_run.get("rows") or [])
        continue
      created = _promote(desk, last_run, max_quality=3, max_high_r=0)
      break
    if not created:
      _log(desk, f"{mode}: chưa đạt WR>50 RR>2 R>80 sau mọi round")
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
  if mode in _FILL_E21_MODES:
    created = _promote(desk, run, max_quality=4, max_high_r=0)
    if not created:
      _log_closest(desk, run.get("rows") or [])
  else:
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
    "target60", "ooswalk", "fillbook", "wr50", "filladapt", "fillrefine", "fillkeep",
    "fillgeom",
  ), default="densify",
                  help="fillgeom=e21 TP không nhân spread; fillkeep=old eras; wr50/fillbook=g23")
  ap.add_argument("--reset-kb", action="store_true")
  ap.add_argument("--workers", type=int, default=2,
                  help="Keep low while M5 tune shares the machine (default 2)")
  ap.add_argument("--promote-only", action="store_true")
  ap.add_argument("--no-salvage", action="store_true",
                  help="Skip promoting high-R books from previous latest grid")
  args = ap.parse_args()
  desks = [d.strip().lower() for d in args.desks.split(",") if d.strip()]
  if args.mode in ("boost", "explore", "refine", "fullera", "hybrid", "fillbook", "wr50"):
    desks = [d for d in desks if d == "g23"] or ["g23"]
  if args.mode in _FILL_E21_MODES:
    desks = [d for d in desks if d == "e21"] or ["e21"]
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
