"""Tổng quan — data status, workflow, điều hướng nhanh."""
from __future__ import annotations

from datetime import date as date_cls
import html

import streamlit as st

from gui.desk_ui import desk_caption, tf_label
from gui.navigation import ALL_ITEMS
from gui.services import load_data_meta, refresh_market_data
from gui.ui_preferences import set_widget_preference
from gui.ui_theme import icon_btn
from gui.workflow_ui import render_workflow_panel


def _clamp_date(
  value: object,
  lo: date_cls,
  hi: date_cls,
  fallback: date_cls,
) -> date_cls:
  """Coerce anything a widget/config may hold into a date inside [lo, hi].

  st.date_input raises if its value falls outside min/max, so a stored DATA_START
  older than the picker floor took down the whole home page with no way to fix it
  from the UI. Streamlit also hands back a list when a range was ever rendered
  under the same key, hence the sequence unwrap.
  """
  if isinstance(value, (list, tuple)):
    value = value[0] if value else None
  if not isinstance(value, date_cls):
    try:
      value = date_cls.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
      value = fallback
  return min(max(value, lo), hi)


def _render_data_start_panel() -> None:
  """Chỉnh DATA_START + force sync."""
  from mt5_bridge.history_sync import (
    MIN_DATA_START,
    data_start_source,
    get_data_start_broker,
    get_history_status,
    set_data_start_broker,
    start_history_sync,
  )

  st.caption(
    "Muốn Simulate/Compare năm cũ: hạ DATA_START rồi **Áp dụng & lấy data**. "
    "Cần ForgeBridge EA + bridge service."
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
      text=f"Đang đồng bộ: {received}/{available or '?'} nến {tf_label()}",
    )
  elif history_data.get("bars"):
    m1, m2, m3 = st.columns(3)
    m1.metric("Nến cache", f"{int(history_data.get('bars') or 0):,}")
    m2.metric("Từ", str(history_data.get("start") or "?")[:10])
    m3.metric("DATA_START", f"{effective_start[:10]}")
    st.caption(f"Nguồn cấu hình: `{source}` · đến {str(history_data.get('end') or '?')[:16]}")
  else:
    st.warning("Chưa có lịch sử MT5.")

  lo = _clamp_date(MIN_DATA_START, date_cls(1990, 1, 1), date_cls.today(), date_cls(2010, 1, 1))
  hi = date_cls.today()
  configured = _clamp_date(effective_start, lo, hi, date_cls(2024, 1, 1))
  # Re-clamp on every run: session_state survives across reruns, so a value that
  # was valid under an older bound would keep crashing the widget otherwise.
  st.session_state["home_data_start"] = _clamp_date(
    st.session_state.get("home_data_start", configured), lo, hi, configured
  )
  raw_configured = str(effective_start)[:10]
  if raw_configured != st.session_state["home_data_start"].isoformat():
    st.warning(
      f"DATA_START đang lưu là **{raw_configured}**, ngoài khoảng chọn được "
      f"({lo} → {hi}). Ô dưới đã kẹp về khoảng hợp lệ — bấm **Áp dụng & lấy data** "
      "mới ghi đè giá trị đang lưu."
    )

  c1, c2, c3 = st.columns([2.2, 1.4, 1.4])
  with c1:
    st.date_input(
      "DATA_START",
      key="home_data_start",
      min_value=lo,
      max_value=hi,
    )
  with c2:
    if st.button(
      "Áp dụng & lấy data",
      type="primary",
      key="home_data_start_apply",
      use_container_width=True,
    ):
      chosen = _clamp_date(st.session_state.get("home_data_start"), lo, hi, configured)
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
  with c3:
    if st.button("Đồng bộ lại", key="home_history_resync", use_container_width=True):
      start_history_sync(force=True)
      st.rerun()


def render():
  from gui.page_chrome import render_page_header

  render_page_header(ALL_ITEMS["home"], show_profile=False)

  desk = html.escape(desk_caption())
  try:
    st.html(
      f"""
<div class="ff-home-hero">
  <h2>{desk}</h2>
  <p>Một luồng: đồng bộ data → học & tối ưu → Trade Model → Compare → Bridge Live/Sim.</p>
</div>
"""
    )
  except Exception:
    st.markdown(
      f"""
<div class="ff-home-hero">
  <h2>{desk}</h2>
  <p>Một luồng: đồng bộ data → học & tối ưu → Trade Model → Compare → Bridge Live/Sim.</p>
</div>
""",
      unsafe_allow_html=True,
    )

  data_meta = load_data_meta()
  if not data_meta.get("bars"):
    st.error(
      "**Chưa có lịch sử MT5** — giữ XM MT5 + ForgeBridge đang chạy rồi "
      "dùng panel **DATA_START** bên dưới."
    )
  else:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Nến", f"{int(data_meta.get('bars') or 0):,}")
    k2.metric("Broker", str(data_meta.get("broker") or "?"))
    k3.metric("Từ", str(data_meta.get("start") or "?")[:10])
    k4.metric("Gap", str(data_meta.get("gap_count", 0)))

  st.markdown("##### Lịch sử MT5 · DATA_START")
  _render_data_start_panel()

  render_workflow_panel()

  st.markdown("##### Đi tới")
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
    if icon_btn("Live Trade", key="cc_nav_bridge", icon=":material/monitoring:"):
      set_widget_preference("nav_page", "live_trade", "navigation.page")
      st.rerun()
  with c4:
    if icon_btn("Đồng bộ MT5", key="cc_refresh", icon=":material/sync:"):
      with st.spinner("Gửi yêu cầu lịch sử tới ForgeBridge EA..."):
        refresh_market_data()
      st.success("Đã bắt đầu đồng bộ lịch sử MT5.")
      st.rerun()
