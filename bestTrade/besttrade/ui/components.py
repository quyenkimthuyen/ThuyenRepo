"""Reusable UI components."""

from __future__ import annotations

from typing import Any

import streamlit as st


def inject_styles(css: str) -> None:
    st.markdown(css, unsafe_allow_html=True)


def hero(title: str, subtitle: str, badges: list[str] | None = None) -> None:
    badges_html = "".join(f'<span class="bt-badge">{b}</span>' for b in (badges or []))
    st.markdown(
        f"""
        <div class="bt-hero">
            {badges_html}
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_grid(items: list[tuple[str, str, str]]) -> None:
    """Render metric cards. Third item: '', 'pos', 'neg', or 'accent'."""
    cards = []
    for label, value, tone in items:
        cls = f" value {tone}" if tone else " value"
        cards.append(
            f'<div class="bt-metric"><div class="label">{label}</div>'
            f'<div class="{cls.strip()}">{value}</div></div>'
        )
    st.markdown(f'<div class="bt-metric-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def validated_banner(text: str) -> None:
    st.markdown(f'<div class="bt-validated">✓ {text}</div>', unsafe_allow_html=True)


def strategy_card(title: str, body: str) -> None:
    st.markdown(
        f'<div class="bt-strategy-card"><h3>{title}</h3><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def fmt_pct(v: float, signed: bool = True) -> str:
    if signed:
        return f"{v:+.1%}"
    return f"{v:.1%}"


def fmt_money(v: float) -> str:
    return f"${v:,.2f}"


def trades_table_rows(trades: list) -> list[dict[str, Any]]:
    rows = []
    for t in trades:
        rows.append({
            "Entry": str(t.entry_time)[:16],
            "Exit": str(t.exit_time)[:16] if t.exit_time else "—",
            "Dir": "LONG" if t.direction == 1 else "SHORT",
            "PnL": round(t.pnl, 2),
            "Result": t.result or "—",
            "RR": round(getattr(t, "realized_rr", 0) or 0, 2),
        })
    return rows
