"""Học & tối ưu — Cài đặt → Huấn luyện KB → Grid Search → Trade Models."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.ui_theme import icon_btn
from gui.views import grid_search, kb_era_hub, settings_page
from gui.views.compare_sections import render_era_compare, render_epoch_sweep, render_train_window
from gui.views import trade_models_view

CORE_TAB_KEYS = ["settings", "train_kb", "grid", "models"]
CORE_TAB_LABELS = {
  "settings": "Cài đặt",
  "train_kb": "Huấn luyện",
  "grid": "Grid Search",
  "models": "Trade Models",
}
CORE_TAB_ICONS = {
  "settings": ":material/settings:",
  "train_kb": ":material/psychology:",
  "grid": ":material/grid_view:",
  "models": ":material/inventory_2:",
}

ADVANCED_TAB_KEYS = ["era", "epoch", "train_win"]
ADVANCED_TAB_LABELS = {
  "era": "So giai đoạn",
  "epoch": "So vòng học",
  "train_win": "So cửa sổ học",
}
ADVANCED_TAB_ICONS = {
  "era": ":material/timeline:",
  "epoch": ":material/loop:",
  "train_win": ":material/date_range:",
}

TAB_KEYS = CORE_TAB_KEYS + ADVANCED_TAB_KEYS


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
  return "settings"


def _render_workflow_strip():
  from gui.grid_search_engine import grid_readiness, load_latest_grid_run
  from gui.trade_model import get_active_trade_model

  r = grid_readiness()
  has_grid = bool((load_latest_grid_run() or {}).get("rows"))
  has_model = bool(get_active_trade_model())
  kb_done = r["kb_complete"]

  mark = {"done": "●", "current": "◉", "todo": "○"}
  s_kb = "done" if kb_done else "current"
  s_grid = "done" if has_grid else ("current" if kb_done else "todo")
  s_model = "done" if has_model else ("current" if has_grid else "todo")

  st.caption(
    f"{mark['done']} Cài đặt · "
    f"{mark[s_kb]} KB ({r['ready_combos']}/{r['expected_combos']}) · "
    f"{mark[s_grid]} Grid · {mark[s_model]} Model"
  )


def _render_subview(module):
  import inspect
  sig = inspect.signature(module.render)
  if "embedded" in sig.parameters:
    module.render(embedded=True)
  else:
    module.render()


def render():
  render_page_header(ALL_ITEMS["learning"], show_profile=False)
  _render_workflow_strip()

  from gui.long_task_ui import render_task_status
  render_task_status(key_prefix="learning_hub", compact=True)

  pick = st.session_state.get("learning_tab")
  if pick not in TAB_KEYS:
    pick = _default_learning_tab()
  st.session_state["learning_tab"] = pick

  cols = st.columns(4)
  for col, tab_key in zip(cols, CORE_TAB_KEYS):
    with col:
      if icon_btn(
        CORE_TAB_LABELS[tab_key],
        key=f"learning_tab_{tab_key}",
        icon=CORE_TAB_ICONS[tab_key],
        active=(pick == tab_key),
      ):
        st.session_state["learning_tab"] = tab_key
        st.rerun()

  with st.expander("So sánh nâng cao", expanded=pick in ADVANCED_TAB_KEYS):
    adv_cols = st.columns(3)
    for col, tab_key in zip(adv_cols, ADVANCED_TAB_KEYS):
      with col:
        if icon_btn(
          ADVANCED_TAB_LABELS[tab_key],
          key=f"learning_adv_{tab_key}",
          icon=ADVANCED_TAB_ICONS[tab_key],
          active=(pick == tab_key),
        ):
          st.session_state["learning_tab"] = tab_key
          st.rerun()

  selected = st.session_state.get("learning_tab", pick)

  st.divider()
  st.session_state["_learning_hub"] = True
  try:
    if selected == "settings":
      _render_subview(settings_page)
    elif selected == "train_kb":
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
