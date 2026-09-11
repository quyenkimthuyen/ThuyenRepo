"""Shared page chrome — header gọn + Bridge (runtime) hoặc Active (Trade Models)."""
from __future__ import annotations

import streamlit as st

from gui.navigation import NavItem


def render_page_header(
  item: NavItem,
  *,
  show_profile: bool = True,
  show_workspace: bool | None = None,
  compact_workspace: bool = True,
):
  """Tiêu đề trang + strip model (Bridge runtime hoặc Active phân tích)."""
  if show_workspace is not None:
    show_profile = show_workspace
  title = f"{item.icon} {item.label}" if getattr(item, "icon", None) else item.label
  st.header(title)
  if item.hint:
    st.caption(item.hint)
  if show_profile:
    render_profile_strip(compact=compact_workspace)


def render_profile_strip(*, compact: bool = True):
  from gui.trade_model import (
    format_model_oneline,
    format_model_short,
    get_active_trade_model,
    get_bridge_runtime_model_ids,
    get_model_by_id,
  )

  nav = st.session_state.get("nav_page") or ""

  # Trade Models: Active = model đang phân tích (không phải runtime Bridge).
  if nav == "models":
    m = get_active_trade_model()
    if not m:
      st.caption("📦 Active (phân tích): _chưa chọn_")
      return
    line = format_model_oneline(m)
    prefix = "📦 Active (phân tích): "
    if compact:
      st.caption(f"{prefix}{line}")
    else:
      st.info(f"{prefix}{line}")
    return

  # Runtime pages: show Bridge roster only.
  bridge_ids = get_bridge_runtime_model_ids()
  if nav in ("mt5_bridge", "live_trade", "live_trade_dash", "compare_trade", "home"):
    if len(bridge_ids) > 1:
      parts = []
      for mid in bridge_ids[:5]:
        bm = get_model_by_id(mid)
        parts.append(format_model_short(bm, max_len=28) if bm else mid[:16])
      line = f"{len(bridge_ids)} model · " + " · ".join(parts)
      text = f"📦 Bridge: {line}"
    elif len(bridge_ids) == 1:
      bm = get_model_by_id(bridge_ids[0])
      line = format_model_oneline(bm) if bm else bridge_ids[0]
      text = f"📦 Bridge: {line}"
    else:
      text = "📦 Bridge: _chưa chọn roster — mở MT5 Bridge_"
    if compact:
      st.caption(text)
    else:
      st.info(text)
    return

  # Other pages: Bridge if set, else quiet.
  if bridge_ids:
    if len(bridge_ids) == 1:
      bm = get_model_by_id(bridge_ids[0])
      line = format_model_short(bm) if bm else bridge_ids[0][:24]
      st.caption(f"📦 Bridge: {line}")
    else:
      st.caption(f"📦 Bridge: {len(bridge_ids)} model")


# Alias tương thích
render_workspace_strip = render_profile_strip


def render_workflow_cards():
  """Deprecated — Tổng quan dùng nút điều hướng riêng."""
  return
