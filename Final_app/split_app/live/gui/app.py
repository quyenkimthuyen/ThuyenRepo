"""Live Trade Streamlit UI — import, roster, bridge, journal, safety."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import streamlit as st

LIVE = Path(__file__).resolve().parents[1]
SPLIT = LIVE.parent
sys.path.insert(0, str(LIVE))
sys.path.insert(0, str(SPLIT))

from bridge_control import is_running, start_bridge, status, stop_bridge  # noqa: E402
from chart_validate import validate_chart_vs_roster  # noqa: E402
from live_config import BRIDGE_DIR, INBOX_DIR  # noqa: E402
from journal_view import journal_summary, load_recent_fills, load_trades  # noqa: E402
from magic_allocator import assign_magics  # noqa: E402
from package_store import (  # noqa: E402
  default_roster_from_installed,
  list_installed,
  load_roster,
  save_roster,
)
from safety import (  # noqa: E402
  arm_kill_switch,
  disarm_kill_switch,
  is_kill_switch_armed,
  write_flatten_command,
)
from shared.constants import LIVE_APP_PORT, LIVE_INSTANCE_ID, LIVE_MAGIC_BASE  # noqa: E402

st.set_page_config(page_title="EdgeMiner Live", layout="wide")
st.title("EdgeMiner Live Trade")
st.caption(
  f"Instance `{LIVE_INSTANCE_ID}` · port {LIVE_APP_PORT} · magic base {LIVE_MAGIC_BASE} · "
  "Packages from Lab · weekly remine via KB pin (no weekly re-export)."
)

tab_roster, tab_import, tab_bridge, tab_journal, tab_safety = st.tabs(
  ["Roster", "Import", "Bridge / EA", "Journal", "Safety"]
)

with tab_import:
  st.subheader("Import package")
  up = st.file_uploader("Upload .tmpkg", type=["tmpkg"])
  path_txt = st.text_input("Or local path to .tmpkg", "")
  if st.button("Import", type="primary"):
    try:
      if up is not None:
        INBOX_DIR.mkdir(parents=True, exist_ok=True)
        dest = INBOX_DIR / up.name
        dest.write_bytes(up.getvalue())
        pkg = dest
      elif path_txt.strip():
        pkg = Path(path_txt.strip())
      else:
        st.error("Choose a file or path")
        pkg = None
      if pkg:
        r = subprocess.run(
          [sys.executable, str(LIVE / "import_trade_package.py"), str(pkg)],
          cwd=str(LIVE),
          capture_output=True,
          text=True,
        )
        if r.returncode == 0:
          st.success(r.stdout or "OK")
          st.rerun()
        else:
          st.error(r.stderr or r.stdout or f"exit {r.returncode}")
    except Exception as exc:
      st.exception(exc)

  st.subheader("Installed")
  installed = list_installed()
  if not installed:
    st.info("No packages yet. Export from `lab/export_trade_package.py` first.")
  else:
    st.dataframe(installed, use_container_width=True)

with tab_roster:
  st.subheader("Live roster")
  st.caption("Enabled models must share one symbol + timeframe (one chart / one EA).")
  roster = load_roster()
  models = roster.get("models") or default_roster_from_installed()
  if st.button("Reset roster from installed"):
    models = default_roster_from_installed()
    save_roster(models)
    st.rerun()

  edited = []
  for i, row in enumerate(models):
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
      st.write(f"**{row.get('label')}** · `{row.get('symbol')}` `{row.get('timeframe')}`")
      st.caption(row.get("model_id"))
    with c2:
      en = st.checkbox("On", value=bool(row.get("enabled", True)), key=f"en_{i}")
    with c3:
      risk = st.number_input(
        "Risk%", min_value=0.1, max_value=5.0,
        value=float(row.get("risk_pct") or 1.0), step=0.1, key=f"risk_{i}",
      )
    with c4:
      st.write(f"magic: {row.get('magic') or '—'}")
    edited.append({**row, "enabled": en, "risk_pct": risk})

  if st.button("Save roster + assign magics", type="primary"):
    assigned = assign_magics(edited, sim=False)
    save_roster(assigned)
    st.success("Roster saved")
    st.rerun()

with tab_bridge:
  st.subheader("Chart vs package")
  check = validate_chart_vs_roster(bridge_dir=BRIDGE_DIR)
  if check["ok"]:
    st.success("Validation OK" + (f" · expected {check['expected']}" if check.get("expected") else ""))
  else:
    st.error("; ".join(check["errors"]))
  for w in check.get("warnings") or []:
    st.warning(w)
  if check.get("chart"):
    st.json(check["chart"])

  st.subheader("Bridge service")
  st_stat = status()
  c1, c2, c3 = st.columns(3)
  c1.metric("Running", "YES" if st_stat["running"] else "NO")
  c2.metric("PID", st_stat["pid"] or "—")
  c3.metric("Kill-switch", "ARMED" if st_stat["kill_switch"] else "off")
  if st_stat.get("bridge_status"):
    st.caption(f"status.json: {st_stat['bridge_status'].get('state')}")

  require_chart = st.checkbox("Require EA online (connection/bar)", value=False)
  b1, b2, b3 = st.columns(3)
  with b1:
    if st.button("Start bridge", type="primary"):
      try:
        out = start_bridge(require_chart=require_chart)
        st.success(f"Started pid={out.get('pid')} models={out['materialize']['model_ids']}")
        st.rerun()
      except Exception as exc:
        st.error(str(exc))
  with b2:
    if st.button("Stop bridge"):
      stop_bridge(flatten=False)
      st.info("Stopped")
      st.rerun()
  with b3:
    if st.button("Stop + flatten"):
      stop_bridge(flatten=True)
      st.warning("Stopped and sent FLAT/CLOSE")
      st.rerun()

  st.subheader("Sync EA roster files")
  if st.button("Sync bridge roster"):
    r = subprocess.run(
      [sys.executable, str(LIVE / "sync_bridge_roster.py")],
      cwd=str(LIVE),
      capture_output=True,
      text=True,
    )
    st.code(r.stdout or "")
    if r.returncode != 0:
      st.error(r.stderr or "failed")
    else:
      st.success("Synced")

  st.subheader("EA")
  st.markdown(
    """
