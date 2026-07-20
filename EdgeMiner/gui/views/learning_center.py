"""Legacy route — chuyển hướng sang KB & Học."""
from __future__ import annotations

import streamlit as st


def render():
  st.session_state["nav_page"] = "kb"
  st.rerun()
