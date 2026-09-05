"""Cài đặt — profile cấu hình mặc định cho grid search & học."""
from __future__ import annotations

from datetime import date

import streamlit as st

from gui.app_settings import (
  TRAIN_WEEK_OPTIONS,
  add_learning_era,
  add_oos_window,
  describe_kb_oos_pairs,
  format_settings_summary,
  get_learning_era_catalog,
  get_oos_window_catalog,
  get_settings,
  oos_window_option,
  remove_learning_era,
  remove_oos_window,
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
  "settings_oos_labels",
  "settings_mining_presets",
  "settings_new_era_label",
  "settings_new_era_from",
  "settings_new_era_until",
  "settings_remove_era_label",
  "settings_new_oos_label",
  "settings_new_oos_from",
  "settings_new_oos_until",
  "settings_remove_oos_label",
  "gs_oos_labels",
)


def _era_option(era: dict) -> str:
  return f"{era['label']} ({era['learn_from']} → {era['learn_until']})"


def _init_widget_state(
  settings: dict,
  era_options: list[str],
  option_to_key: dict[str, str],
  oos_options: list[str],
  oos_option_to_key: dict[str, str],
) -> None:
  from mining_presets import (
    list_curated_presets,
    list_presets,
    preset_label,
    recommended_preset,
  )

  known = list_presets()
  label_by_name = {preset_label(n): n for n in known}
  option_names = []
  for name in list(list_curated_presets()) + list(settings.get("mining_presets") or []):
    if name in known and name not in option_names:
      option_names.append(name)
  mining_options = [preset_label(n) for n in option_names]
  saved = list(settings.get("mining_presets") or [recommended_preset()])
  week_opts = set(TRAIN_WEEK_OPTIONS)
  defaults = {
    "settings_train_weeks": [
      t for t in settings.get("strategy_train_weeks", [8, 12])
      if t in week_opts
    ],
    "settings_era_labels": [
      opt for opt in era_options
      if option_to_key.get(opt) in (settings.get("learning_era_keys") or [])
    ],
    "settings_learning_loops": int(settings.get("learning_loops") or 3),
    "settings_oos_labels": [
      opt for opt in oos_options
      if oos_option_to_key.get(opt) in (settings.get("oos_window_keys") or [])
    ],
    "settings_mining_presets": [
      preset_label(n) for n in saved if n in known
    ] or [preset_label(recommended_preset())],
    "settings_new_era_label": "",
    "settings_new_era_from": date(2024, 1, 1),
    "settings_new_era_until": date(2025, 12, 31),
    "settings_new_oos_label": "",
    "settings_new_oos_from": date(2025, 7, 1),
    "settings_new_oos_until": date(2025, 12, 31),
  }
  for key, value in defaults.items():
    st.session_state.setdefault(key, value)
  # Drop stale options if catalog changed (add/remove).
  selected = st.session_state.get("settings_era_labels") or []
  st.session_state["settings_era_labels"] = [opt for opt in selected if opt in option_to_key]
  picked_oos = st.session_state.get("settings_oos_labels") or []
  st.session_state["settings_oos_labels"] = [opt for opt in picked_oos if opt in oos_option_to_key]
  st.session_state["_settings_mining_option_names"] = option_names
  st.session_state["_settings_mining_label_to_name"] = label_by_name
  # Keep multiselect values in the current option set.
  picked = st.session_state.get("settings_mining_presets") or []
  st.session_state["settings_mining_presets"] = [
    opt for opt in picked if opt in mining_options
  ] or [preset_label(recommended_preset())]



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


