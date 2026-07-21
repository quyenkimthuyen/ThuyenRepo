"""Risk Dashboard — drawdown, streaks, risk of ruin."""
from __future__ import annotations

import streamlit as st

from gui.analysis_support import get_matching_analysis_report, render_report_required_panel
from gui.analysis_viz import default_risk_controls, render_risk_panel


def render(embedded: bool = False):
  if render_report_required_panel(key_prefix="risk_rep"):
    return

  report = get_matching_analysis_report()
  assert report is not None

  with st.expander("⚙️ Giả định rủi ro", expanded=False):
    risk_pct, max_weekly_r = default_risk_controls(report, key_prefix="risk_dash")

  render_risk_panel(report, risk_pct=risk_pct, max_weekly_r=max_weekly_r)

  st.caption(
    "Xác suất phá sản là **ước lượng thống kê** theo expectancy — "
    "không phải xác suất thực tế 100%."
  )
