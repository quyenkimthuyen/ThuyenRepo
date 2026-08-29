"""Shared page chrome — header + Bridge/Active strip."""
from __future__ import annotations

import html

import streamlit as st

from gui.navigation import NavItem


def _html(body: str) -> None:
  try:
    st.html(body)
  except Exception:
    st.markdown(body, unsafe_allow_html=True)


def render_page_header(
  item: NavItem,
  *,
  show_profile: bool = True,
  show_workspace: bool | None = None,
  compact_workspace: bool = True,
  kicker: str | None = None,
):
  """Tiêu đề trang + strip model (Bridge runtime hoặc Active phân tích)."""
  if show_workspace is not None:
    show_profile = show_workspace

  try:
    from gui.desk_ui import desk_caption
    desk = desk_caption()
  except Exception:
    desk = "Train"

  label = html.escape(item.label)
  hint = html.escape(item.hint or "")
  kick = html.escape(kicker or desk)
  hint_html = f'<p class="ff-page-hint">{hint}</p>' if item.hint else ""

  _html(
    f"""
<div class="ff-page-head">
  <p class="ff-page-kicker">{kick}</p>
  <h1 class="ff-page-title">{label}</h1>
  {hint_html}
</div>
"""
  )
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

  def _strip(text: str) -> None:
    _html(f'<div class="ff-strip">{html.escape(text)}</div>')

  if nav == "models":
    m = get_active_trade_model()
    if not m:
      _strip("Active (phân tích): chưa chọn")
      return
    _strip(f"Active (phân tích): {format_model_oneline(m)}")
    return

  bridge_ids = get_bridge_runtime_model_ids()
  if nav in ("mt5_bridge", "live_trade", "live_trade_dash", "compare_trade", "home"):
    if len(bridge_ids) > 1:
      parts = []
      for mid in bridge_ids[:5]:
        bm = get_model_by_id(mid)
        parts.append(format_model_short(bm, max_len=28) if bm else mid[:16])
      line = f"{len(bridge_ids)} model · " + " · ".join(parts)
      _strip(f"Bridge: {line}")
    elif len(bridge_ids) == 1:
      bm = get_model_by_id(bridge_ids[0])
      line = format_model_oneline(bm) if bm else bridge_ids[0]
      _strip(f"Bridge: {line}")
    else:
      _strip("Bridge: chưa chọn roster — mở MT5 Bridge")
    return

  if bridge_ids:
    if len(bridge_ids) == 1:
      bm = get_model_by_id(bridge_ids[0])
      line = format_model_short(bm) if bm else bridge_ids[0][:24]
      _strip(f"Bridge: {line}")
    else:
      _strip(f"Bridge: {len(bridge_ids)} model")


render_workspace_strip = render_profile_strip


def render_workflow_cards():
  """Deprecated — Tổng quan dùng nút điều hướng riêng."""
  return
