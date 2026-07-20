"""Học & tối ưu — quy trình: Huấn luyện KB → Grid Search → Trade Models."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.views import grid_search, kb_era_hub
from gui.views.compare_sections import render_era_compare, render_epoch_sweep, render_train_window
from gui.views import trade_models_view

# Thứ tự bắt buộc — không đổi
CORE_TAB_KEYS = ["train_kb", "grid", "models"]
CORE_TAB_LABELS = {
  "train_kb": "① Huấn luyện bộ nhớ",
  "grid": "② Grid Search",
  "models": "③ Trade Models",
}

ADVANCED_TAB_KEYS = ["era", "epoch", "train_win"]
ADVANCED_TAB_LABELS = {
  "era": "So giai đoạn",
  "epoch": "So vòng học",
  "train_win": "So cửa sổ học",
}

TAB_KEYS = CORE_TAB_KEYS + ADVANCED_TAB_KEYS
TAB_LABELS = {**CORE_TAB_LABELS, **ADVANCED_TAB_LABELS}


def _default_learning_tab() -> str:
  """Tab mặc định theo tiến độ workflow."""
  from gui.grid_search_engine import grid_readiness, load_latest_grid_run
  from gui.trade_model import get_active_trade_model

  if get_active_trade_model():
    return "models"
  data = load_latest_grid_run()
  if data and (data.get("rows") or []):
    return "models"
  r = grid_readiness()
  if r["kb_complete"]:
    return "grid"
  return "train_kb"


def _render_workflow_strip():
  from gui.grid_search_engine import grid_readiness, load_latest_grid_run
  from gui.trade_model import get_active_trade_model

  r = grid_readiness()
  has_grid = bool((load_latest_grid_run() or {}).get("rows"))
  has_model = bool(get_active_trade_model())
  kb_done = r["kb_complete"]

  s1 = "✅" if kb_done else "▶️"
  s2 = "✅" if has_grid else "▶️" if kb_done else "○"
  s3 = "✅" if has_model else "▶️" if has_grid else "○"

  st.markdown(
    f"{s1} **① Huấn luyện bộ nhớ** ({r['ready_combos']}/{r['expected_combos']} combo sẵn sàng)  \n"
    f"{s2} **② Grid Search**  \n"
    f"{s3} **③ Trade Model** → Paper & Phân tích"
  )


def _render_subview(module):
  import inspect
  sig = inspect.signature(module.render)
  if "embedded" in sig.parameters:
    module.render(embedded=True)
  else:
    module.render()


def _tab_button(label: str, tab_key: str, *, active: bool, key: str):
  if st.button(
    label,
    key=key,
    type="primary" if active else "secondary",
    use_container_width=True,
  ):
    st.session_state["learning_tab"] = tab_key
    st.rerun()


def render():
  render_page_header(ALL_ITEMS["learning"], show_profile=False)

  from gui.app_settings import format_settings_summary, get_settings
  st.caption(format_settings_summary(get_settings()))

  _render_workflow_strip()

  st.markdown(
    "**Làm lần lượt:** huấn luyện 3 giai đoạn KB → Grid Search → tạo Trade Model. "
    "Không chạy Grid Search trước khi bước ① xong."
  )

  from gui.long_task_ui import render_task_status
  render_task_status(key_prefix="learning_hub", compact=True)

  pick = st.session_state.get("learning_tab")
  if pick not in TAB_KEYS:
    pick = _default_learning_tab()
  st.session_state["learning_tab"] = pick

  st.markdown("**Quy trình chính**")
  c1, c2, c3 = st.columns(3)
  for col, tab_key in zip((c1, c2, c3), CORE_TAB_KEYS):
    with col:
      _tab_button(
        CORE_TAB_LABELS[tab_key],
        tab_key,
        active=(pick == tab_key),
        key=f"learning_tab_{tab_key}",
      )

  st.markdown("**So sánh**")
  c4, c5, c6 = st.columns(3)
  for col, tab_key in zip((c4, c5, c6), ADVANCED_TAB_KEYS):
    with col:
      _tab_button(
        ADVANCED_TAB_LABELS[tab_key],
        tab_key,
        active=(pick == tab_key),
        key=f"learning_tab_{tab_key}",
      )

  selected = st.session_state.get("learning_tab", pick)

  st.divider()
  st.session_state["_learning_hub"] = True
  try:
    if selected == "train_kb":
      kb_era_hub.render_training_only()
    elif selected == "grid":
      _render_subview(grid_search)
    elif selected == "models":
      trade_models_view.render(embedded=True)
    elif selected == "era":
      render_era_compare()
    elif selected == "epoch":
      render_epoch_sweep()
    else:
      render_train_window()
  finally:
    st.session_state.pop("_learning_hub", None)
