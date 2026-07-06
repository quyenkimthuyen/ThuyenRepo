"""Lightweight Charts Streamlit renderer."""

from __future__ import annotations

import json
from typing import Any

import streamlit.components.v1 as components

from systemtrain.ui.chart_component.template import build_chart_html


def render_lightweight_chart(
    payload: dict[str, Any],
    *,
    height: int,
    key: str,
) -> None:
    """Render a TradingView-like chart inside Streamlit."""
    html = build_chart_html(json.dumps(payload, ensure_ascii=False), height=height)
    components.html(html, height=height + 70, scrolling=False)
