"""Tổng quan — tiến độ quy trình + điều hướng nhanh."""
from __future__ import annotations

from datetime import date as date_cls

import streamlit as st

from gui.navigation import ALL_ITEMS
from gui.services import load_data_meta, refresh_market_data
from gui.ui_preferences import set_widget_preference
from gui.workflow_ui import render_workflow_panel


def _render_data_start_panel() -> None:
  """Chỉnh DATA_START + force sync — đặt ngay trên Tổng quan cho dễ thấy."""
  from mt5_bridge.history_sync import (
    data_start_source,
    get_data_start_broker,
    get_history_status,
    set_data_start_broker,
    start_history_sync,
  )

  st.subheader("Lịch sử MT5 · DATA_START")
  st.caption(
    "Muốn Simulate/Compare năm cũ (vd 2023): hạ DATA_START rồi "
    "**Áp dụng & lấy data**. Cần ForgeBridge EA + bridge service."
  )

  history = get_history_status()
  history_data = history.get("data") or {}
  received = int(history.get("received_bars") or 0)
  available = int(history.get("available_bars") or 0)
  effective_start = get_data_start_broker()
  source = data_start_source()

  if history.get("state") in ("requesting", "receiving"):
    st.progress(
      received / max(available, 1),
      text=f"Đang đồng bộ: {received}/{available or '?'} nến M5",
    )
  elif history_data.get("bars"):
    st.info(
      f"Cache: **{history_data.get('bars')} nến** · "
      f"{str(history_data.get('start'))[:10]} → {str(history_data.get('end'))[:16]} · "
      f"DATA_START **{effective_start[:10]}** (`{source}`)"
    )
  else:
    st.warning("Chưa có lịch sử MT5.")

  try:
    default_start = date_cls.fromisoformat(str(effective_start)[:10])
  except ValueError:
    default_start = date_cls(2024, 1, 1)
  if "home_data_start" not in st.session_state:
    st.session_state["home_data_start"] = default_start

  c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
  with c1:
    st.date_input(
      "DATA_START",
      key="home_data_start",
      min_value=date_cls(2018, 1, 1),
      max_value=date_cls.today(),
    )
  with c2:
    st.caption(f"Hiện hành: **{effective_start[:10]}** · `{source}`")
  with c3:
    if st.button("Áp dụng & lấy data", type="primary", key="home_data_start_apply",
                 use_container_width=True):
      chosen = st.session_state.get("home_data_start") or default_start
      result = set_data_start_broker(f"{chosen} 00:00", sync=True)
      try:
        from gui.services import _clear_ohlc_streamlit_cache
        _clear_ohlc_streamlit_cache()
      except Exception:
        pass
      if result.get("env_overrides"):
        st.warning(
          f"Env `EDGEMINER_DATA_START` đang ghi đè → **{result['effective']}**"
        )
      else:
        st.success(f"DATA_START = **{result['data_start']}** — đang đồng bộ…")
      st.rerun()
  with c4:
    if st.button("Đồng bộ lại", key="home_history_resync", use_container_width=True):
      start_history_sync(force=True)
      st.rerun()


def render():
  from gui.page_chrome import render_page_header
  render_page_header(ALL_ITEMS["home"], show_profile=False)

  data_meta = load_data_meta()
  if not data_meta.get("bars"):
    st.error(
      "**Chưa có lịch sử MT5** — giữ XM MT5 + ForgeBridge đang chạy rồi "
      "dùng panel **DATA_START** bên dưới."
    )
  else:
    st.caption(
      f"Nguồn dữ liệu: **MT5 EA · {data_meta.get('broker') or '?'}** · "
      f"{data_meta.get('bars', 0)} nến M5 · "
      f"{str(data_meta.get('start') or '?')[:10]} → {str(data_meta.get('end') or '?')[:16]} · "
      f"gap: {data_meta.get('gap_count', 0)}"
    )

  _render_data_start_panel()
  st.divider()

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
