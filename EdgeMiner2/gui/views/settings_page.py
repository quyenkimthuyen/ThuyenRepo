"""Cài đặt — profile cấu hình mặc định cho grid search & học."""
from __future__ import annotations

from datetime import date

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from gui.app_settings import (
  LEARNING_ERA_OPTIONS,
  format_settings_summary,
  get_settings,
  settings_changed_since_last_grid,
  settings_grid_signature,
  update_settings,
)
from gui.glossary import HELP
from gui.page_chrome import render_page_header

SETTING_WIDGET_KEYS = (
  "settings_train_weeks",
  "settings_era_labels",
  "settings_learning_loops",
  "settings_backtest_from",
  "settings_backtest_to",
  "settings_spread",
  "settings_slip",
  "settings_objective",
)


def _date_value(value: str, fallback: str) -> date:
  try:
    return date.fromisoformat(str(value)[:10])
  except ValueError:
    return date.fromisoformat(fallback)


def _init_widget_state(settings: dict, era_labels: list[str]) -> None:
  era_by_label = {e["label"]: e["key"] for e in LEARNING_ERA_OPTIONS}
  defaults = {
    "settings_train_weeks": [
      t for t in settings.get("strategy_train_weeks", [3, 6, 9])
      if t in (3, 6, 9)
    ],
    "settings_era_labels": [
      label for label in era_labels
      if era_by_label[label] in (settings.get("learning_era_keys") or [])
    ],
    "settings_learning_loops": int(settings.get("learning_loops") or 4),
    "settings_backtest_from": _date_value(settings.get("backtest_from", ""), "2026-01-01"),
    "settings_backtest_to": _date_value(settings.get("backtest_to", ""), "2026-12-31"),
    "settings_spread": float(settings.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "settings_slip": float(settings.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "settings_objective": settings.get("grid_objective", "risk_adjusted"),
  }
  for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def render(embedded: bool = False):
  embedded = embedded or bool(st.session_state.get("_learning_hub"))
  if not embedded:
    from gui.navigation import ALL_ITEMS
    # Fallback if opened outside hub (legacy links)
    item = ALL_ITEMS.get("learning")
    if item:
      render_page_header(item, show_profile=False)
    st.caption("Cài đặt nằm trong **Học & tối ưu → ① Cài đặt**.")

  s = get_settings()

  st.markdown(
    "Cấu hình **mặc định** cho Grid Search và huấn luyện. "
    "Khi đổi cài đặt, chạy lại **③ Grid Search** — chỉ combo mới được tính."
  )

  if settings_changed_since_last_grid():
    st.warning(
      "⚠️ Cài đặt đã thay đổi so với lần Grid Search gần nhất — "
      "mở tab **③ Grid Search** để cập nhật."
    )

  st.info(format_settings_summary(s))

  era_labels = [e["label"] for e in LEARNING_ERA_OPTIONS]
  era_keys = {e["label"]: e["key"] for e in LEARNING_ERA_OPTIONS}
  _init_widget_state(s, era_labels)

  st.markdown("#### Chiến lược")
  train_weeks = st.multiselect(
    "Cửa sổ học chiến lược (tuần)",
    [3, 6, 9],
    key="settings_train_weeks",
    help=HELP["train_weeks"],
  )

  st.markdown("#### Học bộ nhớ")
  picked_eras = st.multiselect(
    "Giai đoạn học",
    era_labels,
    key="settings_era_labels",
    help="Mỗi giai đoạn = một profile bộ nhớ — grid sẽ thử mọi combo train × giai đoạn × vòng học.",
  )
  learning_loops = st.number_input(
    "Số vòng học (epoch)",
    min_value=1,
    max_value=12,
    key="settings_learning_loops",
    help=HELP["epoch"],
  )

  st.markdown("#### Kiểm chứng")
  c1, c2 = st.columns(2)
  with c1:
    backtest_from = st.date_input("Từ", key="settings_backtest_from", help=HELP["oos"])
  with c2:
    backtest_to = st.date_input("Đến", key="settings_backtest_to", help=HELP["oos"])

  st.markdown("#### Phí mô phỏng")
  c3, c4 = st.columns(2)
  with c3:
    spread = st.number_input(
      "Chênh lệch (pip)", 0.0, 3.0, step=0.1, key="settings_spread",
    )
  with c4:
    slip = st.number_input(
      "Trượt giá (pip)", 0.0, 2.0, step=0.1, key="settings_slip",
    )

  objective = st.selectbox(
    "Mục tiêu Grid Search",
    ["total_r", "win_rate_pct", "profit_factor", "risk_adjusted"],
    key="settings_objective",
  )

  valid = True
  if not train_weeks:
    st.warning("Chọn ít nhất một cửa sổ học chiến lược; thay đổi này chưa được lưu.")
    valid = False
  if not picked_eras:
    st.warning("Chọn ít nhất một giai đoạn học; thay đổi này chưa được lưu.")
    valid = False
  if backtest_from > backtest_to:
    st.warning("Ngày bắt đầu phải trước ngày kết thúc; thay đổi này chưa được lưu.")
    valid = False

  current = {
    "strategy_train_weeks": list(train_weeks),
    "learning_era_keys": [era_keys[label] for label in picked_eras],
    "learning_loops": int(learning_loops),
    "backtest_from": backtest_from.isoformat(),
    "backtest_to": backtest_to.isoformat(),
    "spread_pips": float(spread),
    "slippage_pips": float(slip),
    "grid_objective": objective,
  }
  changed = any(s.get(key) != value for key, value in current.items())
  if valid and changed:
    update_settings(
      **current,
    )
    st.caption("Đã tự động lưu. Chạy Grid Search lại để áp dụng cấu hình mới.")

  st.divider()
  st.caption(
    f"Chữ ký grid: `{settings_grid_signature()}` · "
    f"Cập nhật: {s.get('updated_at') or '—'}"
  )

  if st.button("↺ Khôi phục mặc định", key="settings_reset"):
    from gui.app_settings import DEFAULT_SETTINGS, save_settings
    save_settings(dict(DEFAULT_SETTINGS))
    for key in SETTING_WIDGET_KEYS:
      st.session_state.pop(key, None)
    st.toast("Đã khôi phục cài đặt mặc định")
    st.rerun()
