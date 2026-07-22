"""ForexForge GUI — full application."""
from __future__ import annotations

import sys
from pathlib import Path

# Windows consoles often use cp1252 — avoid UnicodeEncodeError on Vietnamese logs.
for _stream in (sys.stdout, sys.stderr):
  if hasattr(_stream, "reconfigure"):
    try:
      _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
      pass

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from gui.views import (
  command_center, paper_monitor, usage_guide,
  learning_hub, analysis_hub, settings_page, mt5_bridge,
)
from gui.navigation import (
  ALL_ITEMS, LEGACY_ALIASES, NAV_GROUPS,
  LEARNING_TAB_BY_ALIAS, ANALYSIS_TAB_BY_ALIAS, default_page_key,
)
from gui.workspace import ensure_profiles_loaded

VIEW_MODULES = {
  "command_center": command_center,
  "paper_monitor": paper_monitor,
  "mt5_bridge": mt5_bridge,
  "learning_hub": learning_hub,
  "analysis_hub": analysis_hub,
  "settings_page": settings_page,
  "usage_guide": usage_guide,
}


def _resolve_page_key() -> str:
  legacy = st.session_state.get("nav_legacy_page")
  if legacy:
    key = LEGACY_ALIASES.get(legacy)
    if key:
      ltab = LEARNING_TAB_BY_ALIAS.get(legacy)
      if ltab:
        st.session_state["learning_tab"] = ltab
      atab = ANALYSIS_TAB_BY_ALIAS.get(legacy)
      if atab:
        st.session_state["analysis_tab"] = atab
      st.session_state.pop("nav_legacy_page", None)
      st.session_state["nav_page"] = key
      return key

  key = st.session_state.get("nav_page")
  if key in ALL_ITEMS:
    return key
  return default_page_key()


def _render_sidebar_nav() -> str:
  st.sidebar.markdown("### Điều hướng")
  current = _resolve_page_key()

  for group in NAV_GROUPS:
    st.sidebar.markdown(f"**{group.title}**")
    for item in group.items:
      active = item.key == current
      label = f"› {item.label}" if active else item.label
      if st.sidebar.button(
        label,
        key=f"nav_{item.key}",
        use_container_width=True,
        type="primary" if active else "secondary",
      ):
        st.session_state["nav_page"] = item.key
        st.rerun()
    st.sidebar.markdown("")

  return current


def _sidebar_status():
  from gui.services import load_backtest_report
  from gui.trade_model import format_model_label, get_active_trade_model

  m = get_active_trade_model()
  if m:
    st.sidebar.divider()
    st.sidebar.caption(f"Trade model: **{format_model_label(m)}**")
    report = load_backtest_report()
    if report:
      o = report.get("overall_oos") or {}
      st.sidebar.caption(f"Backtest: **{o.get('total_r', '—')}R**")

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
    page_title="ForexForge",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
  )

  try:
    from paper_background import ensure_background_running
    ensure_background_running()
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

  st.sidebar.title("ForexForge")
  st.sidebar.caption("EUR/USD H1 · mô phỏng từng tuần")

  from gui.glossary import render_glossary_expander
  render_glossary_expander(location="sidebar")

  page_key = _render_sidebar_nav()
  _sidebar_status()

  st.sidebar.divider()
  st.sidebar.caption("① Cài đặt → ② Học KB → Grid → Model → Paper")

  item = ALL_ITEMS[page_key]
  module = VIEW_MODULES[item.module]
  module.render()


if __name__ == "__main__":
  main()
