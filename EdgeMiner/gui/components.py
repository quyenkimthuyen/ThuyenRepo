"""Shared Streamlit UI components."""
from __future__ import annotations

import streamlit as st


def kpi_row(items: list[tuple[str, str, str | None]]):
  """Render KPI metrics row. items: (label, value, delta_or_hint)."""
  cols = st.columns(len(items))
  for col, (label, value, hint) in zip(cols, items):
    col.metric(label, value, hint if hint and hint.startswith(("+", "-")) else None)
    if hint and not hint.startswith(("+", "-")):
      col.caption(hint)


def constraint_checklist(constraints: dict, labels: dict[str, str] | None = None):
  default_labels = {
    "profitable": "Profitable (1Y)",
    "win_rate_above_60": "Win Rate > 60% (1Y)",
    "rr_above_2": "RR > 2 (1Y)",
    "trades_per_week_near_2": "~2 lệnh/tuần",
  }
  labels = labels or default_labels
  for key, label in labels.items():
    ok = constraints.get(key, False)
    icon = "✅" if ok else "❌"
    st.markdown(f"{icon} **{label}**")


def status_banner(report: dict | None, kb: dict, data_meta: dict):
  if report:
    dr = report.get("data_range", {})
    cfg = report.get("config", {})
    st.caption(
      f"Data: **{dr.get('start', '?')} → {dr.get('end', '?')}** "
      f"({dr.get('bars', '?')} bars) · "
      f"KB: **{kb.get('genomes', 0)}** genomes, **{kb.get('rules', 0)}** rules · "
      f"Last fetch: {data_meta.get('fetched_at', 'n/a')[:10] if data_meta.get('fetched_at') else 'n/a'} · "
      f"Backtest KB: **{'ON' if cfg.get('use_learning_kb') else 'OFF'}**"
    )
  else:
    st.info("Chưa có báo cáo backtest. Chạy Backtest Lab hoặc Command Center.")


def warn_long_bias(pct_long: float):
  if pct_long >= 85:
    st.warning(
      f"⚠️ **LONG bias {pct_long:.0f}%** — strategy có thể chỉ hoạt động khi EUR/USD tăng. "
      "Kiểm tra kỹ trước khi live."
    )


def warn_kb_leak(use_kb: bool):
  if use_kb:
    st.warning(
      "⚠️ **Knowledge Base ON** — backtest có thể bị ảnh hưởng bởi kinh nghiệm từ các epoch trước "
      "(meta-overfit). Tắt KB để đánh giá walk-forward thuần."
    )


def warn_no_costs():
  st.caption(
    "ℹ️ Chi phí giao dịch: chỉnh **Spread/Slippage** trong Backtest Lab (mặc định 1.0 / 0.3 pip)."
  )
