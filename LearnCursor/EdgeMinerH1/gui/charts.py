"""Plotly chart helper — mọi biểu đồ phải có tên hiển thị riêng."""
from __future__ import annotations

import re
from typing import Any

import streamlit as st


def _slug_key(name: str) -> str:
  slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(name or "chart")).strip("_")
  return (slug or "chart")[:72]


def ensure_chart_title(fig, name: str):
  """Gán title layout nếu thiếu hoặc khác tên yêu cầu."""
  if fig is None or not name:
    return fig
  existing = ""
  try:
    title = fig.layout.title
    if title is not None:
      existing = str(getattr(title, "text", None) or "").strip()
  except Exception:
    existing = ""
  if existing != str(name).strip():
    fig.update_layout(title=dict(text=str(name)))
  return fig


def show_plotly(
  fig,
  name: str,
  *,
  key: str | None = None,
  use_container_width: bool = True,
  **kwargs: Any,
):
  """
  Hiển thị biểu đồ Plotly với **tên riêng** (title) và Streamlit key duy nhất.
  Dùng thay cho st.plotly_chart trong toàn app.
  """
  if fig is None:
    return
  ensure_chart_title(fig, name)
  chart_key = key or f"chart_{_slug_key(name)}"
  st.plotly_chart(
    fig,
    use_container_width=use_container_width,
    key=chart_key,
    **kwargs,
  )
