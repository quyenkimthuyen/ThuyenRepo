"""UI quy trình live — stepper & hành động nhanh."""
from __future__ import annotations

import streamlit as st

from gui.live_workflow import (
  WORKFLOW_STEPS,
  apply_report_to_profile,
  assess_workflow,
  load_workflow_state,
  mark_paper_started,
  save_workflow_state,
)


def _status_icon(done: bool, active: bool) -> str:
  if done:
    return "✅"
  if active:
    return "▶️"
  return "○"


def _go(page: str, *, research_tab: str | None = None):
  st.session_state["nav_page"] = page
  if research_tab:
    st.session_state["research_tab"] = research_tab
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
      title = spec["title"] if not compact else spec["short"] if "short" in spec else f"B{sid}"
      st.markdown(f"**{icon} {title}**")
      if not compact:
        st.caption(spec["subtitle"])


def render_workflow_panel():
  """Panel chi tiết quy trình — Tổng quan."""
  wf = assess_workflow()
  cur = wf["current_step"]
  state = wf["state"]

  st.subheader("Quy trình trước khi live")
  st.caption(
    "Baseline KB OFF → thử KB ON → chọn combo ổn định → paper vài tuần → live nhỏ, scale dần."
  )
  render_workflow_stepper()

  spec = WORKFLOW_STEPS[cur - 1]
  info = wf["steps"][cur]
  st.markdown(f"### Bước {cur}: {spec['title']}")
  st.markdown(spec["detail"])
  st.info(f"**Tiến độ:** {info['progress']}")

  c1, c2 = st.columns(2)
  with c1:
    if st.button(f"▶ Làm bước {cur}", type="primary", use_container_width=True, key=f"wf_go_{cur}"):
      if cur == 1:
        from gui.trade_profile import set_active_trade_profile
        set_active_trade_profile(
          use_kb=False,
          kb_profile=None,
          kb_snapshot=None,
          source="workflow",
        )
      elif cur == 2:
        from gui.trade_profile import set_active_trade_profile
        set_active_trade_profile(use_kb=True, source="workflow")
      _go(spec["nav_page"], research_tab=spec.get("research_tab"))

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

  if cur == 3 and wf["ranked_reports"]:
    st.markdown("#### Gợi ý combo (xếp theo độ ổn định)")
    for e in wf["ranked_reports"][:5]:
      s = e.get("summary") or {}
      label = e.get("label", e["id"])
      chosen = state.get("chosen_report_id") == e["id"]
      badge = " · **đang chọn**" if chosen else ""
      cols = st.columns([4, 1])
      with cols[0]:
        st.markdown(
          f"**{label}**{badge}  \n"
          f"{s.get('total_r', '—')}R · DD {s.get('max_drawdown_r', '—')}R · "
          f"PF {s.get('profit_factor', '—')} · điểm **{e.get('stability', '—')}**"
        )
      with cols[1]:
        if st.button("Chọn", key=f"wf_pick_{e['id']}", use_container_width=True):
          out = apply_report_to_profile(e["id"])
          if out.get("ok"):
            st.toast(f"Đã áp dụng → {out.get('label')}")
            st.rerun()
          else:
            st.error(out.get("error"))

  if cur == 4:
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
    for spec in WORKFLOW_STEPS:
      sid = spec["id"]
      info = wf["steps"][sid]
      mark = "✅" if info["done"] else "○"
      st.markdown(f"{mark} **{sid}. {spec['title']}** — {info['progress']}")


def render_workflow_banner(*, page_step: int | None = None):
  """Banner ngắn trên Nghiên cứu / Paper."""
  wf = assess_workflow()
  cur = wf["current_step"]
  spec = WORKFLOW_STEPS[(page_step or cur) - 1]
  info = wf["steps"][spec["id"]]
  if info["done"] and page_step is None:
    return
  st.info(
    f"**Quy trình · Bước {spec['id']}/5:** {spec['title']} — {spec['detail']}  \n"
    f"_Tiến độ: {info['progress']}_"
  )


def render_baseline_hint():
  """Gợi ý bước 1 trên trang backtest."""
  wf = assess_workflow()
  if wf["steps"][1]["done"]:
    return
  tp_kb = st.session_state.get("tp_kb", True)
  if tp_kb:
    st.warning(
      "**Bước 1 — Baseline KB OFF:** Tắt «Dùng bộ nhớ kinh nghiệm» trong sidebar "
      "→ chạy backtest → bật **Lưu vào kho so sánh**."
    )
  else:
    st.success(
      "**Bước 1:** Profile đang KB OFF — chạy backtest và **lưu vào kho** để hoàn thành baseline."
    )
