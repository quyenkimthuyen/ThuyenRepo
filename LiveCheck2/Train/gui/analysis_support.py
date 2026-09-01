"""Helpers cho trang Phân tích — báo cáo khớp Trade Model."""
from __future__ import annotations

from config import DEFAULT_FEATURE_PROFILE, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS

import streamlit as st

from gui.navigation import LABEL_TAB_OOS
from gui.services import load_backtest_report
from gui.trade_model import (
  format_model_label,
  get_active_trade_model,
  get_model_run_params,
  load_model_report,
  set_active_trade_model,
)
from gui.workspace import report_matches_workspace


def get_matching_analysis_report() -> dict | None:
  """Chỉ trả báo cáo khớp Trade Model đang chọn (không fallback backtest lệch)."""
  m = get_active_trade_model()
  if m and m.get("id"):
    rep = load_model_report(m["id"])
    if rep:
      return rep
  report = load_backtest_report(workspace_aware=True)
  if report and report_matches_workspace(report):
    return report
  return None


def start_model_report_job(model: dict | None = None) -> str:
  """Chạy backtest đầy đủ cho model → lưu report phân tích."""
  from gui.long_task_background import start_job

  m = model or get_active_trade_model()
  if not m:
    raise ValueError("Chưa có trade model.")
  set_active_trade_model(m["id"])
  p = get_model_run_params(m)
  return start_job(
    "backtest",
    {
      "model_id": m["id"],
      "use_learning": bool(p.get("use_kb", True)),
      "train_weeks": int(p.get("train_weeks") or 6),
      "spread_pips": float(p.get("spread_pips", DEFAULT_SPREAD_PIPS)),
      "slippage_pips": float(p.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
      "kb_profile": p.get("kb_profile"),
      "kb_snapshot": p.get("kb_snapshot"),
      "oos_from": p.get("oos_from"),
      "oos_to": p.get("oos_to"),
      "feature_profile": p.get("feature_profile") or DEFAULT_FEATURE_PROFILE,
      "mining_search_space": p.get("mining_search_space"),
      "holdout_months": 0,
      "archive": True,
      "archive_label": f"TM {format_model_label(m)[:48]}",
    },
    label=f"Báo cáo Phân tích · {format_model_label(m)[:40]}",
  )


def start_model_health_job(
  model: dict | None = None,
  *,
  refresh_kb_on: bool = True,
  start_date: str = "2022-01-01",
) -> str:
  """Chạy KB ON (+optional) và KB OFF cùng OOS → biểu đồ sức khỏe theo tháng."""
  from gui.long_task_background import start_job

  m = model or get_active_trade_model()
  if not m:
    raise ValueError("Chưa có trade model.")
  set_active_trade_model(m["id"])
  p = get_model_run_params(m)
  return start_job(
    "model_health",
    {
      "model_id": m["id"],
      "refresh_kb_on": refresh_kb_on,
      "start_date": start_date,
      "train_weeks": int(p.get("train_weeks") or 6),
      "spread_pips": float(p.get("spread_pips", DEFAULT_SPREAD_PIPS)),
      "slippage_pips": float(p.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
      "kb_profile": p.get("kb_profile"),
      "kb_snapshot": p.get("kb_snapshot"),
      "oos_from": p.get("oos_from"),
      "oos_to": p.get("oos_to"),
      "feature_profile": p.get("feature_profile") or DEFAULT_FEATURE_PROFILE,
      "mining_search_space": p.get("mining_search_space"),
    },
    label=f"{LABEL_TAB_OOS} · {format_model_label(m)[:40]}",
  )


def start_mining_space_health_job(
  model: dict | None = None,
  *,
  refresh_active: bool = False,
  start_date: str = "2022-01-01",
) -> str:
  """A/B mining space: active model space vs baseline miner (cùng KB/train/OOS)."""
  from gui.long_task_background import start_job

  m = model or get_active_trade_model()
  if not m:
    raise ValueError("Chưa có trade model.")
  set_active_trade_model(m["id"])
  p = get_model_run_params(m)
  return start_job(
    "mining_space_health",
    {
      "model_id": m["id"],
      "refresh_active": refresh_active,
      "start_date": start_date,
      "train_weeks": int(p.get("train_weeks") or 6),
      "spread_pips": float(p.get("spread_pips", DEFAULT_SPREAD_PIPS)),
      "slippage_pips": float(p.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
      "kb_profile": p.get("kb_profile"),
      "kb_snapshot": p.get("kb_snapshot"),
      "oos_from": p.get("oos_from"),
      "oos_to": p.get("oos_to"),
      "feature_profile": p.get("feature_profile") or DEFAULT_FEATURE_PROFILE,
      "mining_search_space": p.get("mining_search_space"),
    },
    label=f"Mining space vs baseline · {format_model_label(m)[:36]}",
  )


def start_remine_health_job(
  model: dict | None = None,
  *,
  refresh_remine_on: bool = False,
  start_date: str = "2022-01-01",
) -> str:
  """Remine ON (weekly) vs Remine OFF (freeze first-week strategy), same KB/OOS."""
  from gui.long_task_background import start_job

  m = model or get_active_trade_model()
  if not m:
    raise ValueError("Chưa có trade model.")
  set_active_trade_model(m["id"])
  p = get_model_run_params(m)
  return start_job(
    "remine_health",
    {
      "model_id": m["id"],
      "refresh_remine_on": refresh_remine_on,
      "start_date": start_date,
      "train_weeks": int(p.get("train_weeks") or 6),
      "spread_pips": float(p.get("spread_pips", DEFAULT_SPREAD_PIPS)),
      "slippage_pips": float(p.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
      "kb_profile": p.get("kb_profile"),
      "kb_snapshot": p.get("kb_snapshot"),
      "oos_from": p.get("oos_from"),
      "oos_to": p.get("oos_to"),
      "feature_profile": p.get("feature_profile") or DEFAULT_FEATURE_PROFILE,
      "mining_search_space": p.get("mining_search_space"),
    },
    label=f"Remine ON/OFF · {format_model_label(m)[:40]}",
  )


def list_missing_model_health_checks(model: dict | None = None) -> list[dict]:
  """Checks còn thiếu cho Trade Model (Health / Remine / Mining space).

  Mỗi phần tử: ``{key, label, reason, refresh_*}``.
  """
  from gui.trade_model import (
    load_model_kb_off_report,
    load_model_mining_baseline_report,
    load_model_remine_off_report,
    load_model_report,
    report_search_space_matches_model,
  )
  from mining_presets import match_preset_name

  m = model or get_active_trade_model()
  if not m or not m.get("id"):
    return []

  mid = str(m["id"])
  report_on = load_model_report(mid)
  report_off = load_model_kb_off_report(mid)
  remine_off = load_model_remine_off_report(mid)
  space_ok = report_search_space_matches_model(report_on, m) if report_on else False
  missing: list[dict] = []

  need_health = (not report_on) or (not space_ok) or (not report_off)
  if need_health:
    reasons = []
    if not report_on:
      reasons.append("chưa có report KB ON")
    elif not space_ok:
      reasons.append("report lệch mining space")
    if not report_off:
      reasons.append("chưa có KB OFF")
    missing.append({
      "key": "model_health",
      "label": "KB ON / OFF",
      "reason": " · ".join(reasons),
      "refresh_kb_on": (not report_on) or (not space_ok),
    })

  if not remine_off:
    missing.append({
      "key": "remine_health",
      "label": "Remine ON / OFF",
      "reason": "chưa có baseline Remine OFF",
      "refresh_remine_on": not bool(report_on and space_ok),
    })

  ss = m.get("mining_search_space") or {}
  preset = match_preset_name(ss) if ss else None
  if ss and preset and preset != "baseline":
    base_rep = load_model_mining_baseline_report(mid)
    if not base_rep:
      missing.append({
        "key": "mining_space_health",
        "label": "Mining space vs baseline",
        "reason": f"preset `{preset}` chưa so baseline",
        "refresh_active": not bool(report_on and space_ok),
      })

  return missing


def start_missing_model_checks_job(
  model: dict | None = None,
  *,
  start_date: str = "2022-01-01",
) -> str:
  """Một nút: chạy lần lượt mọi check Health còn thiếu của model."""
  from gui.long_task_background import start_job

  m = model or get_active_trade_model()
  if not m:
    raise ValueError("Chưa có trade model.")
  missing = list_missing_model_health_checks(m)
  if not missing:
    raise ValueError(f"Model đã đủ check {LABEL_TAB_OOS} — không cần chạy thêm.")

  set_active_trade_model(m["id"])
  p = get_model_run_params(m)
  steps = [row["key"] for row in missing]
  refresh_kb_on = True
  refresh_remine_on = False
  refresh_active = False
  for row in missing:
    if row["key"] == "model_health":
      refresh_kb_on = bool(row.get("refresh_kb_on", True))
    elif row["key"] == "remine_health":
      # After health step in same suite, ON report will exist — only refresh if
      # health is not also in this suite and ON is still missing.
      refresh_remine_on = bool(row.get("refresh_remine_on", False)) and (
        "model_health" not in steps
      )
    elif row["key"] == "mining_space_health":
      refresh_active = bool(row.get("refresh_active", False)) and (
        "model_health" not in steps
      )

  labels = " → ".join(row["label"] for row in missing)
  return start_job(
    "model_checks_suite",
    {
      "model_id": m["id"],
      "steps": steps,
      "start_date": start_date,
      "refresh_kb_on": refresh_kb_on,
      "refresh_remine_on": refresh_remine_on,
      "refresh_active": refresh_active,
      "train_weeks": int(p.get("train_weeks") or 6),
      "spread_pips": float(p.get("spread_pips", DEFAULT_SPREAD_PIPS)),
      "slippage_pips": float(p.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
      "kb_profile": p.get("kb_profile"),
      "kb_snapshot": p.get("kb_snapshot"),
      "oos_from": p.get("oos_from"),
      "oos_to": p.get("oos_to"),
      "feature_profile": p.get("feature_profile") or DEFAULT_FEATURE_PROFILE,
      "mining_search_space": p.get("mining_search_space"),
    },
    label=f"Check thiếu · {format_model_label(m)[:28]} · {labels}"[:80],
  )


def render_report_required_panel(*, key_prefix: str = "an_rep") -> bool:
  """
  Hiển thị khi chưa có báo cáo khớp model.
  Trả True nếu đã chặn (caller nên return).
  """
  from gui.long_task_background import is_task_running
  from gui.long_task_ui import render_task_status

  if get_matching_analysis_report():
    return False

  m = get_active_trade_model()
  if not m:
    st.info("Chọn **Trade Model** để xem phân tích.")
    return True

  st.info(
    "Trade Model này mới có **chỉ số từ Grid Search** — chưa có báo cáo đầy đủ "
    "(danh sách lệnh / equity) để Risk & Nhật ký."
  )

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Total R (Grid)", f"{float(m.get('total_r') or 0):+.2f}")
  c2.metric("WR%", f"{m.get('win_rate_pct', '—')}%")
  c3.metric("Max DD", f"{m.get('max_drawdown_r', '—')}R")
  c4.metric("Lệnh", f"{m.get('n_trades', '—')}")

  render_task_status(key_prefix=key_prefix, compact=True)

  if is_task_running():
    st.caption("Đang tạo báo cáo nền — có thể chuyển trang, quay lại khi xong.")
    return True

  if st.button(
    "▶ Tạo báo cáo phân tích (chạy backtest đầy đủ)",
    type="primary",
    key=f"{key_prefix}_start",
    use_container_width=True,
  ):
    try:
      start_model_report_job(m)
      st.toast("Đã bắt đầu tạo báo cáo nền")
      st.rerun()
    except Exception as e:
      st.error(str(e))

  st.caption(
    "Lần tạo model từ Grid chỉ lưu KPI tổng hợp. "
    "Báo cáo đầy đủ cần chạy lại walk-forward một lần với đúng tham số model."
  )
  return True
