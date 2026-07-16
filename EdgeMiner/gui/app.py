"""ForexForge GUI — full application."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from gui.views import (
  command_center, backtest_lab, trade_journal, strategy_inspector,
  learning_center, risk_dashboard, paper_monitor, usage_guide,
)

PAGES = {
  "Command Center": command_center,
  "Backtest Lab": backtest_lab,
  "Trade Journal": trade_journal,
  "Strategy Inspector": strategy_inspector,
  "Learning Center": learning_center,
  "Risk Dashboard": risk_dashboard,
  "Paper Monitor": paper_monitor,
  "Usage Guide": usage_guide,
}


def main():
  st.set_page_config(
    page_title="ForexForge",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
  )

  st.sidebar.title("ForexForge")
  st.sidebar.caption("EUR/USD H1 · Walk-forward · Self-learning v4")
  page = st.sidebar.radio("Điều hướng", list(PAGES.keys()))

  st.sidebar.divider()
  st.sidebar.markdown("**Pair** EUR/USD · **TF** H1")
  st.sidebar.markdown("**Data** Dukascopy 2022+")
  st.sidebar.markdown("**Engine** Miner v3/v4")
  st.sidebar.caption("Xem **Usage Guide** để biết quy trình đầy đủ.")

  PAGES[page].render()


if __name__ == "__main__":
  main()
