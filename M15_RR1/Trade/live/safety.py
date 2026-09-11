"""Live safety: flatten, kill-switch, loss-guard config helpers."""
from __future__ import annotations

import json
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import BRIDGE_DIR, RESULTS_DIR
from package_store import load_roster

KILL_SWITCH_PATH = RESULTS_DIR / "kill_switch.json"
CONFIG_PATH = RESULTS_DIR / "mt5_bridge_config.json"
PID_PATH = RESULTS_DIR / "mt5_bridge_service.pid"


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  tmp.replace(path)


def _pid_alive(pid: int | None) -> bool:
  if not pid:
    return False
  try:
    os.kill(int(pid), 0)
    return True
  except OSError:
    return False


def write_flatten_command(
  *,
  bridge_dir: Path | None = None,
  reason: str = "live_flatten",
) -> dict:
  """Ask EA(s) to close roster magics via command.json."""
  dirs: list[Path]
  if bridge_dir is not None:
    dirs = [Path(bridge_dir)]
  else:
    dirs = [BRIDGE_DIR]
    # BUG-05: never rely on a single try — always union roster + workers + disk.
    try:
      from books import bridge_dir as bdir_fn, group_models_by_book
      roster = load_roster() if callable(load_roster) else {"models": []}
      models = list((roster or {}).get("models") or [])
      # Include disabled-with-magic books so orphan tickets still get command.json
      for (sym, tf), _ in group_models_by_book(models).items():
        p = bdir_fn(sym, tf, sim=False)
        if p not in dirs:
          dirs.append(p)
    except Exception:
      pass
    try:
      workers = _read(RESULTS_DIR / "live_workers.json") or {}
      for w in workers.get("workers") or []:
        p = Path(w.get("bridge_dir") or "")
        if p and p not in dirs:
          dirs.append(p)
    except Exception:
      pass
    try:
      from live_config import MT5_ROOT
      if MT5_ROOT.is_dir():
        for p in MT5_ROOT.iterdir():
          if p.is_dir() and p.name.startswith("bridge_live_") and p not in dirs:
            dirs.append(p)
    except Exception:
      pass

  payload = {
    "cmd": "close",
    "action": "FLAT",
    "signal_id": f"live_flatten_{int(datetime.now().timestamp())}",
    "reason": reason,
    "updated_at": _now(),
  }
  flat = {
    "action": "FLAT",
    "reason": reason,
    "halt": False,
    "updated_at": _now(),
  }
  roster_rows: list[dict] = []
  try:
    roster_rows = list((load_roster() or {}).get("models") or [])
  except Exception:
    roster_rows = []
  for bdir in dirs:
    bdir.mkdir(parents=True, exist_ok=True)
    _write(bdir / "command.json", payload)
    _write(bdir / "decision.json", flat)
    dec_dir = bdir / "decisions"
    dec_dir.mkdir(exist_ok=True)
    for row in roster_rows:
      mid = row.get("model_id")
      if not mid:
        continue
      # BUG-02: also FLAT disabled models that still own a magic (orphan tickets).
      if row.get("enabled") or row.get("magic") is not None:
        _write(dec_dir / f"{mid}.json", {**flat, "model_id": mid})
  return payload


def arm_kill_switch(*, reason: str = "manual_kill_switch", flatten: bool = True) -> dict:
  """Hard stop: flag file + disable config + SIGTERM bridge + optional flatten."""
  payload = {
    "armed": True,
    "reason": reason,
    "armed_at": _now(),
  }
  _write(KILL_SWITCH_PATH, payload)

  cfg = _read(CONFIG_PATH) or {}
  cfg.update({
    "enabled": False,
    "kill_switch": True,
    "kill_switch_reason": reason,
    "kill_switch_at": payload["armed_at"],
    "last_action": "kill_switch",
    "last_error": reason,
  })
  _write(CONFIG_PATH, cfg)

  try:
    from bridge_control import stop_bridge
    stop_bridge(flatten=False)
    try:
      stop_bridge(flatten=False, sim=True, sync_autostart=False)
    except Exception:
      pass
  except Exception:
    pid = cfg.get("service_pid")
    if not pid and PID_PATH.exists():
      try:
        pid = int(PID_PATH.read_text(encoding="utf-8").strip())
      except ValueError:
        pid = None
    if _pid_alive(pid):
      try:
        os.kill(int(pid), signal.SIGTERM)
      except OSError:
        pass

  if flatten:
    write_flatten_command(reason=f"kill_switch:{reason}")

  status = {
    "updated_at": _now(),
    "state": "halted",
    "halt_source": "kill_switch",
    "reason": reason,
  }
  _write(BRIDGE_DIR / "status.json", status)
  return payload


def disarm_kill_switch() -> dict:
  payload = {"armed": False, "disarmed_at": _now()}
  _write(KILL_SWITCH_PATH, payload)
  cfg = _read(CONFIG_PATH) or {}
  cfg.update({
    "kill_switch": False,
    "kill_switch_reason": None,
    "last_action": "kill_switch_disarm",
  })
  _write(CONFIG_PATH, cfg)
  return payload


def is_kill_switch_armed() -> bool:
  data = _read(KILL_SWITCH_PATH) or {}
  return bool(data.get("armed"))


def default_loss_guard_from_roster() -> dict[str, Any]:
  """Conservative defaults: per-model DD day/week and optional daily −R."""
  return {
    "loss_guard_enabled": True,
    "loss_guard_max_day": 0,
    "loss_guard_max_week": 0,
    "loss_guard_max_day_dd_r": 6.0,
    "loss_guard_max_week_dd_r": 10.0,
    "loss_guard_max_day_loss_r": 0.0,
    "loss_guard_max_week_loss_r": 0.0,
    "loss_guard_tripped": False,
    "loss_guard_tripped_at": None,
    "loss_guard_tripped_reason": None,
    "loss_guard_halted_models": [],
  }
