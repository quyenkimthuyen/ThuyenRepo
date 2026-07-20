"""UI chung cho task chạy nền."""
from __future__ import annotations

from datetime import timedelta

import streamlit as st

from gui.long_task_background import (
  cancel_task,
  get_task_status,
  is_task_running,
  sync_completed_job_to_session,
)


@st.fragment(run_every=timedelta(seconds=3))
def _task_progress_fragment():
  if is_task_running():
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
    if compact:
      st.caption(
        f"⏳ **{status['job_label']}** — {status['done']}/{status['total']} "
        f"({status['pct']}%) · {status['progress_text'] or '…'}"
      )
    else:
      st.info(
        f"⏳ **{status['job_label']}** đang chạy nền — "
        f"{status['done']}/{status['total']} ({status['pct']}%) · "
        f"`{status['progress_text'] or '…'}`\n\n"
        "Bạn có thể **chuyển tab/trang** — task **không bị dừng**."
      )
    st.progress(status["done"] / max(status["total"], 1))
    if show_cancel and st.button("⏹ Hủy task", key=f"{key_prefix}_cancel"):
      cancel_task()
      st.toast("Đã gửi tín hiệu hủy")
      st.rerun()
    _task_progress_fragment()
  elif status["status"] == "completed":
    res = status.get("result") or {}
    extra = ""
    if status["job_type"] == "backtest" and res.get("total_r") is not None:
      extra = f" · **{res['total_r']}R**"
    st.success(f"✅ Hoàn thành **{status['job_label']}**{extra}")
  elif status["status"] == "cancelled":
    st.warning(f"Đã hủy — {status['job_label']} ({status['done']}/{status['total']}).")
  elif status["status"] == "interrupted":
    st.warning(
      f"⚠️ Task bị gián đoạn (restart server?) — {status['job_label']}. "
      "Chạy lại nếu cần."
    )
  elif status["status"] == "error":
    st.error(f"Lỗi **{status['job_label']}**: {status.get('error') or 'unknown'}")

  return status


def task_blocks_ui(key_prefix: str = "lt") -> bool:
  """True nếu đang có task chạy — dùng để disable nút Start."""
  return is_task_running()
