"""Paper Monitor GUI — **retired**.

``render()`` redirects to MT5 Bridge. Legacy bookmarks / deep-links that still
import this module should land here instead of the old desk UI.
"""
from __future__ import annotations

import streamlit as st


def render() -> None:
  st.info(
    "Paper Monitor đã ngừng dùng. "
    "Dùng **MT5 Bridge** (Live / Simulate) hoặc **Compare Trade**."
  )
  try:
    from gui.ui_preferences import set_widget_preference
    set_widget_preference("nav_page", "mt5_bridge", "navigation.page")
  except Exception:
    st.session_state["nav_page"] = "mt5_bridge"
  if st.button("Mở MT5 Bridge", type="primary", key="paper_retired_go_bridge"):
    st.rerun()
