"""Legacy hub — chuyển hướng sang Học & tối ưu."""
from __future__ import annotations

import streamlit as st


def render():
  st.session_state["nav_page"] = "learning"
  st.session_state["learning_tab"] = "grid"
  st.rerun()
