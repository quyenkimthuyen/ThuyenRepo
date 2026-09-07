"""UI theme — ForexForge desk chrome (typography, color, density)."""
from __future__ import annotations

import streamlit as st

_CSS_VERSION = "ff_theme_v4"

# Steel / forge — cool neutrals + teal accent.
# Inject via st.html (not markdown) so <style> is not sanitized away.
# Avoid [class*="css"] font overrides — that breaks Streamlit Material icons.
_THEME_CSS = """
<style>
:root {
  --ff-ink: #12181f;
  --ff-muted: #5a6875;
  --ff-line: #d5dde5;
  --ff-surface: #f3f5f7;
  --ff-panel: #ffffff;
  --ff-accent: #0e6b6d;
  --ff-accent-deep: #0a4f51;
  --ff-accent-soft: rgba(14, 107, 109, 0.12);
  --ff-sidebar: #e9eef2;
  --ff-radius: 10px;
  --ff-font: "Segoe UI", Candara, Calibri, sans-serif;
  --ff-display: "Palatino Linotype", "Book Antiqua", Georgia, serif;
}

.stApp {
  background:
    radial-gradient(1200px 480px at 12% -8%, rgba(14, 107, 109, 0.10), transparent 55%),
    radial-gradient(900px 420px at 100% 0%, rgba(18, 24, 31, 0.05), transparent 50%),
    linear-gradient(180deg, #eef2f5 0%, var(--ff-surface) 42%, #f7f8fa 100%) !important;
  color: var(--ff-ink);
  font-family: var(--ff-font);
}

[data-testid="stHeader"] {
  background: transparent !important;
}

.block-container {
  padding-top: 1.15rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1280px;
}

section[data-testid="stSidebar"] {
  background:
    linear-gradient(185deg, #e4ebf0 0%, var(--ff-sidebar) 38%, #eef2f5 100%) !important;
  border-right: 1px solid var(--ff-line) !important;
}
section[data-testid="stSidebar"] > div {
  padding-top: 0.75rem;
}
section[data-testid="stSidebar"] .stButton > button {
  justify-content: flex-start;
  text-align: left;
  padding: 0.42rem 0.7rem;
  min-height: 2.15rem;
  font-weight: 500;
  font-size: 0.92rem;
  gap: 0.45rem;
  border-radius: 8px !important;
  border: 1px solid transparent !important;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.12s ease;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  border-color: var(--ff-line) !important;
  transform: translateX(2px);
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
  background: var(--ff-accent) !important;
  border-color: var(--ff-accent-deep) !important;
  color: #fff !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ff-muted);
  margin: 0.55rem 0 0.3rem 0;
  font-weight: 600;
}
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
  gap: 0.18rem;
}

.ff-brand {
  padding: 0.35rem 0.15rem 0.85rem 0.15rem;
  margin-bottom: 0.25rem;
  border-bottom: 1px solid var(--ff-line);
}
.ff-brand-mark {
  font-family: var(--ff-display);
  font-weight: 700;
  font-size: 1.55rem;
  letter-spacing: -0.03em;
  color: var(--ff-ink);
  line-height: 1.1;
  margin: 0;
}
.ff-brand-mark span { color: var(--ff-accent); }
.ff-brand-desk {
  margin-top: 0.35rem;
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ff-accent-deep);
  background: var(--ff-accent-soft);
  border: 1px solid rgba(14, 107, 109, 0.22);
  padding: 0.22rem 0.55rem;
  border-radius: 6px;
}
.ff-brand-hint {
  margin-top: 0.45rem;
  font-size: 0.78rem;
  color: var(--ff-muted);
  line-height: 1.35;
}

.ff-page-head {
  margin: 0 0 0.85rem 0;
  padding: 0.15rem 0 0.85rem 0;
  border-bottom: 1px solid var(--ff-line);
}
.ff-page-kicker {
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ff-accent);
  margin: 0 0 0.25rem 0;
}
.ff-page-title {
  font-family: var(--ff-display);
  font-size: 1.85rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ff-ink);
  margin: 0;
  line-height: 1.15;
}
.ff-page-hint {
  margin: 0.4rem 0 0 0;
  color: var(--ff-muted);
  font-size: 0.92rem;
  line-height: 1.4;
  max-width: 52rem;
}
.ff-strip {
  margin-top: 0.55rem;
  padding: 0.45rem 0.7rem;
  background: var(--ff-panel);
  border: 1px solid var(--ff-line);
  border-radius: 8px;
  font-size: 0.84rem;
  color: var(--ff-ink);
}

.ff-home-hero {
  display: grid;
  gap: 0.35rem;
  margin-bottom: 1rem;
  padding: 1rem 1.15rem 1.1rem;
  background:
    linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.72)),
    linear-gradient(120deg, rgba(14,107,109,0.08), transparent 55%);
  border: 1px solid var(--ff-line);
  border-radius: var(--ff-radius);
}
.ff-home-hero h2 {
  font-family: var(--ff-display);
  font-size: 1.65rem;
  margin: 0;
  letter-spacing: -0.02em;
  color: var(--ff-ink);
}
.ff-home-hero p {
  margin: 0;
  color: var(--ff-muted);
  font-size: 0.95rem;
  max-width: 40rem;
}

.ff-panel-title {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ff-muted);
  margin: 0 0 0.55rem 0;
}

.ff-steps {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.45rem;
  margin: 0.35rem 0 0.85rem 0;
}
.ff-step {
  background: var(--ff-panel);
  border: 1px solid var(--ff-line);
  border-radius: 8px;
  padding: 0.55rem 0.55rem 0.6rem;
  min-height: 4.2rem;
}
.ff-step.is-done {
  border-color: rgba(14, 107, 109, 0.45);
  background: rgba(14, 107, 109, 0.06);
}
.ff-step.is-active {
  border-color: var(--ff-accent);
  box-shadow: inset 0 0 0 1px rgba(14, 107, 109, 0.25);
}
.ff-step-top {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--ff-accent-deep);
  margin-bottom: 0.2rem;
}
.ff-step-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--ff-ink);
  line-height: 1.25;
}
.ff-step-sub {
  font-size: 0.75rem;
  color: var(--ff-muted);
  margin-top: 0.2rem;
  line-height: 1.3;
}

div[data-testid="stHorizontalBlock"] .stButton > button {
  min-height: 2.4rem;
  font-weight: 500;
  gap: 0.4rem;
  border-radius: 8px !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
  background: var(--ff-accent) !important;
  border-color: var(--ff-accent-deep) !important;
}

h1, h2, h3 {
  font-family: var(--ff-display) !important;
  letter-spacing: -0.015em;
  color: var(--ff-ink) !important;
}
[data-testid="stMetric"] {
  background: var(--ff-panel);
  border: 1px solid var(--ff-line);
  border-radius: 8px;
  padding: 0.55rem 0.7rem 0.45rem;
}
[data-testid="stMetricLabel"] { color: var(--ff-muted) !important; }
hr { border-color: var(--ff-line) !important; opacity: 0.85; }

div[data-testid="stExpander"] {
  background: var(--ff-panel);
  border: 1px solid var(--ff-line) !important;
  border-radius: 8px !important;
}

@media (max-width: 900px) {
  .ff-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ff-page-title { font-size: 1.45rem; }
}
</style>
"""


