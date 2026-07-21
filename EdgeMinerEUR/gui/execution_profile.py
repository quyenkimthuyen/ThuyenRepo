"""Profile thực thi đã chốt + tóm tắt A/B — hiển thị trong Phân tích."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from config import (
  DEFAULT_MAX_HOLD_BARS,
  DEFAULT_MIN_BARS_BETWEEN,
  DEFAULT_TRAIL_ACTIVATE_R,
  DEFAULT_TRAIL_DISTANCE_R,
)
from run_backtest import REPORT_DIR

AB_FILES = {
  "reopt": ("Reopt tuần vs tháng", REPORT_DIR / "reopt_compare.json"),
  "quota": ("Quota 2/tuần vs 1/ngày", REPORT_DIR / "trade_quota_compare.json"),
  "max_hold": ("Max hold 24/36/48", REPORT_DIR / "max_hold_compare.json"),
  "exec": ("Gap & trail hybrid", REPORT_DIR / "exec_params_compare.json"),
}


def locked_execution_defaults() -> dict:
  return {
    "max_hold_bars": DEFAULT_MAX_HOLD_BARS,
    "min_bars_between": DEFAULT_MIN_BARS_BETWEEN,
    "trail_activate_r": DEFAULT_TRAIL_ACTIVATE_R,
    "trail_distance_r": DEFAULT_TRAIL_DISTANCE_R,
    "max_trades_per_week": 2,
    "reopt_period": "week",
  }


def resolve_execution_config(report: dict | None) -> dict:
  """Gộp default đã lock + override trong báo cáo (nếu có)."""
  base = locked_execution_defaults()
  if not report:
    return base
  cfg = report.get("config") or {}
  trail = cfg.get("trail_hybrid")
  if trail and len(trail) >= 2:
    base["trail_activate_r"] = float(trail[0])
    base["trail_distance_r"] = float(trail[1])
  elif cfg.get("trail_activate_r") is not None:
    base["trail_activate_r"] = float(cfg["trail_activate_r"])
    base["trail_distance_r"] = float(cfg.get("trail_distance_r", DEFAULT_TRAIL_DISTANCE_R))
  if cfg.get("max_hold_bars") is not None:
    base["max_hold_bars"] = int(cfg["max_hold_bars"])
  if cfg.get("min_bars_between") is not None:
    base["min_bars_between"] = int(cfg["min_bars_between"])
  if cfg.get("target_trades_per_week") is not None:
    base["max_trades_per_week"] = int(cfg["target_trades_per_week"])
  if cfg.get("reopt_period"):
    base["reopt_period"] = str(cfg["reopt_period"])
  return base


def load_ab_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def render_execution_profile_panel(report: dict | None = None, *, expanded: bool = False):
  """Thẻ cấu hình thực thi — defaults đã chốt sau A/B."""
  ex = resolve_execution_config(report)
  cfg = (report or {}).get("config") or {}
  reopt = "tuần" if ex["reopt_period"] == "week" else "tháng"

  with st.expander("⚙️ Cấu hình thực thi (đã chốt)", expanded=expanded):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Reopt", reopt)
    c2.metric("Max hold", f"{ex['max_hold_bars']} bars")
    c3.metric("Gap lệnh", f"{ex['min_bars_between']} bars")
    c4.metric("Quota", f"{ex['max_trades_per_week']}/tuần")
    st.caption(
      f"Trail hybrid: **act {ex['trail_activate_r']}R** / **dist {ex['trail_distance_r']}R** · "
      f"Phí: spread **{cfg.get('spread_pips', 1.0)}** / slip **{cfg.get('slippage_pips', 0.3)}** pip"
    )
    if report:
      st.caption(
        f"Train **{cfg.get('train_months', '?')}T** · "
        f"KB **{'ON' if cfg.get('use_learning_kb') else 'OFF'}** "
        f"({cfg.get('kb_profile') or '—'}, {cfg.get('kb_snapshot', 'latest')}) · "
        f"OOS **{cfg.get('oos_from', '?')} → {cfg.get('oos_to', '?')}**"
      )
    st.caption("Chi tiết: `PARAMS.md` · Miner vẫn thử grid nội (hold/gap/exit) mỗi tuần.")


def render_ab_study_summary():
  """Tóm tắt kết quả A/B hôm nay (nếu có file JSON)."""
  rows = []
  data_exec = load_ab_json(AB_FILES["exec"][1])
  data_hold = load_ab_json(AB_FILES["max_hold"][1])
  data_reopt = load_ab_json(AB_FILES["reopt"][1])
  data_quota = load_ab_json(AB_FILES["quota"][1])

  if data_reopt:
    rows.append(("Reopt", data_reopt.get("winner", "week"), "Giữ weekly"))
  if data_quota:
    rows.append(("Quota", data_quota.get("winner", "2/week"), "Giữ 2 lệnh/tuần"))
  if data_hold:
    w = data_hold.get("winner") or data_hold.get("summary", {}).get("winner")
    rows.append(("Max hold", f"{w} bars" if w else "24", "Chọn ổn định → 24"))
  if data_exec:
    mb = data_exec.get("min_bars_winner", "gap=4")
    tr = data_exec.get("trail_winner", "act=1.0/dist=0.5")
    rows.append(("Min bars", mb, "Lock gap=4"))
    rows.append(("Trail", tr, "Lock 1.0/0.5 (ổn định)"))

  if not rows:
    return

  with st.expander("📊 A/B đã chạy (hôm nay)", expanded=False):
    for name, winner, note in rows:
      st.markdown(f"- **{name}**: `{winner}` — _{note}_")
    st.caption("File: `results/*_compare.json` · `results/exec_params_compare.json`")
