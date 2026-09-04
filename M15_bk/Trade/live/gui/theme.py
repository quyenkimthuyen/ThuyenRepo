"""Trader-desk visual theme for Live Streamlit UI (light only)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import streamlit as st

ThemeMode = Literal["light"]
_PREF_NAME = "ui_prefs.json"


def _prefs_path() -> Path:
  try:
    from live_config import RESULTS_DIR
    return RESULTS_DIR / _PREF_NAME
  except Exception:
    return Path(__file__).resolve().parents[1] / "results" / _PREF_NAME


def restore_widget_choice(current, saved, valid: tuple[str, ...], default: str) -> str:
  """Pick session value if still mounted; otherwise the saved pref.

  Streamlit deletes a widget's session_state key when that control is not
  rendered (other top-nav tabs, or a Live sub-tab that hides the radio).
  F5 rebuilds session_state from disk; tab hops must do the same restore.
  """
  if current in valid:
    return str(current)
  saved_s = str(saved or default).strip().lower()
  return saved_s if saved_s in valid else default


def load_ui_prefs() -> dict:
  """Sidebar / desk prefs that must survive browser refresh."""
  path = _prefs_path()
  out: dict = {
    "theme": "light",
    "auto_refresh": False,
    "auto_refresh_every": 5,
    "live_stats_period": "today",
    "live_desk_section": "now",
    "now_chart_checks": {},
    "now_picked_models": {},
  }
  try:
    if path.exists():
      raw = json.loads(path.read_text(encoding="utf-8"))
      if isinstance(raw, dict):
        out.update(raw)
  except Exception:
    pass
  out["theme"] = "light"
  out["auto_refresh"] = bool(out.get("auto_refresh"))
  try:
    every = int(out.get("auto_refresh_every") or 5)
  except (TypeError, ValueError):
    every = 5
  if every not in (5, 10, 15, 30):
    every = 5
  out["auto_refresh_every"] = every
  period = str(out.get("live_stats_period") or "today").strip().lower()
  if period not in ("today", "week", "month", "all"):
    period = "today"
  out["live_stats_period"] = period
  section = str(out.get("live_desk_section") or "now").strip().lower()
  if section == "control":
    section = "now"
  if section not in ("now", "pipeline", "session"):
    section = "now"
  out["live_desk_section"] = section
  checks = out.get("now_chart_checks")
  out["now_chart_checks"] = checks if isinstance(checks, dict) else {}
  picked = out.get("now_picked_models")
  out["now_picked_models"] = picked if isinstance(picked, dict) else {}
  return out


def save_ui_prefs(updates: dict | None = None) -> dict:
  path = _prefs_path()
  path.parent.mkdir(parents=True, exist_ok=True)
  payload = load_ui_prefs()
  if updates:
    payload.update(updates)
  payload["theme"] = "light"
  path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
  return payload


def now_chart_check_id(side: str, feat: str, thr) -> str:
  try:
    t = f"{float(thr):.4f}"
  except (TypeError, ValueError):
    t = "0"
  return f"{side}|{feat}|{t}"


def load_now_chart_checks(model_id: str | None) -> dict[str, bool]:
  mid = str(model_id or "").strip()
  if not mid:
    return {}
  raw = (load_ui_prefs().get("now_chart_checks") or {}).get(mid)
  if not isinstance(raw, dict):
    return {}
  return {str(k): bool(v) for k, v in raw.items()}


def save_now_chart_checks(model_id: str | None, checks: dict[str, bool]) -> dict:
  mid = str(model_id or "").strip()
  blob = dict(load_ui_prefs().get("now_chart_checks") or {})
  if mid:
    blob[mid] = {str(k): bool(v) for k, v in (checks or {}).items()}
  return save_ui_prefs({"now_chart_checks": blob})


def load_now_picked_model(book_key: str | None) -> str:
  key = str(book_key or "").strip()
  if not key:
    return ""
  raw = (load_ui_prefs().get("now_picked_models") or {}).get(key)
  return str(raw or "").strip()


def save_now_picked_model(book_key: str | None, model_id: str | None) -> dict:
  key = str(book_key or "").strip()
  blob = dict(load_ui_prefs().get("now_picked_models") or {})
  if key:
    blob[key] = str(model_id or "").strip()
  return save_ui_prefs({"now_picked_models": blob})


def load_theme_pref() -> ThemeMode:
  return "light"


def save_theme_pref(mode: ThemeMode = "light") -> None:
  save_ui_prefs({"theme": "light"})


def get_theme_mode() -> ThemeMode:
  st.session_state.ui_theme = "light"
  return "light"


def set_theme_mode(mode: ThemeMode | str = "light") -> None:
  """Light-only desk — dark mode removed."""
  st.session_state.ui_theme = "light"
  save_theme_pref("light")
  _sync_streamlit_config()


def _sync_streamlit_config(mode: ThemeMode | str = "light") -> None:
  """Keep .streamlit/config.toml on light base."""
  cfg = Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml"
  body = (
    '[theme]\n'
    'base = "light"\n'
    'primaryColor = "#0f766e"\n'
    'backgroundColor = "#f3f6fa"\n'
    'secondaryBackgroundColor = "#ffffff"\n'
    'textColor = "#0f172a"\n'
    'font = "sans serif"\n'
    '\n'
    '[server]\n'
    'headless = true\n'
  )
  try:
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(body, encoding="utf-8")
  except OSError:
    pass


# Desk tokens + Streamlit theme tokens (--text-color etc.) so native widgets match.
_LIGHT_VARS = """
:root, .stApp {
  color-scheme: light;
  --desk-bg: #f3f6fa;
  --desk-bg-glow-a: rgba(15, 118, 110, 0.06);
  --desk-bg-glow-b: rgba(37, 99, 235, 0.05);
  --desk-panel: #ffffff;
  --desk-panel-2: #f8fafc;
  --desk-border: #d0d7e2;
  --desk-text: #0f172a;
  --desk-muted: #475569;
  --desk-faint: #64748b;
  --desk-long: #047857;
  --desk-short: #b91c1c;
  --desk-flat: #1e293b;
  --desk-accent: #0f766e;
  --desk-warn: #b45309;
  --desk-chip: #f1f5f9;
  --desk-chip-strong: #e2e8f0;
  --desk-inset: rgba(15, 23, 42, 0.04);
  --desk-divider: #e2e8f0;
  --desk-reason: #334155;
  --desk-neutral: #334155;
  --desk-health-row: #1e293b;
  --desk-shadow-text: transparent;
  --pill-ok-bg: #d1fae5;
  --pill-ok-fg: #065f46;
  --pill-ok-bd: #6ee7b7;
  --pill-warn-bg: #ffedd5;
  --pill-warn-fg: #9a3412;
  --pill-warn-bd: #fdba74;
  --pill-danger-bg: #fee2e2;
  --pill-danger-fg: #991b1b;
  --pill-danger-bd: #fca5a5;
  --pill-muted-bg: #e2e8f0;
  --pill-muted-fg: #334155;
  --pill-muted-bd: #cbd5e1;
  --sig-flat-bar: #0284c7;
  --sig-flat-badge: #075985;
  --sig-unknown: #b45309;
  --st-sidebar-bg: #ffffff;
  --st-widget-bg: #ffffff;
  --st-btn-bg: #ffffff;
  --st-btn-fg: #0f172a;
  --st-btn-bd: #cbd5e1;
  --st-primary-fg: #ffffff;
  --st-disabled-bg: #e2e8f0;
  --st-disabled-fg: #64748b;
  --text-color: #0f172a;
  --background-color: #f3f6fa;
  --secondary-background-color: #ffffff;
  --primary-color: #0f766e;
}
"""

_SHARED = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600;700&display=swap');

html, body, .stApp {
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  color: var(--desk-text) !important;
  background: var(--desk-bg) !important;
}

.stApp {
  background:
    radial-gradient(1100px 480px at 8% -12%, var(--desk-bg-glow-a), transparent 55%),
    radial-gradient(900px 420px at 100% 0%, var(--desk-bg-glow-b), transparent 50%),
    var(--desk-bg) !important;
}

/* no-rerun-fade: Streamlit marks widgets stale (opacity 0.33, 1s ease) while
   auto-refresh / fragment ticks. Keep the last paint fully visible. */
.stApp .stale,
.stApp [class~="stale"],
.stApp .element-container,
.stApp [data-testid="stElementContainer"],
.stApp [data-testid="stVerticalBlock"],
.stApp [data-testid="stVerticalBlockBorderWrapper"],
.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stPlotlyChart"] {
  opacity: 1 !important;
  filter: none !important;
  transition: none !important;
}
.stApp [data-testid="stSkeleton"],
.stApp .stSkeleton {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
}

[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
.block-container {
  background: transparent !important;
  color: var(--desk-text) !important;
}

.block-container {
  padding-top: 1.1rem;
  padding-bottom: 2rem;
  max-width: 1180px;
}

#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] {
  background: transparent !important;
}

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div:first-child {
  background: var(--st-sidebar-bg) !important;
  border-right: 1px solid var(--desk-border) !important;
}

h1, h2, h3, h4 {
  letter-spacing: -0.02em;
  font-weight: 600;
  color: var(--desk-text) !important;
}

/* Native Streamlit copy — avoid targeting every span (breaks pills) */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
label,
.stCaption,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[role="radiogroup"] label,
[role="radiogroup"] p {
  color: var(--desk-text) !important;
}
.stCaption,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
[data-testid="stMetricLabel"] {
  color: var(--desk-muted) !important;
}

/* Buttons */
div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
  min-height: 2.5rem;
  width: 100%;
  background: var(--st-btn-bg) !important;
  color: var(--st-btn-fg) !important;
  border: 1px solid var(--st-btn-bd) !important;
}
div[data-testid="stButton"] > button p,
div[data-testid="stButton"] > button span,
div[data-testid="stDownloadButton"] > button p,
div[data-testid="stDownloadButton"] > button span {
  color: inherit !important;
}
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
  background: var(--desk-accent) !important;
  border-color: var(--desk-accent) !important;
  color: var(--st-primary-fg) !important;
  font-weight: 650;
}
div[data-testid="stButton"] > button:disabled,
div[data-testid="stButton"] > button[disabled] {
  background: var(--st-disabled-bg) !important;
  color: var(--st-disabled-fg) !important;
  border-color: var(--desk-border) !important;
  opacity: 1 !important;
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-baseweb="select"] > div,
div[data-baseweb="input"],
div[data-baseweb="input"] input,
div[data-baseweb="base-input"],
div[data-baseweb="base-input"] input {
  background: var(--st-widget-bg) !important;
  background-color: var(--st-widget-bg) !important;
  color: var(--desk-text) !important;
  border-color: var(--desk-border) !important;
  caret-color: var(--desk-text) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] svg,
div[data-testid="stSelectbox"] span,
div[data-testid="stMultiSelect"] span,
div[data-testid="stDateInput"] span {
  color: var(--desk-text) !important;
  fill: var(--desk-muted) !important;
}

/* Select / date popovers (portaled to body) */
body > div[data-baseweb="popover"],
div[data-baseweb="popover"],
div[data-floating-ui-portal],
div[data-floating-ui-portal] > div,
ul[role="listbox"],
[data-baseweb="menu"],
[data-baseweb="calendar"],
[data-baseweb="calendar"] div,
[data-baseweb="month"],
[data-baseweb="datepicker"] {
  background: var(--st-widget-bg) !important;
  background-color: var(--st-widget-bg) !important;
  color: var(--desk-text) !important;
  border-color: var(--desk-border) !important;
}
ul[role="listbox"] li,
[role="option"],
[data-baseweb="menu"] li,
[data-baseweb="calendar"] button,
[data-baseweb="calendar"] [role="gridcell"],
[data-baseweb="datepicker"] button {
  background: transparent !important;
  color: var(--desk-text) !important;
}
ul[role="listbox"] li:hover,
[role="option"]:hover,
[role="option"][aria-selected="true"],
[data-baseweb="menu"] li:hover,
[data-baseweb="calendar"] button:hover {
  background: var(--desk-panel-2) !important;
  color: var(--desk-text) !important;
}

/* Expander / tabs / slider / toggle */
div[data-testid="stExpander"],
div[data-testid="stExpander"] details,
div[data-testid="stExpander"] summary {
  background: var(--desk-panel) !important;
  color: var(--desk-text) !important;
  border-color: var(--desk-border) !important;
}
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span {
  color: var(--desk-text) !important;
}
button[data-baseweb="tab"],
button[role="tab"] {
  color: var(--desk-muted) !important;
}
button[data-baseweb="tab"][aria-selected="true"],
button[role="tab"][aria-selected="true"] {
  color: var(--desk-text) !important;
}
div[data-testid="stSlider"] [data-baseweb="slider"],
div[data-testid="stSelectSlider"] {
  color: var(--desk-text) !important;
}
label[data-baseweb="checkbox"],
label[data-testid="stWidgetLabel"] {
  color: var(--desk-text) !important;
}

/* Dataframe / table */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"],
[data-testid="stDataFrame"] [role="grid"],
[data-testid="stDataFrame"] [role="row"],
[data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stTable"] table,
div[data-testid="stTable"] th,
div[data-testid="stTable"] td {
  background-color: var(--desk-panel) !important;
  color: var(--desk-text) !important;
  border-color: var(--desk-border) !important;
}
[data-testid="stDataFrame"] [role="columnheader"] {
  background-color: var(--desk-panel-2) !important;
  color: var(--desk-muted) !important;
}

/* Metrics card */
div[data-testid="stMetric"] {
  background: var(--desk-chip) !important;
  border: 1px solid var(--desk-border) !important;
  border-radius: 10px;
  padding: 0.55rem 0.75rem !important;
}
div[data-testid="stMetricValue"],
div[data-testid="stMetricDelta"] {
  color: var(--desk-text) !important;
}

/* Plotly / chart host */
[data-testid="stPlotlyChart"],
[data-testid="stVegaLiteChart"] {
  background: var(--desk-panel) !important;
  border: 1px solid var(--desk-border) !important;
  border-radius: 10px;
  padding: 0.25rem;
}
.js-plotly-plot .plotly,
.js-plotly-plot .plot-container {
  background: transparent !important;
}

/* Custom replay progress — explicit width. Do not restyle st.progress:
   Streamlit 1.58 fill is width:100% + translateX; coloring it looks 100% done. */
.replay-prog {
  height: 10px;
  background: var(--desk-chip-strong);
  border: 1px solid var(--desk-border);
  border-radius: 6px;
  overflow: hidden;
  margin: 0.2rem 0 0.75rem 0;
}
.replay-prog-fill {
  height: 100%;
  max-width: 100%;
  background: var(--desk-accent);
  border-radius: 6px;
}

[data-testid="stAlert"] {
  background: var(--desk-chip) !important;
  border: 1px solid var(--desk-border) !important;
  color: var(--desk-text) !important;
}
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) {
  background: var(--pill-ok-bg) !important;
  border-color: var(--pill-ok-bd) !important;
  color: var(--pill-ok-fg) !important;
}
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {
  background: var(--pill-danger-bg) !important;
  border-color: var(--pill-danger-bd) !important;
  color: var(--pill-danger-fg) !important;
}
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) {
  background: var(--pill-warn-bg) !important;
  border-color: var(--pill-warn-bd) !important;
  color: var(--pill-warn-fg) !important;
}
[data-testid="stAlert"] p {
  color: inherit !important;
}

div[data-testid="stHorizontalBlock"] { align-items: flex-start; }
div[role="radiogroup"] {
  gap: 0.35rem 0.75rem;
  margin: 0.35rem 0 0.85rem 0;
  flex-wrap: wrap;
}
div[role="radiogroup"] label p {
  white-space: normal;
  line-height: 1.25;
}

/* ── Custom desk components ───────────────────────────────────────── */
.desk-top {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--desk-border);
}
.desk-brand {
  font-size: 1.55rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0;
  line-height: 1.1;
  color: var(--desk-text) !important;
}
.desk-sub {
  margin: 0.25rem 0 0 0;
  font-size: 0.92rem;
  color: var(--desk-muted) !important;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.desk-clock {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.85rem;
  color: var(--desk-faint) !important;
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
  padding: 0.32rem 0.75rem;
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
.pill-ok { background: var(--pill-ok-bg) !important; color: var(--pill-ok-fg) !important; border-color: var(--pill-ok-bd) !important; }
.pill-warn { background: var(--pill-warn-bg) !important; color: var(--pill-warn-fg) !important; border-color: var(--pill-warn-bd) !important; }
.pill-danger { background: var(--pill-danger-bg) !important; color: var(--pill-danger-fg) !important; border-color: var(--pill-danger-bd) !important; }
.pill-muted { background: var(--pill-muted-bg) !important; color: var(--pill-muted-fg) !important; border-color: var(--pill-muted-bd) !important; }

.panel {
  background: linear-gradient(165deg, var(--desk-panel-2), var(--desk-panel)) !important;
  border: 1px solid var(--desk-border) !important;
  border-radius: 14px;
  padding: 1rem 1.1rem 1.05rem;
  margin-bottom: 0.75rem;
  box-shadow: inset 0 1px 0 var(--desk-inset);
  color: var(--desk-text) !important;
}
.panel-label {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--desk-muted) !important;
  margin-bottom: 0.4rem;
  font-weight: 700;
}

.signal-panel {
  position: relative;
  overflow: hidden;
  min-height: 10.5rem;
  padding-left: 1.2rem;
}
.signal-panel::before {
  content: "";
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 5px;
  background: var(--desk-faint);
}
.signal-panel.signal-long::before { background: var(--desk-long); }
.signal-panel.signal-short::before { background: var(--desk-short); }
.signal-panel.signal-flat::before { background: var(--sig-flat-bar); }
.signal-panel.signal-unknown::before { background: var(--desk-warn); }

.signal-panel.signal-long {
  background: linear-gradient(135deg, color-mix(in srgb, var(--desk-long) 14%, var(--desk-panel)), var(--desk-panel) 58%) !important;
  border-color: color-mix(in srgb, var(--desk-long) 35%, var(--desk-border)) !important;
}
.signal-panel.signal-short {
  background: linear-gradient(135deg, color-mix(in srgb, var(--desk-short) 12%, var(--desk-panel)), var(--desk-panel) 58%) !important;
  border-color: color-mix(in srgb, var(--desk-short) 32%, var(--desk-border)) !important;
}
.signal-panel.signal-flat {
  background: linear-gradient(135deg, color-mix(in srgb, var(--sig-flat-bar) 10%, var(--desk-panel)), var(--desk-panel) 58%) !important;
  border-color: color-mix(in srgb, var(--sig-flat-bar) 28%, var(--desk-border)) !important;
}
.signal-panel.signal-unknown {
  background: linear-gradient(135deg, color-mix(in srgb, var(--desk-warn) 10%, var(--desk-panel)), var(--desk-panel) 58%) !important;
  border-color: color-mix(in srgb, var(--desk-warn) 28%, var(--desk-border)) !important;
}

.signal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.55rem;
}
.signal-head .panel-label { margin-bottom: 0; }
.signal-badge {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.18rem 0.5rem;
  border-radius: 6px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  background: var(--desk-chip-strong) !important;
  color: var(--desk-muted) !important;
  border: 1px solid var(--desk-border) !important;
}
.signal-long .signal-badge {
  color: var(--pill-ok-fg) !important;
  background: var(--pill-ok-bg) !important;
  border-color: var(--pill-ok-bd) !important;
}
.signal-short .signal-badge {
  color: var(--pill-danger-fg) !important;
  background: var(--pill-danger-bg) !important;
  border-color: var(--pill-danger-bd) !important;
}
.signal-flat .signal-badge {
  color: var(--sig-flat-badge) !important;
  background: color-mix(in srgb, var(--sig-flat-bar) 14%, var(--desk-panel)) !important;
  border-color: color-mix(in srgb, var(--sig-flat-bar) 35%, var(--desk-border)) !important;
}

.decision-action {
  font-size: 2.55rem;
  font-weight: 700;
  line-height: 1;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  letter-spacing: -0.04em;
  text-shadow: 0 1px 0 var(--desk-shadow-text);
}
.decision-long { color: var(--desk-long) !important; }
.decision-short { color: var(--desk-short) !important; }
.decision-flat { color: var(--desk-flat) !important; }
.decision-unknown { color: var(--sig-unknown) !important; }

.decision-meta {
  margin-top: 0.7rem;
  display: grid;
  gap: 0.28rem;
  line-height: 1.4;
}
.decision-model {
  font-size: 0.98rem;
  font-weight: 650;
  color: var(--desk-text) !important;
}
.decision-reason {
  font-size: 0.88rem;
  color: var(--desk-reason) !important;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.decision-wait {
  font-size: 0.86rem;
  color: var(--desk-muted) !important;
}

.now-watch-panel { min-height: 0; }
.now-hint {
  margin-top: 0.4rem;
  font-size: 0.72rem;
  color: var(--desk-muted) !important;
  line-height: 1.35;
}
.now-watch {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0.45rem;
  font-size: 0.8rem;
}
.now-watch-compact { font-size: 0.76rem; }
.now-watch th {
  text-align: left;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--desk-muted) !important;
  font-weight: 700;
  padding: 0.15rem 0.4rem 0.28rem 0;
  border-bottom: 1px solid var(--desk-border);
}
.now-watch td {
  padding: 0.22rem 0.4rem 0.22rem 0;
  border-top: 1px solid var(--desk-divider);
  vertical-align: middle;
  color: var(--desk-text) !important;
}
.now-watch tr:first-child td { border-top: none; }
.now-act {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
  width: 3.6rem;
}
.now-model {
  font-weight: 650;
  font-size: 0.86rem;
  line-height: 1.3;
  white-space: normal;
}
.now-gate-cell {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  white-space: nowrap;
  width: 2.8rem;
}
.now-wait-cell {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-weight: 700;
  white-space: nowrap;
  font-size: 0.72rem;
}
.now-extra {
  display: flex;
  flex-wrap: wrap;
  gap: 0.28rem 0.4rem;
  margin: 0 0 0.32rem 0;
}
.now-chip {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.68rem;
  font-weight: 650;
  padding: 0.06rem 0.38rem;
  border-radius: 999px;
  border: 1px solid var(--desk-border);
}
.now-levels {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: var(--desk-muted) !important;
  white-space: nowrap;
  font-size: 0.72rem;
  line-height: 1.3;
}
.now-reason {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: var(--desk-reason) !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.72rem;
  line-height: 1.3;
  max-width: 22rem;
}
.now-expect, .now-current {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.74rem;
  line-height: 1.35;
}
.now-gate {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-bottom: 0.08rem;
}
.now-rule { display: block; font-size: 0.72rem; line-height: 1.35; padding-top: 0; }
.now-expect { color: var(--desk-muted) !important; }
.now-current { color: var(--desk-text) !important; }
.now-hit { color: var(--desk-long) !important; font-weight: 650; }
.now-miss { color: var(--desk-reason) !important; }
.now-bar {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  color: var(--desk-muted) !important;
  font-size: 0.76rem;
  line-height: 1.35;
}
.now-row-long { background: color-mix(in srgb, var(--desk-long) 10%, transparent); }
.now-row-short { background: color-mix(in srgb, var(--desk-short) 10%, transparent); }
.now-row-hold { background: color-mix(in srgb, var(--pill-warn-fg) 8%, transparent); }
.now-row-long .now-act { color: var(--desk-long) !important; }
.now-row-short .now-act { color: var(--desk-short) !important; }
.now-inspect {
  margin: 0.15rem 0 0.35rem 0;
}
.now-inspect-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.3rem 0.55rem;
  margin-bottom: 0.28rem;
}
.now-inspect-head .now-act { font-size: 0.86rem; }
.now-inspect-head .now-row-long { background: none; color: var(--desk-long) !important; }
.now-inspect-head .now-row-short { background: none; color: var(--desk-short) !important; }
.now-inspect-head .now-row-flat,
.now-inspect-head .now-row-hold { background: none; }
.now-inspect-why {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.7rem;
  color: var(--desk-reason) !important;
  line-height: 1.35;
}
.now-inspect-k {
  font-size: 0.64rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--desk-muted) !important;
  margin-bottom: 0.08rem;
}
.now-inspect-side {
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 0.72rem;
  line-height: 1.35;
}
.now-gate {
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  margin-bottom: 0.08rem;
}
.now-rule { display: block; font-size: 0.72rem; line-height: 1.35; padding-top: 0; }
.now-inspect-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.35rem 0.8rem;
}
.now-row-flat .now-act { color: var(--desk-flat) !important; }
.now-row-hold .now-act { color: var(--pill-warn-fg) !important; }
.now-row-unknown .now-act { color: var(--sig-unknown) !important; }

/* Compact BUY/SELL rule ticks (keys now_xf_*) */
div[class*="st-key-now_xf_"] {
  min-height: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  margin-bottom: -0.12rem !important;
}
div[class*="st-key-now_xf_"] label {
  min-height: 1.35rem !important;
  gap: 0.32rem !important;
}
div[class*="st-key-now_xf_"] p {
  font-size: 0.72rem !important;
  font-family: "IBM Plex Mono", ui-monospace, monospace !important;
  line-height: 1.35 !important;
  font-weight: 550 !important;
}
.now-row-hold .now-act { color: var(--pill-warn-fg) !important; }
.now-row-unknown .now-act { color: var(--sig-unknown) !important; }

.session-panel { min-height: 10.5rem; }
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem;
}
.stat-cell {
  background: var(--desk-chip) !important;
  border: 1px solid var(--desk-border) !important;
  border-radius: 10px;
  padding: 0.55rem 0.7rem 0.6rem;
}
.stat-k {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--desk-muted) !important;
  font-weight: 700;
  margin-bottom: 0.2rem;
}
.stat-v {
  font-size: 1.4rem;
  font-weight: 700;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  letter-spacing: -0.02em;
  color: var(--desk-text) !important;
}
.stat-v.pos { color: var(--desk-long) !important; }
.stat-v.neg { color: var(--desk-short) !important; }
.stat-v.neutral { color: var(--desk-neutral) !important; }

.model-card, .health-book {
  background: var(--desk-chip) !important;
  border: 1px solid var(--desk-border) !important;
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
  margin-bottom: 0.45rem;
  color: var(--desk-text) !important;
}
.model-title, .health-book-title {
  font-weight: 650;
  font-size: 0.95rem;
  color: var(--desk-text) !important;
}
.model-meta, .health-book-meta {
  font-size: 0.8rem;
  color: var(--desk-muted) !important;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  margin-top: 0.15rem;
}
.health-book-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.35rem 0.75rem;
  margin-bottom: 0.35rem;
}
.health-model {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) auto auto auto;
  gap: 0.25rem 0.65rem;
  align-items: center;
  padding: 0.28rem 0;
  border-top: 1px solid var(--desk-divider);
  font-size: 0.82rem;
  color: var(--desk-health-row) !important;
}
.health-model:first-of-type { border-top: none; }
.health-flag {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 0.12rem 0.42rem;
  border-radius: 4px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.health-flag-ok { background: var(--pill-ok-bg) !important; color: var(--pill-ok-fg) !important; }
.health-flag-warn { background: var(--pill-warn-bg) !important; color: var(--pill-warn-fg) !important; }
.health-flag-danger { background: var(--pill-danger-bg) !important; color: var(--pill-danger-fg) !important; }
.health-flag-muted { background: var(--pill-muted-bg) !important; color: var(--pill-muted-fg) !important; }
.health-alert {
  font-size: 0.8rem;
  padding: 0.35rem 0.55rem;
  border-radius: 8px;
  margin: 0.25rem 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
}
.health-alert-warn { background: var(--pill-warn-bg) !important; color: var(--pill-warn-fg) !important; }
.health-alert-danger { background: var(--pill-danger-bg) !important; color: var(--pill-danger-fg) !important; }

.import-flash {
  font-size: 0.95rem;
  line-height: 1.4;
  padding: 0.7rem 0.9rem;
  border-radius: 8px;
  margin: 0.45rem 0 0.75rem 0;
  border: 1px solid transparent;
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
}
.import-flash strong { display: block; margin-bottom: 0.2rem; }
.import-flash-ok {
  background: var(--pill-ok-bg) !important;
  color: var(--pill-ok-fg) !important;
  border-color: var(--pill-ok-bd) !important;
}
.import-flash-fail {
  background: var(--pill-danger-bg) !important;
  color: var(--pill-danger-fg) !important;
  border-color: var(--pill-danger-bd) !important;
}

.hint {
  font-size: 0.82rem;
  color: var(--desk-muted) !important;
  margin: 0.2rem 0 0.6rem 0;
}
"""


