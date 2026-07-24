"""Helpers cho trang Phân tích — báo cáo khớp Trade Model."""
from __future__ import annotations

import streamlit as st

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
      "use_learning": bool(p.get("use_kb", True)),
      "train_weeks": int(p.get("train_weeks") or 6),
      "spread_pips": float(p.get("spread_pips", 1.0)),
      "slippage_pips": float(p.get("slippage_pips", 0.3)),
      "kb_profile": p.get("kb_profile"),
      "kb_snapshot": p.get("kb_snapshot"),
      "oos_from": p.get("oos_from"),
      "oos_to": p.get("oos_to"),
      "holdout_months": 0,
      "archive": True,
      "archive_label": f"TM {format_model_label(m)[:48]}",
    },
    label=f"Báo cáo Phân tích · {format_model_label(m)[:40]}",
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
