"""Paper Monitor GUI — **retired**.

``render()`` redirects to MT5 Bridge. Legacy bookmarks / deep-links that still
import this module should land here instead of the old desk UI.
"""
from __future__ import annotations

import streamlit as st


def render() -> None:
  st.info(
    "Paper Monitor đã ngừng dùng. "
    "Dùng **Live Trade** hoặc **Compare Trade**."
  )
  try:
    from gui.ui_preferences import set_widget_preference
    set_widget_preference("nav_page", "live_trade", "navigation.page")
  except Exception:
    st.session_state["nav_page"] = "live_trade"
  if st.button("Mở Live Trade", type="primary", key="paper_retired_go_bridge"):
    st.rerun()
