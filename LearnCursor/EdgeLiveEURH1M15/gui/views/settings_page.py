"""Cài đặt — TF-aware profile cho Grid Search & học (H1 tháng / M15 tuần)."""
from __future__ import annotations

from datetime import date

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS, get_active_tf
from gui.app_settings import (
  TRAIN_OPTIONS,
  default_settings_for,
  format_settings_summary,
  get_settings,
  learning_era_options,
  settings_changed_since_last_grid,
  settings_grid_signature,
  train_field_name,
  train_unit_for,
  update_settings,
)
from gui.glossary import HELP
from gui.page_chrome import render_page_header

SETTING_WIDGET_KEYS = (
  "settings_train_weeks",
  "settings_train_months",
  "settings_era_labels",
  "settings_learning_loops",
  "settings_backtest_from",
  "settings_backtest_to",
  "settings_spread",
  "settings_slip",
  "settings_objective",
  "settings_tf_bound",
)


def _date_value(value: str, fallback: str) -> date:
  try:
    return date.fromisoformat(str(value)[:10])
  except ValueError:
    return date.fromisoformat(fallback)


def _clear_settings_widgets() -> None:
  for key in SETTING_WIDGET_KEYS:
    st.session_state.pop(key, None)


def _init_widget_state(settings: dict, era_labels: list[str], eras: list[dict]) -> None:
  tf = get_active_tf()
  if st.session_state.get("settings_tf_bound") != tf:
    _clear_settings_widgets()
    st.session_state["settings_tf_bound"] = tf

  era_by_label = {e["label"]: e["key"] for e in eras}
  unit = train_unit_for()
  field = train_field_name()
  defaults_tf = default_settings_for()
  train_key = "settings_train_months" if unit == "months" else "settings_train_weeks"
  defaults = {
    train_key: [
      t for t in settings.get(field, [3, 6, 9])
      if t in TRAIN_OPTIONS
    ],
    "settings_era_labels": [
      label for label in era_labels
      if era_by_label.get(label) in (settings.get("learning_era_keys") or [])
    ],
    "settings_learning_loops": int(settings.get("learning_loops") or 4),
    "settings_backtest_from": _date_value(
      settings.get("backtest_from", ""), defaults_tf["backtest_from"],
    ),
    "settings_backtest_to": _date_value(
      settings.get("backtest_to", ""), defaults_tf["backtest_to"],
    ),
    "settings_spread": float(settings.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "settings_slip": float(settings.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "settings_objective": settings.get(
      "grid_objective", defaults_tf.get("grid_objective", "total_r"),
    ),
  }
  for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def render(embedded: bool = False):
  embedded = embedded or bool(st.session_state.get("_learning_hub"))
  if not embedded:
    from gui.navigation import ALL_ITEMS
    item = ALL_ITEMS.get("learning")
    if item:
      render_page_header(item, show_profile=False)
    st.caption("Cài đặt nằm trong **Học & tối ưu → ① Cài đặt**.")

  tf = get_active_tf()
  unit = train_unit_for()
  field = train_field_name()
  eras = learning_era_options()
  s = get_settings()

  st.markdown(
    f"Cấu hình **{_tf_label(tf)}** cho Grid Search và huấn luyện. "
    "Đổi timeframe trên sidebar để cấu hình TF kia. "
    "Khi đổi cài đặt, chạy lại **③ Grid Search**."
  )

  if settings_changed_since_last_grid():
    st.warning(
      "⚠️ Cài đặt đã thay đổi so với lần Grid Search gần nhất — "
      "mở tab **③ Grid Search** để cập nhật."
    )

  st.info(format_settings_summary(s))

  era_labels = [e["label"] for e in eras]
  era_keys = {e["label"]: e["key"] for e in eras}
  _init_widget_state(s, era_labels, eras)

  st.markdown("#### Chiến lược")
  if unit == "months":
    trains = st.multiselect(
      "Cửa sổ học chiến lược (tháng)",
      TRAIN_OPTIONS,
      key="settings_train_months",
      help=HELP.get("train_months") or HELP.get("train_weeks"),
    )
  else:
    trains = st.multiselect(
      "Cửa sổ học chiến lược (tuần)",
      TRAIN_OPTIONS,
      key="settings_train_weeks",
      help=HELP.get("train_weeks"),
    )

  st.markdown("#### Học bộ nhớ")
  picked_eras = st.multiselect(
    "Giai đoạn học",
    era_labels,
    key="settings_era_labels",
    help="Mỗi giai đoạn = một profile bộ nhớ — grid thử combo train × giai đoạn × vòng học.",
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

  defaults_tf = default_settings_for()
  objective = st.selectbox(
    "Mục tiêu Grid Search",
    ["total_r", "win_rate_pct", "profit_factor", "risk_adjusted"],
    key="settings_objective",
  )

  valid = True
  if not trains:
    st.warning("Chọn ít nhất một cửa sổ học chiến lược; thay đổi này chưa được lưu.")
    valid = False
  if not picked_eras:
    st.warning("Chọn ít nhất một giai đoạn học; thay đổi này chưa được lưu.")
    valid = False
  if backtest_from > backtest_to:
    st.warning("Ngày bắt đầu phải trước ngày kết thúc; thay đổi này chưa được lưu.")
    valid = False

  current = {
    field: list(trains),
    "learning_era_keys": [era_keys[label] for label in picked_eras],
    "learning_loops": int(learning_loops),
    "backtest_from": backtest_from.isoformat(),
    "backtest_to": backtest_to.isoformat(),
    "spread_pips": float(spread),
    "slippage_pips": float(slip),
    "grid_objective": objective,
  }
  # Drop the other train field so sanitize stays clean
  other = "strategy_train_weeks" if field == "strategy_train_months" else "strategy_train_months"
  current[other] = None

  changed = any(s.get(key) != value for key, value in current.items() if value is not None)
  if valid and changed:
    update_settings(**current)
    st.caption("Đã tự động lưu. Chạy Grid Search lại để áp dụng cấu hình mới.")

  st.divider()
  st.caption(
    f"TF `{tf}` · Chữ ký grid: `{settings_grid_signature()}` · "
    f"Cập nhật: {s.get('updated_at') or '—'} · mặc định obj `{defaults_tf.get('grid_objective')}`"
  )


def _tf_label(tf: str) -> str:
  return f"**{tf}** ({'tháng' if train_unit_for(tf) == 'months' else 'tuần'})"
