"""ForexForge v2 Streamlit entry — UX ro rang hon."""
from __future__ import annotations

import sys

try:
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
  pass

import streamlit as st

from forexforge.ui import (
  page_backtest,
  page_compare,
  page_data,
  page_home,
  page_inspect,
  page_kb,
  page_paper,
)

st.set_page_config(page_title="ForexForge v2", layout="wide", initial_sidebar_state="expanded")

PAGES = {
  "0. Bat dau (doc truoc)": page_home.render,
  "1. Data Hub": page_data.render,
  "2. Backtest Lab": page_backtest.render,
  "3. KB Era Hub": page_kb.render,
  "4. Report Compare": page_compare.render,
  "5. Risk / Journal / Inspector": page_inspect.render,
  "6. Paper Monitor": page_paper.render,
}

st.sidebar.title("ForexForge v2")
st.sidebar.markdown(
  """
**Cach dung nhanh**
1. Data Hub → Refresh  
2. Backtest Lab → KB OFF  
3. KB Era → hoc era  
4. Compare OFF vs ON  
5. Paper tick  

Thuat toan giong ban cu.  
Khac: job chay **nen**, chong leakage.
"""
)
choice = st.sidebar.radio("Menu", list(PAGES.keys()), index=0)
PAGES[choice]()
