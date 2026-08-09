"""Deploy ForgeBridge EA (Live + Simulate) — sidebar control."""
from __future__ import annotations

from pathlib import Path

import streamlit as st


def _repo_root() -> Path:
  return Path(__file__).resolve().parent.parent


def deploy_script_path() -> Path:
  return _repo_root() / "scripts" / "deploy_xm_forgebridge.ps1"


def run_deploy_mode(
  mode: str,
  *,
  enable_trading: bool = False,
  skip_bridge_service: bool = False,
) -> tuple[int, str, str]:
  """Run deploy_xm_forgebridge.ps1 for one Mode. Returns (code, stdout, stderr)."""
  import subprocess
  script = deploy_script_path()
  cmd = [
    "powershell.exe",
    "-ExecutionPolicy", "Bypass",
    "-File", str(script),
    "-Mode", mode,
    "-Attach",
  ]
  if enable_trading:
    cmd.append("-EnableTrading")
  if skip_bridge_service:
    cmd.append("-SkipBridgeService")
  res = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    check=False,
    cwd=str(script.parent.parent),
  )
  return res.returncode, res.stdout or "", res.stderr or ""


def ea_live_name() -> str:
  """EA stem matches INSTANCE_ID (M15 → ForgeBridgeM15E21, M15B → ForgeBridgeM15E21B)."""
  from mt5_bridge.protocol import INSTANCE_ID
  return f"ForgeBridge{INSTANCE_ID}"


def ea_sim_name() -> str:
  return f"{ea_live_name()}Sim"


def render_sidebar_deploy_eas() -> None:
  """Compact Deploy Live+Simulate — one script run, one MT5 restart."""
  live_ea = ea_live_name()
  sim_ea = ea_sim_name()
  if st.sidebar.button(
    "Deploy Live + Simulate",
    icon=":material/settings_suggest:",
    use_container_width=True,
    key="sidebar_mt5_deploy_both",
    help=f"{live_ea} + {sim_ea} · 1 lần restart MT5",
  ):
    with st.spinner(f"Deploy {live_ea} + {sim_ea} (một lần)…"):
      try:
        code, out, err = run_deploy_mode("Both", enable_trading=True)
      except Exception as e:
        st.sidebar.error(str(e))
        return
    if code != 0:
      st.sidebar.error(f"Deploy thất bại ({code})")
      with st.sidebar.expander("Log", expanded=True):
        st.code((err + "\n" + out).strip() or "(empty)")
      return
    st.sidebar.success(f"OK · {live_ea} + {sim_ea}")
    with st.sidebar.expander("Log", expanded=False):
      st.code(out or "(no stdout)")
    st.toast("Đã deploy Live + Simulate (1 lần restart MT5)")