def _html(body: str) -> None:
  """Render raw HTML safely for Streamlit 1.33+."""
  try:
    st.html(body)
  except Exception:
    st.markdown(body, unsafe_allow_html=True)


def inject_theme() -> None:
  """Inject theme CSS every run (Streamlit rebuilds DOM on rerun)."""
  _html(_THEME_CSS)
  st.session_state["_ff_theme_injected"] = _CSS_VERSION


def render_sidebar_brand(*, desk: str, hint: str | None = None) -> None:
  import html as _html_mod
  desk_e = _html_mod.escape(desk)
  hint_html = ""
  if hint:
    hint_html = f'<div class="ff-brand-hint">{_html_mod.escape(hint)}</div>'
  st.sidebar.markdown(
    f"""
<div class="ff-brand">
  <p class="ff-brand-mark">Forex<span>Forge</span></p>
  <div class="ff-brand-desk">{desk_e}</div>
  {hint_html}
</div>
""",
    unsafe_allow_html=True,
  )


def icon_btn(
  label: str,
  *,
  key: str,
  icon: str | None = None,
  active: bool = False,
  help: str | None = None,
  width: str = "stretch",
) -> bool:
  """Primary when active; Material icon via Streamlit ``icon=``."""
  return st.button(
    label,
    key=key,
    icon=icon,
    help=help,
    type="primary" if active else "secondary",
    width=width,
  )
