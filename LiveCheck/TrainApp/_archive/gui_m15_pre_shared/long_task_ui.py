"""UI chung cho task chạy nền."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from gui.long_task_background import (
  cancel_task,
  dismiss_task,
  get_task_status,
  is_task_running,
  sync_completed_job_to_session,
)


@st.fragment(run_every=timedelta(seconds=3))
def _task_progress_fragment():
  """Poll tiến trình; khi task kết thúc → full rerun để hiện banner hoàn thành/lỗi."""
  status = get_task_status()
  if status["running"]:
    st.progress(
      status["done"] / max(status["total"], 1),
      text=(
        f"⏳ {status['job_label']} — {status['done']}/{status['total']} "
        f"({status['pct']}%) · {status['progress_text'] or '…'}"
      ),
    )
    return
  # Parent script still thinks task is running until a full remount.
  st.rerun()


def _dismiss_button(key_prefix: str):
  if st.button("✕ Bỏ qua", key=f"{key_prefix}_dismiss"):
    dismiss_task()
    st.rerun()


def render_task_status(
  *,
  key_prefix: str = "lt",
  show_cancel: bool = True,
  compact: bool = False,
) -> dict:
  """Hiển thị banner tiến trình task nền. Trả về status dict."""
  sync_completed_job_to_session()
  status = get_task_status()

  if status["status"] == "idle" and not status.get("job_id"):
    return status

  if status["running"]:
    if not compact:
      st.info(
        "Task đang chạy nền. Bạn có thể **chuyển tab/trang** mà không làm dừng task."
      )
    _task_progress_fragment()
    if show_cancel and st.button("⏹ Hủy task", key=f"{key_prefix}_cancel"):
      cancel_task()
      st.toast("Đã gửi tín hiệu hủy")
      st.rerun()
  elif status["status"] == "completed":
    res = status.get("result") or {}
    extra = ""
    if status["job_type"] == "backtest" and res.get("total_r") is not None:
      extra = f" · **{res['total_r']}R**"
    elif status["job_type"] == "learning" and res.get("kb_profile"):
      extra = f" · `{res['kb_profile']}`"
    elif status["job_type"] == "kb_then_grid":
      bits = []
      if res.get("run_id"):
        bits.append(f"`{res['run_id']}`")
      if res.get("n_ok") is not None:
        bits.append(f"{res['n_ok']}/{res.get('n_combos', '?')} combo")
      if res.get("best_total_r") is not None:
        bits.append(f"best **{res['best_total_r']}R**")
      if bits:
        extra = " · " + " · ".join(bits)
    elif status["job_type"] == "compare_trade":
      bits = []
      if res.get("run_id"):
        bits.append(f"`{res['run_id']}`")
      if res.get("n_models") is not None:
        bits.append(f"{res['n_models']} model")
      if res.get("bars_done") is not None:
        bits.append(f"{res['bars_done']}/{res.get('bars_total', '?')} bar")
      if bits:
        extra = " · " + " · ".join(bits)
    elif status["job_type"] == "remine_health":
      bits = []
      if res.get("remine_on_total_r") is not None:
        bits.append(f"ON **{res['remine_on_total_r']}R**")
      if res.get("remine_off_total_r") is not None:
        bits.append(f"OFF **{res['remine_off_total_r']}R**")
      if bits:
        extra = " · " + " · ".join(bits)
    elif status["job_type"] == "model_health":
      bits = []
      if res.get("kb_on_total_r") is not None:
        bits.append(f"KB ON **{res['kb_on_total_r']}R**")
      if res.get("kb_off_total_r") is not None:
        bits.append(f"OFF **{res['kb_off_total_r']}R**")
      if bits:
        extra = " · " + " · ".join(bits)
    elif status["job_type"] == "model_checks_suite":
      bits = []
      n = res.get("n_steps")
      if n is not None:
        bits.append(f"{n} bước")
      done = res.get("steps_done") or []
      if done:
        bits.append(" → ".join(str(x) for x in done))
      if bits:
        extra = " · " + " · ".join(bits)
    c1, c2 = st.columns([5, 1])
    with c1:
      st.success(f"✅ Hoàn thành **{status['job_label']}**{extra}")
    with c2:
      _dismiss_button(key_prefix)
  elif status["status"] == "cancelled":
    c1, c2 = st.columns([5, 1])
    with c1:
      st.warning(f"Đã hủy — {status['job_label']} ({status['done']}/{status['total']}).")
    with c2:
      _dismiss_button(key_prefix)
  elif status["status"] == "interrupted":
    c1, c2 = st.columns([5, 1])
    with c1:
      st.warning(
        f"⚠️ Task bị gián đoạn (restart server) — **{status['job_label']}** "
        f"({status['done']}/{status['total']}). Chạy lại nếu cần."
      )
    with c2:
      _dismiss_button(key_prefix)
  elif status["status"] == "error":
    c1, c2 = st.columns([5, 1])
    with c1:
      st.error(f"Lỗi **{status['job_label']}**: {status.get('error') or 'unknown'}")
    with c2:
      _dismiss_button(key_prefix)

  return status


def task_blocks_ui(key_prefix: str = "lt") -> bool:
  """True nếu đang có task chạy — dùng để disable nút Start."""
  return is_task_running()
