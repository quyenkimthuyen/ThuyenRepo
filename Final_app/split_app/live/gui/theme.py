"""Trader-desk visual theme for Live Streamlit UI."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [class*="css"] {
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
}

.block-container {
  padding-top: 1.1rem;
  padding-bottom: 2rem;
  max-width: 1180px;
}

/* Hide Streamlit chrome noise */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

h1, h2, h3 { letter-spacing: -0.02em; font-weight: 600; }

.desk-top {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.desk-brand {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0;
  line-height: 1.1;
}
.desk-sub {
  margin: 0.2rem 0 0 0;
  font-size: 0.92rem;
  opacity: 0.72;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.desk-clock {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.85rem;
  opacity: 0.55;
  text-align: right;
}

.pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin: 0.35rem 0 0.9rem 0;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.28rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
  font-family: "IBM Plex Sans", sans-serif;
}
.pill .dot {
  width: 0.45rem; height: 0.45rem; border-radius: 50%;
  background: currentColor;
}
.pill-ok { background: rgba(34, 160, 107, 0.16); color: #3dd68c; border-color: rgba(61,214,140,0.25); }
.pill-warn { background: rgba(214, 158, 46, 0.16); color: #e6b84d; border-color: rgba(230,184,77,0.28); }
.pill-danger { background: rgba(220, 68, 68, 0.16); color: #ff6b6b; border-color: rgba(255,107,107,0.28); }
.pill-muted { background: rgba(148, 163, 184, 0.12); color: #94a3b8; border-color: rgba(148,163,184,0.2); }

.panel {
  background: linear-gradient(160deg, rgba(22, 32, 45, 0.95), rgba(14, 20, 30, 0.98));
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 1rem 1.1rem 1.05rem;
  margin-bottom: 0.75rem;
}
.panel-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.55;
  margin-bottom: 0.35rem;
  font-weight: 600;
}
.decision-action {
  font-size: 2.4rem;
  font-weight: 700;
  line-height: 1;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  letter-spacing: -0.04em;
}
.decision-long { color: #3dd68c; }
.decision-short { color: #ff6b6b; }
.decision-flat { color: #94a3b8; }
.decision-unknown { color: #cbd5e1; }
.decision-meta {
  margin-top: 0.55rem;
  font-size: 0.88rem;
  opacity: 0.78;
  line-height: 1.45;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem 1rem;
}
.stat-k {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.5;
  font-weight: 600;
}
.stat-v {
  font-size: 1.35rem;
  font-weight: 650;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  letter-spacing: -0.02em;
}
.stat-v.pos { color: #3dd68c; }
.stat-v.neg { color: #ff6b6b; }

.model-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px;
  padding: 0.65rem 0.8rem;
  margin-bottom: 0.4rem;
}
.model-title {
  font-weight: 600;
  font-size: 0.95rem;
}
.model-meta {
  font-size: 0.8rem;
  opacity: 0.65;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  margin-top: 0.15rem;
}

.health-book {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
  margin-bottom: 0.55rem;
}
.health-book-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.35rem 0.75rem;
  margin-bottom: 0.35rem;
}
.health-book-title {
  font-weight: 650;
  font-size: 0.95rem;
}
.health-book-meta {
  font-size: 0.78rem;
  opacity: 0.7;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.health-model {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) auto auto auto;
  gap: 0.25rem 0.65rem;
  align-items: center;
  padding: 0.28rem 0;
  border-top: 1px solid rgba(255,255,255,0.05);
  font-size: 0.82rem;
}
.health-model:first-of-type { border-top: none; }
.health-flag {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.health-flag-ok { background: rgba(34,160,107,0.18); color: #3dd68c; }
.health-flag-warn { background: rgba(214,158,46,0.18); color: #e6b84d; }
.health-flag-danger { background: rgba(220,68,68,0.18); color: #ff6b6b; }
.health-flag-muted { background: rgba(148,163,184,0.12); color: #94a3b8; }
.health-alert {
  font-size: 0.8rem;
  padding: 0.35rem 0.55rem;
  border-radius: 8px;
  margin: 0.25rem 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.health-alert-warn { background: rgba(214,158,46,0.12); color: #e6b84d; }
.health-alert-danger { background: rgba(220,68,68,0.12); color: #ff6b6b; }

.hint {
  font-size: 0.82rem;
  opacity: 0.65;
  margin: 0.2rem 0 0.6rem 0;
}

div[data-testid="stTabs"] button[role="tab"] {
  font-weight: 500;
}

/* Stable nav + action row */
div[data-testid="stHorizontalBlock"] {
  align-items: flex-start;
}
div[data-testid="stHorizontalBlock"] .stButton > button {
  min-height: 2.5rem;
  width: 100%;
}
div[role="radiogroup"] {
  gap: 0.35rem 0.75rem;
  margin: 0.35rem 0 0.85rem 0;
}

/* Primary action emphasis */
div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"] {
  font-weight: 650;
}
</style>
"""


def inject_theme() -> None:
  """Inject CSS on every script run.

  Streamlit rebuilds the page DOM each interaction; skipping inject after the
  first run (via session_state) drops styles until a full browser refresh.
  """
  st.markdown(_CSS, unsafe_allow_html=True)


def pill(label: str, tone: str = "muted") -> str:
  return f'<span class="pill pill-{tone}"><span class="dot"></span>{label}</span>'


def r_class(val: float | int | None) -> str:
  try:
    v = float(val or 0)
  except (TypeError, ValueError):
    return ""
  if v > 0:
    return "pos"
  if v < 0:
    return "neg"
  return ""
