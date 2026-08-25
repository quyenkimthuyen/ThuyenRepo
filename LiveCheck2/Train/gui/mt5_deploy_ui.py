"""Deploy ForgeBridge Live EA — sidebar control."""
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
  timeout_sec: float = 120.0,
) -> tuple[int, str, str]:
  """Run deploy_xm_forgebridge.ps1 for one Mode. Returns (code, stdout, stderr)."""
  import os
  import subprocess
  script = deploy_script_path()
  if not script.is_file():
    return 2, "", f"Deploy script missing: {script}"
  root = _repo_root()
  env = os.environ.copy()
  env["TRAINAPP_ROOT"] = str(root)
  desk = (env.get("TRAINAPP_DESK") or "").strip()
  if desk:
    env["TRAINAPP_DESK"] = desk
    env["TRAINAPP_RUNTIME"] = str((root / "runtime" / desk).resolve())
    try:
      from desk_context import load_desk
      env["TRAINAPP_CORE"] = str(load_desk(desk)["core_root"])
    except Exception:
      pass
  cmd = [
    "powershell.exe",
    "-ExecutionPolicy", "Bypass",
    "-File", str(script),
  ]
  if desk:
    cmd.extend(["-Desk", desk])
  cmd.extend(["-Mode", mode, "-Attach"])
  if enable_trading:
    cmd.append("-EnableTrading")
  if skip_bridge_service:
    cmd.append("-SkipBridgeService")
  try:
    res = subprocess.run(
      cmd,
      capture_output=True,
      text=True,
      check=False,
      cwd=str(root),
      env=env,
      timeout=max(30.0, float(timeout_sec)),
    )
  except subprocess.TimeoutExpired as e:
    out = (e.stdout or "") if isinstance(e.stdout, str) else (
      (e.stdout or b"").decode("utf-8", errors="replace") if e.stdout else ""
    )
    err = (e.stderr or "") if isinstance(e.stderr, str) else (
      (e.stderr or b"").decode("utf-8", errors="replace") if e.stderr else ""
    )
    return 124, out, (err + f"\nDeploy timeout sau {timeout_sec:.0f}s — MT5 có thể đang bận.").strip()
  return res.returncode, res.stdout or "", res.stderr or ""


def ea_live_name() -> str:
  """EA stem matches INSTANCE_ID (e.g. ForgeBridgeM15E21)."""
  from mt5_bridge.protocol import INSTANCE_ID
  return f"ForgeBridge{INSTANCE_ID}"


def wait_ea_online(
  bridge_dir,
  *,
  stale_after_seconds: float = 15.0,
  wait_sec: float = 45.0,
  poll_sec: float = 1.0,
) -> bool:
  """Poll ``connection.json`` until EA heartbeat is fresh."""
  import time
  from gui.mt5_live_chart import connection_health
  from mt5_bridge.protocol import connection_path, read_json

  deadline = time.time() + float(wait_sec)
  while time.time() < deadline:
    conn = read_json(connection_path(bridge_dir)) or {}
    health = connection_health(
      conn,
      stale_after_seconds=stale_after_seconds,
      bridge_dir=bridge_dir,
    )
    if health.get("online"):
      return True
    time.sleep(max(0.2, float(poll_sec)))
  return False


def deploy_ea_and_wait_online(
  mode: str,
  bridge_dir,
  *,
  enable_trading: bool = False,
  skip_bridge_service: bool = False,
  wait_sec: float = 25.0,
  deploy_timeout_sec: float = 90.0,
) -> tuple[bool, str]:
  """Deploy EA then wait for heartbeat. Returns ``(ok, detail)``."""
  try:
    code, out, err = run_deploy_mode(
      mode,
      enable_trading=enable_trading,
      skip_bridge_service=skip_bridge_service,
      timeout_sec=deploy_timeout_sec,
    )
  except Exception as e:
    return False, f"Deploy thất bại: {e}"
  if code != 0:
    log = ((err or "") + "\n" + (out or "")).strip() or "(empty)"
    return False, f"Deploy thất bại (code {code})\n{log}"
  if wait_ea_online(bridge_dir, wait_sec=wait_sec):
    return True, "EA online sau deploy"
  return False, (
    "Deploy xong nhưng chưa thấy heartbeat EA. "
    "Kiểm tra MT5 đã mở chart + EA đúng mode, rồi bấm lại."
  )


def render_sidebar_deploy_eas() -> None:
  """Compact Deploy Live — one script run, one MT5 restart."""
  live_ea = ea_live_name()
  if st.sidebar.button(
    "Deploy Live",
    icon=":material/settings_suggest:",
    use_container_width=True,
    key="sidebar_mt5_deploy_live",
    help=f"{live_ea} · 1 lần restart MT5 · test lịch sử dùng cùng EA",
  ):
    with st.spinner(f"Deploy {live_ea}…"):
      try:
        code, out, err = run_deploy_mode("Live", enable_trading=True)
      except Exception as e:
        st.sidebar.error(str(e))
        return
    if code != 0:
      st.sidebar.error(f"Deploy thất bại ({code})")
      with st.sidebar.expander("Log", expanded=True):
        st.code((err + "\n" + out).strip() or "(empty)")
      return
    st.sidebar.success(f"OK · {live_ea}")
    with st.sidebar.expander("Log", expanded=False):
      st.code(out or "(no stdout)")
    st.toast("Đã deploy Live EA (test lịch sử: from/to trên cùng chart)")
