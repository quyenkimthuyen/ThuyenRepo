"""UI polish — Material icons + compact Streamlit chrome."""
from __future__ import annotations

import streamlit as st

# Inject once per session
_CSS_KEY = "_ff_theme_injected"

_COMPACT_CSS = """
<style>
/* Denser sidebar nav */
section[data-testid="stSidebar"] .stButton > button {
  justify-content: flex-start;
  text-align: left;
  padding-top: 0.35rem;
  padding-bottom: 0.35rem;
  min-height: 2.1rem;
  font-weight: 500;
  gap: 0.45rem;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.65;
  margin-bottom: 0.35rem;
}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
  gap: 0.2rem;
}
/* Hub tab row — equal compact buttons */
div[data-testid="stHorizontalBlock"] .stButton > button {
  min-height: 2.35rem;
  font-weight: 500;
  gap: 0.4rem;
}
/* Softer page headers */
h1, h2 { letter-spacing: -0.01em; }
</style>
"""


def inject_theme():
  if st.session_state.get(_CSS_KEY):
    return
  st.markdown(_COMPACT_CSS, unsafe_allow_html=True)
  st.session_state[_CSS_KEY] = True


def icon_btn(
  label: str,
  *,
  key: str,
  icon: str | None = None,
  active: bool = False,
  help: str | None = None,
  width: str = "stretch",
) -> bool:
  """Primary when active; Material icon via Streamlit ``icon=``."""
  return st.button(
    label,
    key=key,
    icon=icon,
    help=help,
    type="primary" if active else "secondary",
    width=width,
  )
