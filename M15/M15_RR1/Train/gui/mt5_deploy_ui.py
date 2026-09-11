"""Deploy ForgeBridge Live EA — sidebar control."""
from __future__ import annotations

import os
import subprocess
import time
from datetime import timedelta
from pathlib import Path

import streamlit as st

_DEPLOY_HANDLES: dict[int, tuple] = {}
_CREATE_NO_WINDOW = 0x08000000


def _repo_root() -> Path:
  return Path(__file__).resolve().parent.parent


def deploy_script_path() -> Path:
  return _repo_root() / "scripts" / "deploy_xm_forgebridge.ps1"


def _pid_alive(pid: int | None) -> bool:
  if not pid:
    return False
  if os.name == "nt":
    try:
      import ctypes
      from ctypes import wintypes

      kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
      handle = kernel32.OpenProcess(0x1000, False, int(pid))
      if not handle:
        return False
      try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
          return False
        return int(code.value) == 259
      finally:
        kernel32.CloseHandle(handle)
    except (OSError, TypeError, ValueError):
      return False
  try:
    os.kill(int(pid), 0)
    return True
  except (OSError, TypeError, ValueError):
    return False


def _deploy_cmd(
  mode: str,
  *,
  enable_trading: bool = False,
  skip_bridge_service: bool = False,
) -> tuple[list[str], dict, Path, Path] | tuple[None, str, None, None]:
  script = deploy_script_path()
  if not script.is_file():
    return None, f"Deploy script missing: {script}", None, None
  root = _repo_root()
  env = os.environ.copy()
  env["TRAINAPP_ROOT"] = str(root)
  desk = (env.get("TRAINAPP_DESK") or "").strip()
  runtime = (root / "runtime" / desk).resolve() if desk else root
  if desk:
    env["TRAINAPP_DESK"] = desk
    env["TRAINAPP_RUNTIME"] = str(runtime)
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
  return cmd, env, root, runtime


def run_deploy_mode(
  mode: str,
  *,
  enable_trading: bool = False,
  skip_bridge_service: bool = False,
  timeout_sec: float = 120.0,
) -> tuple[int, str, str]:
  """Run deploy_xm_forgebridge.ps1 for one Mode. Returns (code, stdout, stderr)."""
  built = _deploy_cmd(
    mode, enable_trading=enable_trading, skip_bridge_service=skip_bridge_service,
  )
  cmd, env, root, _runtime = built
  if cmd is None:
    return 2, "", str(env)
  try:
    run_kw: dict = dict(
      capture_output=True,
      text=True,
      check=False,
      cwd=str(root),
      env=env,
      timeout=max(30.0, float(timeout_sec)),
    )
    if os.name == "nt":
      run_kw["creationflags"] = _CREATE_NO_WINDOW
    res = subprocess.run(cmd, **run_kw)
  except subprocess.TimeoutExpired as e:
    out = (e.stdout or "") if isinstance(e.stdout, str) else (
      (e.stdout or b"").decode("utf-8", errors="replace") if e.stdout else ""
    )
    err = (e.stderr or "") if isinstance(e.stderr, str) else (
      (e.stderr or b"").decode("utf-8", errors="replace") if e.stderr else ""
    )
    return 124, out, (err + f"\nDeploy timeout sau {timeout_sec:.0f}s — MT5 có thể đang bận.").strip()
  return res.returncode, res.stdout or "", res.stderr or ""


def start_deploy_mode_async(
  mode: str,
  *,
  enable_trading: bool = False,
  skip_bridge_service: bool = False,
) -> dict:
  """Start deploy in a hidden process. Does not block the Streamlit script."""
  built = _deploy_cmd(
    mode, enable_trading=enable_trading, skip_bridge_service=skip_bridge_service,
  )
  cmd, env, root, runtime = built
  if cmd is None:
    raise RuntimeError(str(env))
  results = Path(runtime) / "results"
  results.mkdir(parents=True, exist_ok=True)
  out_path = results / "ui_deploy.out"
  err_path = results / "ui_deploy.err"
  out_f = open(out_path, "w", encoding="utf-8", errors="replace")
  err_f = open(err_path, "w", encoding="utf-8", errors="replace")
  kw: dict = dict(cwd=str(root), env=env, stdout=out_f, stderr=err_f)
  if os.name == "nt":
    kw["creationflags"] = _CREATE_NO_WINDOW
  proc = subprocess.Popen(cmd, **kw)
  _DEPLOY_HANDLES[proc.pid] = (proc, out_f, err_f)
  return {
    "pid": proc.pid,
    "out_path": str(out_path),
    "err_path": str(err_path),
    "started_at": time.time(),
  }


