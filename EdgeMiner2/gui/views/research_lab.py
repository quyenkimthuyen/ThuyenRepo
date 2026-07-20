"""Nghiên cứu — hub thống nhất: backtest, grid search, so sánh."""
from __future__ import annotations

import streamlit as st

from gui.page_chrome import render_page_header
from gui.navigation import ALL_ITEMS
from gui.views import backtest_lab, grid_search, report_compare
from gui.views.compare_sections import render_era_compare, render_epoch_sweep, render_train_window


TAB_KEYS = ["backtest", "grid", "era", "epoch", "train", "reports"]
TAB_LABELS = {
  "backtest": "📊 Kiểm chứng",
  "grid": "🔎 Tìm tham số",
  "era": "⚖️ So giai đoạn",
  "epoch": "📈 So vòng học",
  "train": "⏱ So cửa sổ học",
  "reports": "📁 Lưu & so sánh",
}


def _render_subview(module):
  """Gọi render() — hỗ trợ cả bản cũ không có tham số embedded."""
  import inspect
  sig = inspect.signature(module.render)
  if "embedded" in sig.parameters:
    module.render(embedded=True)
  else:
    module.render()


def render():
  item = ALL_ITEMS["research"]
  render_page_header(item)

  st.markdown(
    "Một nơi để **kiểm chứng chiến lược**: chạy backtest, tìm tham số tốt hơn, "
    "so sánh giai đoạn / vòng học / cửa sổ học."
  )

  from gui.workflow_ui import render_workflow_banner
  render_workflow_banner()

  from gui.long_task_ui import render_task_status
  render_task_status(key_prefix="research_hub", compact=True)

  default_tab = st.session_state.get("research_tab", "backtest")
  if default_tab not in TAB_KEYS:
    default_tab = "backtest"
  tab_idx = TAB_KEYS.index(default_tab)

  selected_label = st.radio(
    "Công cụ",
    [TAB_LABELS[k] for k in TAB_KEYS],
    horizontal=True,
    index=tab_idx,
    key="research_tab_radio",
  )
  selected = TAB_KEYS[[TAB_LABELS[k] for k in TAB_KEYS].index(selected_label)]
  st.session_state["research_tab"] = selected

  st.divider()

  st.session_state["_research_hub"] = True
  try:
    if selected == "backtest":
      _render_subview(backtest_lab)
    elif selected == "grid":
      _render_subview(grid_search)
    elif selected == "era":
      render_era_compare()
    elif selected == "epoch":
      render_epoch_sweep()
    elif selected == "train":
      render_train_window()
    else:
      _render_subview(report_compare)
  finally:
    st.session_state.pop("_research_hub", None)
