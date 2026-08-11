"""ForexForge GUI — full application."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows consoles / Streamlit workers may have stdout/stderr is None (pythonw).
# Guard before any import that prints or uses tqdm.
for _name in ("stdout", "stderr"):
  _stream = getattr(sys, _name, None)
  if _stream is None:
    setattr(sys, _name, open(os.devnull, "w", encoding="utf-8", errors="replace"))
  elif hasattr(_stream, "reconfigure"):
    try:
      _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from config import DEFAULT_PAIR, DEFAULT_TF

from gui.views import (
  command_center, usage_guide,
  learning_hub, mt5_bridge, trade_models_view, compare_trade, live_trade_dash,
)
from gui.navigation import (
  ALL_ITEMS, LEGACY_ALIASES, NAV_ITEMS,
  LEARNING_TAB_BY_ALIAS, ANALYSIS_TAB_BY_ALIAS, default_page_key,
)
from gui.ui_theme import icon_btn, inject_theme
from gui.ui_preferences import restore_widget, set_widget_preference
from gui.workspace import ensure_profiles_loaded

VIEW_MODULES = {
  "command_center": command_center,
  "mt5_bridge": mt5_bridge,
  "live_trade_dash": live_trade_dash,
  "learning_hub": learning_hub,
  "trade_models_view": trade_models_view,
  "compare_trade": compare_trade,
  "usage_guide": usage_guide,
}


def _resolve_page_key() -> str:
  legacy = st.session_state.get("nav_legacy_page")
  if legacy:
    key = LEGACY_ALIASES.get(legacy)
    if key:
      ltab = LEARNING_TAB_BY_ALIAS.get(legacy)
      if ltab:
        set_widget_preference("learning_tab", ltab, "navigation.learning_tab")
      atab = ANALYSIS_TAB_BY_ALIAS.get(legacy)
      if atab:
        set_widget_preference("analysis_tab", atab, "navigation.analysis_tab")
        set_widget_preference("models_subtab", atab, "navigation.models_subtab")
      st.session_state.pop("nav_legacy_page", None)
      set_widget_preference("nav_page", key, "navigation.page")
      return key

  key = st.session_state.get("nav_page")
  # Old bookmarks: settings / analysis / paper / learning+models tab
  if key == "settings":
    set_widget_preference("nav_page", "learning", "navigation.page")
    set_widget_preference("learning_tab", "settings", "navigation.learning_tab")
    return "learning"
  if key == "analysis":
    set_widget_preference("nav_page", "models", "navigation.page")
    sub = st.session_state.get("models_subtab") or st.session_state.get("analysis_tab") or "risk"
    set_widget_preference("models_subtab", sub, "navigation.models_subtab")
    return "models"
  if key == "paper":
    # Paper Monitor retired — send bookmarks to MT5 Bridge
    set_widget_preference("nav_page", "mt5_bridge", "navigation.page")
    return "mt5_bridge"
  if key == "learning" and st.session_state.get("learning_tab") == "models":
    set_widget_preference("nav_page", "models", "navigation.page")
    set_widget_preference("learning_tab", "grid", "navigation.learning_tab")
    return "models"
  if key in ALL_ITEMS:
    return key
  return default_page_key()


def _render_sidebar_nav() -> str:
  st.sidebar.markdown("### Menu")
  current = _resolve_page_key()

  for item in NAV_ITEMS:
    active = item.key == current
    with st.sidebar:
      if icon_btn(
        item.label,
        key=f"nav_{item.key}",
        icon=item.icon or None,
        active=active,
      ):
        set_widget_preference("nav_page", item.key, "navigation.page")
        st.rerun()

  return current


def _sidebar_status():
  try:
    from gui.grid_search_background import get_grid_status
    gs = get_grid_status()
    if gs.get("running"):
      st.sidebar.caption(
        f"🔎 Grid: **{gs['done']}/{gs['total']}** ({gs['pct']}%)"
      )
  except Exception:
    pass

  try:
    from gui.long_task_background import get_task_status
    ts = get_task_status()
    if ts.get("running"):
      st.sidebar.caption(
        f"⏳ {ts['job_label']}: **{ts['done']}/{ts['total']}** ({ts['pct']}%)"
      )
  except Exception:
    pass


def main():
  st.set_page_config(
    page_title=f"ForexForge · {DEFAULT_PAIR} {DEFAULT_TF}",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
  )

  try:
    from paper_service import stop_worker as stop_paper_worker
    stop_paper_worker()
  except Exception:
    pass

  try:
    from gui.grid_search_background import ensure_grid_worker_running
    ensure_grid_worker_running()
  except Exception:
    pass

  try:
    from gui.long_task_background import ensure_task_worker_running
    ensure_task_worker_running()
  except Exception:
    pass

  try:
    from mt5_bridge.background import ensure_worker_running
    ensure_worker_running()
  except Exception:
    pass

  ensure_profiles_loaded()
  restore_widget(
    "nav_page", default_page_key(),
    preference_key="navigation.page",
    options=list(ALL_ITEMS.keys()),
  )
  inject_theme()

  st.sidebar.markdown("### ForexForge")
  st.sidebar.caption(f"{DEFAULT_PAIR} {DEFAULT_TF} · retrain tuần")

  page_key = _render_sidebar_nav()
  _sidebar_status()

  st.sidebar.divider()
  from gui.mt5_deploy_ui import render_sidebar_deploy_eas
  render_sidebar_deploy_eas()

  st.sidebar.divider()
  st.sidebar.caption("Cài đặt → KB → Grid → Model → Live/Simulate")

  item = ALL_ITEMS[page_key]
  module = VIEW_MODULES[item.module]
  module.render()


if __name__ == "__main__":
  main()
