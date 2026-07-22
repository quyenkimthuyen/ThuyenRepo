"""Phân tích — legacy entry; thực tế nằm dưới Trade Models."""
from __future__ import annotations

import streamlit as st


def render():
  """Redirect vào Học & tối ưu → Trade Models → phân tích."""
  st.session_state["nav_page"] = "learning"
  st.session_state["learning_tab"] = "models"
  sub = st.session_state.get("models_subtab") or st.session_state.get("analysis_tab") or "risk"
  if sub not in ("risk", "journal", "strategy", "manage"):
    sub = "risk"
  st.session_state["models_subtab"] = sub
  st.rerun()
