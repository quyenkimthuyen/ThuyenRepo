"""Học & tối ưu — Grid Search, Trade Models, so sánh, huấn luyện bộ nhớ."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.views import grid_search, kb_era_hub
from gui.views.compare_sections import render_era_compare, render_epoch_sweep, render_train_window
from gui.views import trade_models_view


TAB_KEYS = ["grid", "models", "train_kb", "era", "epoch", "train_win"]
TAB_LABELS = {
  "grid": "🔎 Grid Search",
  "models": "📦 Trade Models",
  "train_kb": "🧠 Huấn luyện bộ nhớ",
  "era": "⚖️ So giai đoạn",
  "epoch": "📈 So vòng học",
  "train_win": "⏱ So cửa sổ học",
}


def _render_subview(module):
  import inspect
  sig = inspect.signature(module.render)
  if "embedded" in sig.parameters:
    module.render(embedded=True)
  else:
    module.render()


def render():
  render_page_header(ALL_ITEMS["learning"], show_profile=False)

  from gui.app_settings import format_settings_summary, get_settings
  st.info(f"**Cài đặt hiện tại:** {format_settings_summary(get_settings())}")

  st.markdown(
    "Chạy **Grid Search** theo cài đặt → chọn combo tốt → **tạo Trade Model** dùng cho paper & phân tích."
  )

  from gui.long_task_ui import render_task_status
  render_task_status(key_prefix="learning_hub", compact=True)

  default_tab = st.session_state.get("learning_tab", "grid")
  if default_tab not in TAB_KEYS:
    default_tab = "grid"
  tab_idx = TAB_KEYS.index(default_tab)

  selected_label = st.radio(
    "Tab",
    [TAB_LABELS[k] for k in TAB_KEYS],
    horizontal=True,
    index=tab_idx,
    key="learning_tab_radio",
  )
  selected = TAB_KEYS[[TAB_LABELS[k] for k in TAB_KEYS].index(selected_label)]
  st.session_state["learning_tab"] = selected

  st.divider()
  st.session_state["_learning_hub"] = True
  try:
    if selected == "grid":
      _render_subview(grid_search)
    elif selected == "models":
      trade_models_view.render(embedded=True)
    elif selected == "train_kb":
      kb_era_hub.render_training_only()
    elif selected == "era":
      render_era_compare()
    elif selected == "epoch":
      render_epoch_sweep()
    else:
      render_train_window()
  finally:
    st.session_state.pop("_learning_hub", None)
