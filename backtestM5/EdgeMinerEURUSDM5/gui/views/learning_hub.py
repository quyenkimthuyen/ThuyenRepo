"""Học & tối ưu — Cài đặt → Huấn luyện KB → Grid Search → Final Train."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.page_chrome import render_page_header
from gui.ui_theme import icon_btn
from gui.ui_preferences import restore_widget, set_widget_preference
from gui.views import final_train, grid_search, kb_era_hub, settings_page

CORE_TAB_KEYS = ["settings", "train_kb", "grid", "final"]
CORE_TAB_LABELS = {
  "settings": "Cài đặt",
  "train_kb": "Huấn luyện",
  "grid": "Grid Search",
  "final": "Final Train",
}
CORE_TAB_ICONS = {
  "settings": ":material/settings:",
  "train_kb": ":material/psychology:",
  "grid": ":material/grid_view:",
  "final": ":material/emoji_events:",
}

TAB_KEYS = CORE_TAB_KEYS


def _default_learning_tab() -> str:
  """Tab mặc định theo tiến độ workflow."""
  from gui.grid_search_engine import grid_readiness, load_latest_grid_run

  data = load_latest_grid_run()
  if data and (data.get("rows") or []):
    # Có kết quả Grid → Final Train để xếp combo / tạo Trade Model.
    return "final"
  r = grid_readiness()
  if r["kb_complete"]:
    return "grid"
  return "settings"


def _render_workflow_strip():
  from gui.grid_search_engine import grid_readiness, load_latest_grid_run
  from gui.trade_model import get_active_trade_model, list_trade_models

  r = grid_readiness()
  has_grid = bool((load_latest_grid_run() or {}).get("rows"))
  has_models = bool(list_trade_models(include_archived=False))
  has_active = bool(get_active_trade_model())
  kb_done = r["kb_complete"]

  mark = {"done": "●", "current": "◉", "todo": "○"}
  s_kb = "done" if kb_done else "current"
  s_grid = "done" if has_grid else ("current" if kb_done else "todo")
  s_final = "done" if has_models else ("current" if has_grid else "todo")
  s_model = "done" if has_active else ("current" if has_models else "todo")

  st.caption(
    f"{mark['done']} Cài đặt · "
    f"{mark[s_kb]} KB ({r['ready_combos']}/{r['expected_combos']}) · "
    f"{mark[s_grid]} Grid · {mark[s_final]} Final · "
    f"{mark[s_model]} Model (sidebar)"
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

  # Old preference may still hold "models" — send users to the sidebar page.
  if st.session_state.get("learning_tab") == "models":
    set_widget_preference("nav_page", "models", "navigation.page")
    set_widget_preference("learning_tab", "grid", "navigation.learning_tab")
    st.rerun()

  pick = restore_widget(
    "learning_tab", _default_learning_tab(),
    preference_key="navigation.learning_tab",
    options=TAB_KEYS,
  )

  cols = st.columns(len(CORE_TAB_KEYS))
  for col, tab_key in zip(cols, CORE_TAB_KEYS):
    with col:
      if icon_btn(
        CORE_TAB_LABELS[tab_key],
        key=f"learning_tab_{tab_key}",
        icon=CORE_TAB_ICONS[tab_key],
        active=(pick == tab_key),
      ):
        set_widget_preference("learning_tab", tab_key, "navigation.learning_tab")
        st.rerun()

  selected = st.session_state.get("learning_tab", pick)

  st.divider()
  st.session_state["_learning_hub"] = True
  try:
    if selected == "settings":
      _render_subview(settings_page)
    elif selected == "train_kb":
      kb_era_hub.render_training_only()
    elif selected == "final":
      _render_subview(final_train)
    else:
      _render_subview(grid_search)
  finally:
    st.session_state.pop("_learning_hub", None)