- **One shared EA:** `split_app/mt5/Experts/ForgeBridgeLive.mq5` (+ Sim)
- Attach to chart matching package symbol/TF (`Period()` from chart)
- `InpBridgeSubdir=bridge_live`, magic base `20263001`
- Windows: `live/scripts/deploy_live_ea.ps1` (Attach + EnableTrading by default)
"""
  )
  br = BRIDGE_DIR / "models.json"
  if br.exists():
    st.json(json.loads(br.read_text(encoding="utf-8")))

with tab_journal:
  st.subheader("Trades / fills")
  summary = journal_summary()
  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Closed", summary["n_closed"])
  m2.metric("Total R", summary["total_r"])
  m3.metric("WR%", summary["win_rate_pct"] if summary["win_rate_pct"] is not None else "—")
  m4.metric("Fills log", summary["recent_fills"])
  trades = load_trades()
  if trades:
    st.dataframe(trades[-100:], use_container_width=True)
  fills = load_recent_fills(limit=30)
  if fills:
    st.subheader("Recent fills")
    st.dataframe(fills, use_container_width=True)
  if not trades and not fills:
    st.info("No journal yet — appears after EA fills.")

with tab_safety:
  st.subheader("Flatten / Kill-switch")
  st.write("Flatten writes `command.json` CLOSE for all roster magics + FLAT decisions.")
  if st.button("Flatten now"):
    payload = write_flatten_command(reason="ui_flatten")
    st.success(payload)
  armed = is_kill_switch_armed()
  st.write(f"Kill-switch: **{'ARMED' if armed else 'disarmed'}**")
  k1, k2 = st.columns(2)
  with k1:
    if st.button("ARM kill-switch", type="primary"):
      arm_kill_switch(reason="ui_kill_switch", flatten=True)
      st.error("Armed — bridge stopped, flatten sent")
      st.rerun()
  with k2:
    if st.button("Disarm kill-switch"):
      disarm_kill_switch()
      st.info("Disarmed — Start bridge manually when ready")
      st.rerun()
  st.caption("Loss-guard (consecutive losses) runs inside the bridge service when enabled in config.")
