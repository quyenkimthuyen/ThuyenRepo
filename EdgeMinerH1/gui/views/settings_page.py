"""Cài đặt — profile cấu hình mặc định cho grid search & học."""
from __future__ import annotations

from datetime import date

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from gui.app_settings import (
  add_learning_era,
  format_settings_summary,
  get_learning_era_catalog,
  get_settings,
  remove_learning_era,
  settings_changed_since_last_grid,
  settings_grid_signature,
  update_settings,
)
from gui.glossary import HELP
from gui.page_chrome import render_page_header

SETTING_WIDGET_KEYS = (
  "settings_train_months",
  "settings_era_labels",
  "settings_learning_loops",
  "settings_backtest_from",
  "settings_backtest_to",
  "settings_spread",
  "settings_slip",
  "settings_objective",
  "settings_new_era_label",
  "settings_new_era_from",
  "settings_new_era_until",
  "settings_remove_era_label",
)


def _date_value(value: str, fallback: str) -> date:
  try:
    return date.fromisoformat(str(value)[:10])
  except ValueError:
    return date.fromisoformat(fallback)


def _era_option(era: dict) -> str:
  return f"{era['label']} ({era['learn_from']} → {era['learn_until']})"


def _init_widget_state(settings: dict, era_options: list[str], option_to_key: dict[str, str]) -> None:
  defaults = {
    "settings_train_months": [
      t for t in settings.get("strategy_train_months", [3, 6, 9])
      if t in (3, 6, 9)
    ],
    "settings_era_labels": [
      opt for opt in era_options
      if option_to_key.get(opt) in (settings.get("learning_era_keys") or [])
    ],
    "settings_learning_loops": int(settings.get("learning_loops") or 4),
    "settings_backtest_from": _date_value(settings.get("backtest_from", ""), "2025-01-01"),
    "settings_backtest_to": _date_value(settings.get("backtest_to", ""), "2026-12-31"),
    "settings_spread": float(settings.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "settings_slip": float(settings.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "settings_objective": settings.get("grid_objective", "total_r"),
    "settings_new_era_label": "",
    "settings_new_era_from": date(2023, 1, 1),
    "settings_new_era_until": date(2025, 12, 31),
  }
  for key, value in defaults.items():
    st.session_state.setdefault(key, value)
  selected = st.session_state.get("settings_era_labels") or []
  st.session_state["settings_era_labels"] = [opt for opt in selected if opt in option_to_key]


def _render_era_catalog(settings: dict) -> list[dict]:
  catalog = get_learning_era_catalog(settings)
  if catalog:
    rows = [
      {
        "Tên": e["label"],
        "Từ": e["learn_from"],
        "Đến": e["learn_until"],
        "KB": e["kb_profile"],
        "Bật": "✓" if e["key"] in (settings.get("learning_era_keys") or []) else "",
      }
      for e in catalog
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
  return catalog


def render(embedded: bool = False):
  embedded = embedded or bool(st.session_state.get("_learning_hub"))
  if not embedded:
    from gui.navigation import ALL_ITEMS
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

  catalog = get_learning_era_catalog(s)
  era_options = [_era_option(e) for e in catalog]
  option_to_key = {_era_option(e): e["key"] for e in catalog}
  _init_widget_state(s, era_options, option_to_key)

  st.markdown("#### Chiến lược")
  train_months = st.multiselect(
    "Cửa sổ học chiến lược (tháng)",
    [3, 6, 9],
    key="settings_train_months",
    help=HELP["train_months"],
  )

  st.markdown("#### Học bộ nhớ")
  st.caption("Giai đoạn học lưu trong Cài đặt — có thể thêm/bớt, không hard-code.")
  _render_era_catalog(s)

  picked_eras = st.multiselect(
    "Giai đoạn đang dùng (bật cho học / grid)",
    era_options,
    key="settings_era_labels",
    help="Mỗi giai đoạn = một profile bộ nhớ — grid sẽ thử mọi combo train × giai đoạn × vòng học.",
  )

  with st.expander("Thêm giai đoạn học", expanded=False):
    new_label = st.text_input(
      "Tên giai đoạn",
      key="settings_new_era_label",
      placeholder="vd. 2022–2024",
    )
    c_add1, c_add2 = st.columns(2)
    with c_add1:
      new_from = st.date_input("Học từ", key="settings_new_era_from")
    with c_add2:
      new_until = st.date_input("Học đến", key="settings_new_era_until")
    if st.button("＋ Thêm giai đoạn", key="settings_add_era", type="primary"):
      try:
        if not str(new_label or "").strip():
          raise ValueError("Nhập tên giai đoạn.")
        if new_from > new_until:
          raise ValueError("Ngày bắt đầu phải trước ngày kết thúc.")
        add_learning_era(
          label=str(new_label).strip(),
          learn_from=new_from.isoformat(),
          learn_until=new_until.isoformat(),
          activate=True,
        )
        for key in (
          "settings_era_labels",
          "settings_new_era_label",
          "settings_remove_era_label",
        ):
          st.session_state.pop(key, None)
        st.toast("Đã thêm giai đoạn học")
        st.rerun()
      except ValueError as exc:
        st.error(str(exc))

  if len(catalog) > 1:
    remove_opt = st.selectbox(
      "Xóa giai đoạn khỏi danh sách",
      era_options,
      key="settings_remove_era_label",
    )
    if st.button("Xóa giai đoạn đã chọn", key="settings_remove_era"):
      try:
        key = option_to_key.get(remove_opt)
        if not key:
          raise ValueError("Không tìm thấy giai đoạn.")
        remove_learning_era(key)
        for k in ("settings_era_labels", "settings_remove_era_label"):
          st.session_state.pop(k, None)
        st.toast("Đã xóa giai đoạn học")
        st.rerun()
      except ValueError as exc:
        st.error(str(exc))
  else:
    st.caption("Giữ ít nhất một giai đoạn — thêm giai đoạn mới trước khi xóa.")

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
  if not train_months:
    st.warning("Chọn ít nhất một cửa sổ học chiến lược; thay đổi này chưa được lưu.")
    valid = False
  if not picked_eras:
    st.warning("Chọn ít nhất một giai đoạn học; thay đổi này chưa được lưu.")
    valid = False
  if backtest_from > backtest_to:
    st.warning("Ngày bắt đầu phải trước ngày kết thúc; thay đổi này chưa được lưu.")
    valid = False

  current = {
    "strategy_train_months": list(train_months),
    "learning_era_keys": [option_to_key[opt] for opt in picked_eras if opt in option_to_key],
    "learning_loops": int(learning_loops),
    "backtest_from": backtest_from.isoformat(),
    "backtest_to": backtest_to.isoformat(),
    "spread_pips": float(spread),
    "slippage_pips": float(slip),
    "grid_objective": objective,
  }
  changed = any(s.get(key) != value for key, value in current.items())
  if valid and changed:
    update_settings(**current)
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
