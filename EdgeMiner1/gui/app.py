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
  learning_center, risk_dashboard, paper_monitor, usage_guide, kb_era_hub,
  report_compare,
)

PAGES = {
  "Command Center": command_center,
  "KB & Giai đoạn": kb_era_hub,
  "Backtest Lab": backtest_lab,
  "Report Compare": report_compare,
  "Trade Journal": trade_journal,
  "Strategy Inspector": strategy_inspector,
  "Learning Center": learning_center,
  "Risk Dashboard": risk_dashboard,
  "Paper Monitor": paper_monitor,
  "Usage Guide": usage_guide,
}


def _sidebar_kb_profiles():
  try:
    from kb_profiles import list_profiles
    profiles = [p for p in list_profiles() if p.get("exists")]
    if not profiles:
      st.sidebar.caption("KB profiles: chưa có")
      return
    st.sidebar.markdown(f"**KB Profiles** ({len(profiles)})")
    for p in profiles[:5]:
      tf = p.get("trained_from") or "?"
      tt = p.get("trained_to") or "?"
      st.sidebar.caption(f"· `{p['id']}` {tf}→{tt}")
    if len(profiles) > 5:
      st.sidebar.caption(f"… +{len(profiles) - 5} profile")
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

  st.sidebar.title("ForexForge")
  st.sidebar.caption("EUR/USD H1 · Walk-forward · Self-learning v4")
  page = st.sidebar.radio("Điều hướng", list(PAGES.keys()))

  st.sidebar.divider()
  st.sidebar.markdown("**Pair** EUR/USD · **TF** H1")
  st.sidebar.markdown("**Data** Dukascopy 2022+")
  _sidebar_kb_profiles()
  st.sidebar.caption("Xem **KB & Giai đoạn** hoặc **Usage Guide**.")

  PAGES[page].render()


if __name__ == "__main__":
  main()
