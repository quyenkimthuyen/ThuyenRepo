"""UI quy trình live — stepper & hành động nhanh."""
from __future__ import annotations

import streamlit as st

from gui.live_workflow import (
  WORKFLOW_STEPS,
  assess_workflow,
  mark_paper_started,
  save_workflow_state,
)


def _status_icon(done: bool, active: bool) -> str:
  if done:
    return "✅"
  if active:
    return "▶️"
  return "○"


def _go(page: str, *, learning_tab: str | None = None):
  st.session_state["nav_page"] = page
  if learning_tab:
    st.session_state["learning_tab"] = learning_tab
  st.rerun()


def render_workflow_stepper(*, compact: bool = False):
  """Thanh 5 bước — dùng trên Tổng quan."""
  wf = assess_workflow()
  cur = wf["current_step"]
  cols = st.columns(len(WORKFLOW_STEPS))
  for col, spec in zip(cols, WORKFLOW_STEPS):
    sid = spec["id"]
    info = wf["steps"][sid]
    with col:
      icon = _status_icon(info["done"], sid == cur and not info["done"])
      title = spec["title"] if not compact else spec.get("short", f"B{sid}")
      st.markdown(f"**{icon} {title}**")
      if not compact:
        st.caption(spec["subtitle"])


def render_workflow_panel():
  """Panel quy trình gọn — một stepper + một CTA."""
  wf = assess_workflow()
  cur = wf["current_step"]
  state = wf["state"]
  spec = WORKFLOW_STEPS[cur - 1]
  info = wf["steps"][cur]

  st.subheader("Quy trình trước khi live")
  render_workflow_stepper()

  st.markdown(f"**Bước {cur}: {spec['title']}** — {spec['detail']}")
  st.caption(f"Tiến độ: {info['progress']}")

  c1, c2 = st.columns(2)
  with c1:
    if st.button(f"▶ Làm bước {cur}", type="primary", use_container_width=True, key=f"wf_go_{cur}"):
      _go(spec["nav_page"], learning_tab=spec.get("learning_tab"))
  with c2:
    if not info["done"] and st.button(
      "✓ Đánh dấu xong",
      use_container_width=True,
      key=f"wf_done_{cur}",
    ):
      manual = dict(state.get("manual") or {})
      manual[str(cur)] = True
      state["manual"] = manual
      save_workflow_state(state)
      st.toast(f"Đã đánh dấu bước {cur}")
      st.rerun()

  if cur == 4 and not state.get("paper_started_at"):
    if st.button("📡 Bắt đầu theo dõi paper", use_container_width=True, key="wf_paper_start"):
      mark_paper_started()
      _go("paper")

  if cur == 5:
    notes = st.text_area(
      "Ghi chú live (size, broker, ngày bắt đầu…)",
      value=state.get("live_notes") or "",
      key="wf_live_notes",
    )
    if st.button("Lưu ghi chú live", key="wf_save_live"):
      state["live_notes"] = notes.strip()
      manual = dict(state.get("manual") or {})
      manual["5"] = True
      state["manual"] = manual
      save_workflow_state(state)
      st.toast("Đã lưu")
      st.rerun()

  with st.expander("Tất cả các bước", expanded=False):
    for step in WORKFLOW_STEPS:
      sid = step["id"]
      sinfo = wf["steps"][sid]
      mark = "✅" if sinfo["done"] else "○"
      st.markdown(f"{mark} **{sid}. {step['title']}** — {sinfo['progress']}")


def render_workflow_banner(*, page_step: int | None = None):
  """Banner ngắn trên Paper (chỉ khi chưa xong bước đó)."""
  wf = assess_workflow()
  cur = wf["current_step"]
  spec = WORKFLOW_STEPS[(page_step or cur) - 1]
  info = wf["steps"][spec["id"]]
  if info["done"] and page_step is None:
    return
  st.caption(f"Quy trình · Bước {spec['id']}/5: **{spec['title']}** — {info['progress']}")


def render_baseline_hint():
  """Deprecated — không còn bước KB OFF."""
  return