def _render_oos_catalog(settings: dict) -> list[dict]:
  catalog = get_oos_window_catalog(settings)
  if catalog:
    rows = [
      {
        "Tên": w["label"],
        "Từ": w["oos_from"],
        "Đến": w["oos_to"],
        "Bật": "✓" if w["key"] in (settings.get("oos_window_keys") or []) else "",
      }
      for w in catalog
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
  oos_catalog = get_oos_window_catalog(s)
  oos_options = [oos_window_option(w) for w in oos_catalog]
  oos_option_to_key = {oos_window_option(w): w["key"] for w in oos_catalog}
  _init_widget_state(s, era_options, option_to_key, oos_options, oos_option_to_key)

  st.markdown("#### Chiến lược")
  train_weeks = st.multiselect(
    "Cửa sổ học chiến lược (tuần)",
    TRAIN_WEEK_OPTIONS,
    key="settings_train_weeks",
    help=HELP["train_weeks"],
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
      placeholder="vd. 2024–2025",
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
  st.caption(
    "Catalog cửa sổ OOS — thêm/xóa như giai đoạn học. "
    "Grid Search chỉ chạy các cửa sổ **đang bật**, và **bỏ combo** nếu khoảng học KB "
    "trùng ngày với OOS (kề nhau: học đến 30/6 rồi OOS từ 01/7 — được)."
  )
  _render_oos_catalog(s)
  picked_oos = st.multiselect(
    "Cửa sổ OOS đang dùng (bật cho Grid / pipeline)",
    oos_options,
    key="settings_oos_labels",
    help=HELP["oos"],
  )

  with st.expander("Thêm cửa sổ OOS", expanded=False):
    new_oos_label = st.text_input(
      "Tên cửa sổ",
      key="settings_new_oos_label",
      placeholder="vd. 2025 (6 tháng cuối)",
    )
    c_oos1, c_oos2 = st.columns(2)
    with c_oos1:
      new_oos_from = st.date_input("OOS từ", key="settings_new_oos_from")
    with c_oos2:
      new_oos_until = st.date_input("OOS đến", key="settings_new_oos_until")
    if st.button("＋ Thêm cửa sổ OOS", key="settings_add_oos", type="primary"):
      try:
        add_oos_window(
          label=str(new_oos_label or "").strip(),
          oos_from=new_oos_from.isoformat(),
          oos_to=new_oos_until.isoformat(),
          activate=True,
        )
        for key in (
          "settings_oos_labels",
          "settings_new_oos_label",
          "settings_remove_oos_label",
          "gs_oos_labels",
        ):
          st.session_state.pop(key, None)
        st.toast("Đã thêm cửa sổ OOS")
        st.rerun()
      except ValueError as exc:
        st.error(str(exc))

  if len(oos_catalog) > 1:
    remove_oos_opt = st.selectbox(
      "Xóa cửa sổ OOS khỏi danh sách",
      oos_options,
      key="settings_remove_oos_label",
    )
    if st.button("Xóa cửa sổ OOS đã chọn", key="settings_remove_oos"):
      try:
        key = oos_option_to_key.get(remove_oos_opt)
        if not key:
          raise ValueError("Không tìm thấy cửa sổ OOS.")
        remove_oos_window(key)
        for k in ("settings_oos_labels", "settings_remove_oos_label", "gs_oos_labels"):
          st.session_state.pop(k, None)
        st.toast("Đã xóa cửa sổ OOS")
        st.rerun()
      except ValueError as exc:
        st.error(str(exc))
  else:
    st.caption("Giữ ít nhất một cửa sổ OOS — thêm cửa sổ mới trước khi xóa.")

  st.caption(
    "Mục tiêu xếp hạng Grid Search nằm ở trang **Grid Search** "
    "(đổi objective → bảng / Best đổi ngay, không cần chạy lại combo)."
  )

  st.markdown("#### Mining search space")
  import os
  from mining_presets import curated_preset_catalog, preset_label, recommended_preset
  desk = (os.environ.get("TRAINAPP_DESK") or "").strip().lower()
  is_gbp = desk.startswith("g")
  rec = recommended_preset()
  fill_cap = (
    "Lab fill **BUY Ask / SELL Bid**, SL = ATR×mult + 1 **SpreadPoints từng nến** XM. "
    "Không cộng trượt giá lab."
  )
  if is_gbp:
    mining_help = (
      "Hướng **GBP Bid/Ask**: densify n (gap 6, confirm 0.12) + trail 2.4R — nhắm WR>50 và R>50. "
      "Bỏ trống = miner baseline cũ (không khuyến nghị)."
    )
    rec_cap = (
      "Reset / chạy lại GBP: **r50** (`gbp_fill_r50`) · OOS **2026-h1**. "
      f"`{rec}` vẫn trong catalog. Trade Model active mang search space riêng cho Live."
    )
  else:
    mining_help = (
      "Hướng **EUR Bid/Ask**: densify n (gap 6, confirm 0.15) + trail 2.4R — nhắm WR>50 và R>50. "
      "Bỏ trống = miner baseline cũ (không khuyến nghị)."
    )
    rec_cap = (
      "Reset / chạy lại EUR: **r50** (`eur_fill_r50`) · OOS **2026-h1**. "
      "`eur_fill_ss_lab` vẫn trong catalog. Trade Model active mang search space riêng cho Live."
    )
  st.caption(fill_cap)
  mining_option_names = st.session_state.get("_settings_mining_option_names") or []
  mining_options = [preset_label(n) for n in mining_option_names]
  mining_picked = st.multiselect(
    "Preset mining (Grid Search)",
    mining_options,
    key="settings_mining_presets",
    help=mining_help,
  )
  st.caption(rec_cap)
  with st.expander("Chi tiết preset — ý định & trade-off", expanded=False):
    catalog = curated_preset_catalog()
    if catalog:
      st.dataframe(catalog, hide_index=True, use_container_width=True)
    st.caption(
      "Mỗi preset = baseline + vài knobs (RR, exit, anti-chase, cách chấm điểm). "
      "Đổi preset → chạy lại Grid → tạo Trade Model mới nếu muốn Live dùng hướng đó."
    )

  valid = True
  if not train_weeks:
    st.warning("Chọn ít nhất một cửa sổ học chiến lược; thay đổi này chưa được lưu.")
    valid = False
  if not picked_eras:
    st.warning("Chọn ít nhất một giai đoạn học; thay đổi này chưa được lưu.")
    valid = False
  if not picked_oos:
    st.warning("Chọn ít nhất một cửa sổ OOS; thay đổi này chưa được lưu.")
    valid = False

  label_to_name = st.session_state.get("_settings_mining_label_to_name") or {}
  mining_names = [label_to_name[opt] for opt in mining_picked if opt in label_to_name]
  current = {
    "strategy_train_weeks": list(train_weeks),
    "learning_era_keys": [option_to_key[opt] for opt in picked_eras if opt in option_to_key],
    "learning_loops": int(learning_loops),
    "oos_window_keys": [
      oos_option_to_key[opt] for opt in picked_oos if opt in oos_option_to_key
    ],
    "mining_presets": mining_names,
  }
  preview = dict(s)
  preview.update(current)
  pairs = describe_kb_oos_pairs(preview)
  if pairs:
    ok_n = sum(1 for p in pairs if p["ok"])
    skipped = [p for p in pairs if p["overlap"]]
    st.caption(f"Cặp KB × OOS hợp lệ: **{ok_n}/{len(pairs)}** — trùng ngày thì Grid bỏ.")
    if skipped:
      st.warning(
        "Bỏ vì KB trùng OOS: "
        + "; ".join(f"{p['era_label']} × {p['oos_label']}" for p in skipped)
      )
    if ok_n == 0:
      st.error("Không còn cặp KB × OOS hợp lệ — Grid Search sẽ không chạy được.")
  changed = any(s.get(key) != value for key, value in current.items())
  if valid and changed:
    update_settings(**current)
    st.caption("Đã tự động lưu. Chạy Grid Search lại để áp dụng cấu hình mới.")

  st.divider()
  st.markdown("#### Pipeline một lần")
  st.caption(
    "Học đủ epoch cho mọi giai đoạn đã chọn trong Cài đặt, rồi chạy Grid Search "
    "(train × KB × epoch × mining) theo cấu hình hiện tại. Chạy nền — có thể đổi tab."
  )
  from gui.grid_search_background import is_grid_running
  from gui.long_task_background import is_task_running, start_job
  from gui.long_task_ui import render_task_status, task_blocks_ui

  render_task_status(key_prefix="settings_pipe", show_cancel=True)
  pipe_busy = task_blocks_ui("settings_pipe") or is_grid_running()
  reset_pipe = st.checkbox(
    "Reset & học lại mọi KB từ đầu",
    value=False,
    key="settings_pipeline_reset",
    help="Tắt = bỏ qua profile đã đủ epoch. Bật = xóa KB rồi học lại từ đầu.",
  )
  n_eras = len(current["learning_era_keys"])
  loops = int(current["learning_loops"])
  if st.button(
    "▶ Chạy pipeline: học KB → Grid",
    type="primary",
    key="settings_run_pipeline",
    disabled=pipe_busy or not valid,
  ):
    try:
      # Persist current widget values before the job reads Settings.
      if valid and changed:
        update_settings(**current)
      start_job(
        "kb_then_grid",
        {
          "reset_kb": bool(reset_pipe),
          "objective": s.get("grid_objective") or "risk_adjusted",
        },
        label=f"Pipeline · {n_eras} KB × {loops} vòng → Grid",
      )
      st.toast("Pipeline đã bắt đầu chạy nền")
      st.rerun()
    except (RuntimeError, ValueError) as e:
      st.error(str(e))
  if is_task_running() or is_grid_running():
    st.caption("Đang có task/Grid chạy — đợi hoặc hủy trước khi khởi động pipeline mới.")

  st.divider()
  st.caption(
    f"Chữ ký grid: `{settings_grid_signature()}` · "
    f"Cập nhật: {s.get('updated_at') or '—'}"
  )

  if st.button("↺ Khôi phục mặc định", key="settings_reset"):
    from gui.app_settings import default_settings_for_desk, save_settings
    save_settings(default_settings_for_desk())
    for key in SETTING_WIDGET_KEYS:
      st.session_state.pop(key, None)
    st.toast("Đã khôi phục cài đặt mặc định")
    st.rerun()
