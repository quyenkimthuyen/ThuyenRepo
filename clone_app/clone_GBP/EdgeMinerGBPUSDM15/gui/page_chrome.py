"""Shared page chrome — header gọn + Trade Model."""
from __future__ import annotations

import streamlit as st

from gui.navigation import NavItem
from gui.trade_model import format_model_oneline, get_active_trade_model


def render_page_header(
  item: NavItem,
  *,
  show_profile: bool = True,
  show_workspace: bool | None = None,
  compact_workspace: bool = True,
):
  """Tiêu đề trang + trade model một dòng."""
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
  bridge_ids = get_bridge_runtime_model_ids()
  if nav in ("mt5_bridge", "live_trade", "live_trade_dash") and len(bridge_ids) > 1:
    parts = []
    for mid in bridge_ids[:5]:
      bm = get_model_by_id(mid)
      parts.append(format_model_short(bm, max_len=28) if bm else mid[:16])
    line = f"{len(bridge_ids)} model · " + " · ".join(parts)
    if compact:
      st.caption(f"📦 Bridge: {line}")
    else:
      st.info(f"📦 Bridge: {line}")
    return

  m = get_active_trade_model()
  if not m:
    st.caption("📦 _Chưa chọn trade model_")
    return
  line = format_model_oneline(m)
  if compact:
    st.caption(f"📦 {line}")
  else:
    st.info(f"📦 {line}")


# Alias tương thích
render_workspace_strip = render_profile_strip


def render_workflow_cards():
  """Deprecated — Tổng quan dùng nút điều hướng riêng."""
  return
