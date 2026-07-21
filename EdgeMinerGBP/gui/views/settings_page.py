"""Cài đặt — profile cấu hình mặc định cho grid search & học."""
from __future__ import annotations

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
from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header


def render():
  render_page_header(ALL_ITEMS["settings"], show_profile=False)
  s = get_settings()

  st.markdown(
    "Cấu hình **mặc định** cho Grid Search và huấn luyện. "
    "Khi đổi cài đặt, chạy lại Grid Search ở **Học & tối ưu** — chỉ combo mới được tính."
  )

  if settings_changed_since_last_grid():
    st.warning(
      "⚠️ Cài đặt đã thay đổi so với lần Grid Search gần nhất — "
      "mở **Học & tối ưu → Grid Search** để cập nhật."
    )

  st.info(format_settings_summary(s))

  with st.form("settings_form"):
    st.markdown("#### Chiến lược")
    train_opts = [3, 6, 9]
    train_months = st.multiselect(
      "Cửa sổ học chiến lược (tháng)",
      train_opts,
      default=[t for t in s.get("strategy_train_months", [3, 6, 9]) if t in train_opts],
      help=HELP["train_months"],
    )
    reopt_labels = {"Tuần (mặc định)": "week", "Tháng": "month"}
    reopt_pick = st.radio(
      "Tần suất cập nhật chiến lược",
      list(reopt_labels.keys()),
      index=0 if s.get("reopt_period", "week") == "week" else 1,
      horizontal=True,
      help=HELP["reopt_period"],
    )
    reopt_period = reopt_labels[reopt_pick]

    st.markdown("#### Học bộ nhớ")
    era_labels = [e["label"] for e in LEARNING_ERA_OPTIONS]
    era_keys = {e["label"]: e["key"] for e in LEARNING_ERA_OPTIONS}
    default_eras = [
      era_keys[k] for k in era_labels
      if era_keys[k] in (s.get("learning_era_keys") or [])
    ]
    picked_eras = st.multiselect(
      "Giai đoạn học",
      era_labels,
      default=[e["label"] for e in LEARNING_ERA_OPTIONS if e["key"] in default_eras]
      or era_labels,
      help="Mỗi giai đoạn = một profile bộ nhớ — grid sẽ thử mọi combo train × giai đoạn × vòng học.",
    )
    learning_loops = st.number_input(
      "Số vòng học (epoch)",
      min_value=1,
      max_value=12,
      value=int(s.get("learning_loops") or 4),
      help=HELP["epoch"],
    )

    st.markdown("#### Kiểm chứng")
    c1, c2 = st.columns(2)
    with c1:
      backtest_from = st.text_input("Từ", value=s.get("backtest_from", "2025-01-01"), help=HELP["oos"])
    with c2:
      backtest_to = st.text_input("Đến", value=s.get("backtest_to", "2026-12-31"), help=HELP["oos"])

    st.markdown("#### Phí mô phỏng")
    c3, c4 = st.columns(2)
    with c3:
      spread = st.number_input("Chênh lệch (pip)", 0.0, 3.0, float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)), 0.1)
    with c4:
      slip = st.number_input("Trượt giá (pip)", 0.0, 2.0, float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)), 0.1)

    objective = st.selectbox(
      "Mục tiêu Grid Search",
      ["total_r", "win_rate_pct", "profit_factor", "risk_adjusted"],
      index=["total_r", "win_rate_pct", "profit_factor", "risk_adjusted"].index(
        s.get("grid_objective", "total_r")
      ),
    )

    submitted = st.form_submit_button("💾 Lưu cài đặt", type="primary", use_container_width=True)

  if submitted:
    if not train_months:
      st.error("Chọn ít nhất một cửa sổ học chiến lược.")
      return
    if not picked_eras:
      st.error("Chọn ít nhất một giai đoạn học.")
      return
    new_sig = settings_grid_signature({
      **s,
      "strategy_train_months": train_months,
      "learning_era_keys": [era_keys[l] for l in picked_eras],
      "learning_loops": int(learning_loops),
      "backtest_from": backtest_from.strip(),
      "backtest_to": backtest_to.strip(),
      "reopt_period": reopt_period,
    })
    old_sig = settings_grid_signature(s)
    update_settings(
      strategy_train_months=train_months,
      learning_era_keys=[era_keys[l] for l in picked_eras],
      learning_loops=int(learning_loops),
      backtest_from=backtest_from.strip(),
      backtest_to=backtest_to.strip(),
      spread_pips=float(spread),
      slippage_pips=float(slip),
      grid_objective=objective,
      reopt_period=reopt_period,
    )
    st.session_state["settings_grid_signature"] = new_sig
    if new_sig != old_sig:
      st.toast("Đã lưu — chạy Grid Search để cập nhật combo mới")
    else:
      st.toast("Đã lưu cài đặt")
    st.rerun()

  st.divider()
  st.caption(
    f"Chữ ký grid: `{settings_grid_signature()}` · "
    f"Cập nhật: {s.get('updated_at') or '—'}"
  )

  if st.button("↺ Khôi phục mặc định", key="settings_reset"):
    from gui.app_settings import DEFAULT_SETTINGS, save_settings
    save_settings(dict(DEFAULT_SETTINGS))
    st.session_state.pop("app_settings", None)
    st.toast("Đã khôi phục cài đặt mặc định")
    st.rerun()
