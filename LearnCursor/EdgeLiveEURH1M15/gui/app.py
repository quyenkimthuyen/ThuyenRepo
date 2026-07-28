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
  command_center, usage_guide,
  learning_hub, mt5_bridge,
)
from gui.navigation import (
  ALL_ITEMS, LEGACY_ALIASES, NAV_ITEMS,
  LEARNING_TAB_BY_ALIAS, ANALYSIS_TAB_BY_ALIAS, default_page_key,
)
from gui.ui_theme import icon_btn, inject_theme
from gui.ui_preferences import restore_widget, set_widget_preference
from gui.workspace import ensure_profiles_loaded
from config import get_active_tf, set_active_tf

VIEW_MODULES = {
  "command_center": command_center,
  "mt5_bridge": mt5_bridge,
  "learning_hub": learning_hub,
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
  # Old bookmarks: settings / analysis were top-level pages
  if key == "settings":
    set_widget_preference("nav_page", "learning", "navigation.page")
    set_widget_preference("learning_tab", "settings", "navigation.learning_tab")
    return "learning"
  if key == "analysis":
    set_widget_preference("nav_page", "learning", "navigation.page")
    set_widget_preference("learning_tab", "models", "navigation.learning_tab")
    sub = st.session_state.get("models_subtab") or st.session_state.get("analysis_tab") or "risk"
    set_widget_preference("models_subtab", sub, "navigation.models_subtab")
    return "learning"
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
    from gui.grid_search_background import ensure_grid_worker_running
    ensure_grid_worker_running()
  except Exception:
    pass

  try:
    from gui.long_task_background import ensure_task_worker_running
    ensure_task_worker_running()
  except Exception:
    pass

  # Keep both TF live workers warm if previously enabled
  try:
    from mt5_bridge.background import ensure_worker_running
    ensure_worker_running(tf="M15")
    ensure_worker_running(tf="H1")
  except Exception:
    pass

  ensure_profiles_loaded()
  restore_widget(
    "nav_page", default_page_key(),
    preference_key="navigation.page",
    options=list(ALL_ITEMS.keys()),
  )
  restore_widget(
    "active_tf", get_active_tf(),
    preference_key="app.active_tf",
    options=["M15", "H1"],
  )
  # Bridge TF shares the same sidebar choice (avoid duplicate pickers on page)
  if "mt5_bridge_tf" not in st.session_state:
    restore_widget(
      "mt5_bridge_tf", st.session_state.get("active_tf", get_active_tf()),
      preference_key="mt5.bridge_tf",
      options=["M15", "H1"],
    )
  inject_theme()

  st.sidebar.markdown("### ForexForge")
  st.sidebar.caption("EUR/USD · H1 + M15 Live/Sim")

  def _on_tf_change():
    tf = st.session_state.get("active_tf", "M15")
    set_active_tf(tf)
    st.session_state["mt5_bridge_tf"] = tf
    set_widget_preference("active_tf", tf, "app.active_tf")
    set_widget_preference("mt5_bridge_tf", tf, "mt5.bridge_tf")

  tf_choice = st.sidebar.radio(
    "Timeframe Bridge",
    ["M15", "H1"],
    horizontal=True,
    key="active_tf",
    on_change=_on_tf_change,
    help="TF cho Học & tối ưu / Trade Model và desk MT5 Bridge (Live/Sim).",
  )
  set_active_tf(tf_choice)
  st.session_state["mt5_bridge_tf"] = tf_choice

  from gui.ui_theme import icon_btn
  from gui.ea_deploy import ALL_EA_LABELS, deploy_all_eas

  st.sidebar.divider()
  if icon_btn(
    "Deploy 4 EA",
    key="sb_deploy_all_eas",
    icon=":material/rocket_launch:",
    help=(
      "Compile + attach cả 4 EA: M15/H1 × Live/Sim. "
      "Cần XM MT5 Windows · 2 chart EURUSD M15 + 2 chart EURUSD H1."
    ),
  ):
    with st.spinner(
      "Đang deploy 4 EA (M15/H1 · Live/Sim) — compile + attach…"
    ):
      result = deploy_all_eas(attach=True, enable_trading=True)
    if result.get("ok"):
      st.sidebar.success("Deploy 4 EA OK")
      st.toast("Đã deploy: " + " · ".join(ALL_EA_LABELS), icon="🚀")
    else:
      st.sidebar.error("Deploy 4 EA thất bại")
    with st.sidebar.expander("Log deploy", expanded=not result.get("ok")):
      log = (result.get("stdout") or "") + "\n" + (result.get("stderr") or "")
      st.code(log.strip() or f"(exit {result.get('returncode')})")

  from gui.glossary import render_glossary_expander
  render_glossary_expander(location="sidebar")

  page_key = _render_sidebar_nav()
  _sidebar_status()

  st.sidebar.divider()
  st.sidebar.caption("Cài đặt → KB → Grid → Model → Live/Sim")

  item = ALL_ITEMS[page_key]
  module = VIEW_MODULES[item.module]
  module.render()


if __name__ == "__main__":
  main()