def inject_theme(mode: ThemeMode | None = None) -> None:
  """Inject light-only desk CSS on every script run."""
  set_theme_mode("light")
  st.markdown(
    f"<style>\n{_LIGHT_VARS}\n{_SHARED}\n</style>",
    unsafe_allow_html=True,
  )


def progress_bar_html(pct: float) -> str:
  """Determinate bar with inline width — Streamlit st.progress + theme CSS looks 100%."""
  try:
    p = float(pct)
  except (TypeError, ValueError):
    p = 0.0
  p = min(max(p, 0.0), 100.0)
  return (
    f'<div class="replay-prog" role="progressbar" '
    f'aria-valuenow="{p:.1f}" aria-valuemin="0" aria-valuemax="100">'
    f'<div class="replay-prog-fill" style="width:{p:.1f}%"></div></div>'
  )


def pill(label: str, tone: str = "muted") -> str:
  return f'<span class="pill pill-{tone}"><span class="dot"></span>{label}</span>'


def r_class(val: float | int | None) -> str:
  try:
    v = float(val or 0)
  except (TypeError, ValueError):
    return "neutral"
  if v > 0:
    return "pos"
  if v < 0:
    return "neg"
  return "neutral"


def signal_badge(tone: str | None) -> str:
  t = (tone or "unknown").lower()
  labels = {
    "long": "LONG",
    "short": "SHORT",
    "flat": "FLAT",
    "unknown": "WAIT",
  }
  return labels.get(t, "WAIT")