def poll_deploy_job(job: dict, *, timeout_sec: float = 120.0) -> dict:
  """Check a job from ``start_deploy_mode_async``. Never waits on PowerShell."""
  pid = int(job.get("pid") or 0)
  started = float(job.get("started_at") or time.time())
  elapsed = max(0.0, time.time() - started)
  handles = _DEPLOY_HANDLES.get(pid)
  alive = _pid_alive(pid)
  timed_out = False
  if alive and elapsed >= float(timeout_sec):
    timed_out = True
    if handles:
      try:
        handles[0].kill()
      except OSError:
        pass
    elif os.name == "nt":
      subprocess.run(
        ["taskkill", "/PID", str(pid), "/F"],
        capture_output=True, check=False,
        creationflags=_CREATE_NO_WINDOW,
      )
    alive = False
  if alive:
    return {"alive": True, "elapsed": elapsed, "code": None, "out": "", "err": ""}
  code = 0
  if handles:
    proc, out_f, err_f = handles
    try:
      code = proc.wait(timeout=2)
    except Exception:
      code = proc.returncode if proc.returncode is not None else 1
    for fh in (out_f, err_f):
      try:
        fh.close()
      except OSError:
        pass
    _DEPLOY_HANDLES.pop(pid, None)
  out = ""
  err = ""
  try:
    out = Path(job["out_path"]).read_text(encoding="utf-8", errors="replace")
  except OSError:
    pass
  try:
    err = Path(job["err_path"]).read_text(encoding="utf-8", errors="replace")
  except OSError:
    pass
  if timed_out:
    err = (err + f"\nDeploy timeout sau {timeout_sec:.0f}s — MT5 có thể đang bận.").strip()
    if not code:
      code = 124
  return {"alive": False, "elapsed": elapsed, "code": int(code or 0), "out": out, "err": err}


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


def rerun_app() -> None:
  """Full-page rerun so fragment spinners clear and EA chips refresh after Deploy."""
  try:
    st.rerun(scope="app")
  except TypeError:
    st.rerun()


@st.fragment(run_every=timedelta(seconds=1))
def mount_deploy_watch() -> None:
  """Poll background Deploy without blocking the websocket (avoids stuck spinner)."""
  job = st.session_state.get("_deploy_job")
  if not job:
    return
  stt = poll_deploy_job(job, timeout_sec=120.0)
  if stt.get("alive"):
    name = ea_live_name()
    st.info(
      f"Đang deploy `{name}`… {int(stt['elapsed'])}s — "
      "trang vẫn chạy, không cần refresh."
    )
    return
  st.session_state.pop("_deploy_job", None)
  code = int(stt.get("code") or 0)
  out = stt.get("out") or ""
  err = stt.get("err") or ""
  st.session_state["_deploy_done"] = {
    "code": code,
    "out": out,
    "err": err,
    "start_bridge": bool(job.get("start_bridge")),
    "model_ids": list(job.get("model_ids") or []),
    "sidebar": bool(job.get("sidebar")),
  }
  if job.get("sidebar"):
    st.session_state["_sidebar_deploy_result"] = (code, out, err, ea_live_name())
  rerun_app()


def render_sidebar_deploy_eas() -> None:
  """Compact Deploy Live — one script run, one MT5 restart."""
  live_ea = ea_live_name()
  result = st.session_state.pop("_sidebar_deploy_result", None)
  if result:
    code, out, err, name = result
    if code != 0:
      st.sidebar.error(f"Deploy thất bại ({code})")
      with st.sidebar.expander("Log", expanded=True):
        st.code((err + "\n" + out).strip() or "(empty)")
    else:
      st.sidebar.success(f"OK · {name}")
      with st.sidebar.expander("Log", expanded=False):
        st.code(out or "(no stdout)")
      st.toast("Đã deploy Live EA (test lịch sử: from/to trên cùng chart)")
  busy = bool(st.session_state.get("_deploy_job"))
  if st.sidebar.button(
    "Deploy Live",
    icon=":material/settings_suggest:",
    use_container_width=True,
    key="sidebar_mt5_deploy_live",
    disabled=busy,
    help=f"{live_ea} · 1 lần restart MT5 · test lịch sử dùng cùng EA",
  ):
    try:
      job = start_deploy_mode_async("Live", enable_trading=True)
    except Exception as e:
      st.sidebar.error(str(e))
      return
    st.session_state["_deploy_job"] = {**job, "start_bridge": False, "sidebar": True}
    rerun_app()
