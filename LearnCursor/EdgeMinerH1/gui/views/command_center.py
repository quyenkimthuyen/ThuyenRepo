"""Tổng quan — tiến độ quy trình + điều hướng nhanh."""
from __future__ import annotations

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.services import load_data_meta, refresh_market_data
from gui.ui_preferences import set_widget_preference
from gui.workflow_ui import render_workflow_panel


def render():
  from gui.page_chrome import render_page_header
  render_page_header(ALL_ITEMS["home"], show_profile=False)

  data_meta = load_data_meta()
  if not data_meta.get("bars"):
    st.error(
      "**Chưa có lịch sử MT5** — giữ XM MT5 + ForgeBridge đang chạy rồi bấm "
      "**Đồng bộ MT5**."
    )
  else:
    st.caption(
      f"Nguồn dữ liệu: **MT5 EA · {data_meta.get('broker') or '?'}** · "
      f"{data_meta.get('bars', 0)} nến H1 · "
      f"{str(data_meta.get('start') or '?')[:10]} → {str(data_meta.get('end') or '?')[:16]} · "
      f"gap: {data_meta.get('gap_count', 0)}"
    )

  render_workflow_panel()

  from gui.ui_theme import icon_btn

  st.subheader("Đi tới")
  c1, c2, c3, c4 = st.columns(4)
  with c1:
    if icon_btn("Học & tối ưu", key="cc_nav_learning", icon=":material/school:"):
      set_widget_preference("nav_page", "learning", "navigation.page")
      from gui.views.learning_hub import _default_learning_tab
      set_widget_preference(
        "learning_tab", _default_learning_tab(), "navigation.learning_tab",
      )
      st.rerun()
  with c2:
    if icon_btn("Trade Models", key="cc_nav_models", icon=":material/inventory_2:"):
      set_widget_preference("nav_page", "models", "navigation.page")
      set_widget_preference("models_subtab", "info", "navigation.models_subtab")
      st.rerun()
  with c3:
    if icon_btn("MT5 Bridge", key="cc_nav_bridge", icon=":material/hub:"):
      set_widget_preference("nav_page", "mt5_bridge", "navigation.page")
      st.rerun()
  with c4:
    if icon_btn("Đồng bộ MT5", key="cc_refresh", icon=":material/sync:"):
      with st.spinner("Gửi yêu cầu lịch sử tới ForgeBridge EA..."):
        refresh_market_data()
      st.success("Đã bắt đầu đồng bộ lịch sử MT5.")
      st.rerun()
