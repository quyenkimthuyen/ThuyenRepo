"""Professional dark theme for BestTrade Streamlit UI."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bt-bg: #0b0e14;
  --bt-panel: #12161f;
  --bt-card: #181d28;
  --bt-border: #2a3142;
  --bt-text: #e8ecf4;
  --bt-muted: #8b93a7;
  --bt-accent: #f0b429;
  --bt-accent-dim: rgba(240, 180, 41, 0.12);
  --bt-green: #26a69a;
  --bt-red: #ef5350;
  --bt-blue: #42a5f5;
}

html, body, [class*="css"] {
  font-family: 'DM Sans', system-ui, sans-serif;
}

.stApp {
  background: linear-gradient(165deg, #0b0e14 0%, #0f1319 45%, #0b0e14 100%);
}

.block-container {
  padding-top: 1.5rem;
  max-width: 1400px;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: #0e1118;
  border-right: 1px solid var(--bt-border);
}
[data-testid="stSidebar"] .stMarkdown h1 {
  font-size: 1.35rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--bt-text);
}

/* Hero */
.bt-hero {
  background: linear-gradient(135deg, #181d28 0%, #1a2030 50%, #151a24 100%);
  border: 1px solid var(--bt-border);
  border-radius: 16px;
  padding: 1.75rem 2rem;
  margin-bottom: 1.25rem;
  box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}
.bt-hero h1 {
  font-size: 1.85rem;
  font-weight: 700;
  margin: 0 0 0.35rem 0;
  color: var(--bt-text);
  letter-spacing: -0.03em;
}
.bt-hero .subtitle {
  color: var(--bt-muted);
  font-size: 0.95rem;
  margin: 0;
  line-height: 1.5;
}
.bt-badge {
  display: inline-block;
  background: var(--bt-accent-dim);
  color: var(--bt-accent);
  border: 1px solid rgba(240,180,41,0.35);
  border-radius: 999px;
  padding: 0.2rem 0.75rem;
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 0.5rem;
}

/* Metric cards */
.bt-metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0;
}
.bt-metric {
  background: var(--bt-card);
  border: 1px solid var(--bt-border);
  border-radius: 12px;
  padding: 1rem 1.1rem;
}
.bt-metric .label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--bt-muted);
  margin-bottom: 0.35rem;
}
.bt-metric .value {
  font-size: 1.45rem;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: var(--bt-text);
}
.bt-metric .value.pos { color: var(--bt-green); }
.bt-metric .value.neg { color: var(--bt-red); }
.bt-metric .value.accent { color: var(--bt-accent); }

/* Strategy card */
.bt-strategy-card {
  background: var(--bt-card);
  border: 1px solid var(--bt-border);
  border-left: 3px solid var(--bt-accent);
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
  margin: 0.75rem 0;
}
.bt-strategy-card h3 {
  margin: 0 0 0.5rem 0;
  color: var(--bt-text);
  font-size: 1.1rem;
}
.bt-strategy-card p {
  color: var(--bt-muted);
  font-size: 0.88rem;
  line-height: 1.55;
  margin: 0;
}

/* Validation banner */
.bt-validated {
  background: linear-gradient(90deg, rgba(38,166,154,0.15), rgba(38,166,154,0.05));
  border: 1px solid rgba(38,166,154,0.35);
  border-radius: 10px;
  padding: 0.85rem 1.1rem;
  color: #7dcec6;
  font-size: 0.88rem;
  margin: 0.75rem 0;
}

/* Hide Streamlit branding clutter */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.5rem;
  background: transparent;
}
.stTabs [data-baseweb="tab"] {
  background: var(--bt-card);
  border-radius: 8px;
  border: 1px solid var(--bt-border);
  color: var(--bt-muted);
  padding: 0.5rem 1rem;
}
.stTabs [aria-selected="true"] {
  background: var(--bt-accent-dim) !important;
  border-color: rgba(240,180,41,0.4) !important;
  color: var(--bt-accent) !important;
}
</style>
"""
