"""Background worker — tự cập nhật Paper Monitor theo chu kỳ."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from run_backtest import REPORT_DIR

CONFIG_PATH = REPORT_DIR / "paper_monitor_config.json"
STATE_PATH = REPORT_DIR / "paper_monitor_state.json"

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop = threading.Event()


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _json_safe(obj):
  import numpy as np
  if isinstance(obj, dict):
    return {k: _json_safe(v) for k, v in obj.items()}
  if isinstance(obj, list):
    return [_json_safe(v) for v in obj]
  if isinstance(obj, (np.integer,)):
    return int(obj)
  if isinstance(obj, (np.floating,)):
    return float(obj)
  if isinstance(obj, np.ndarray):
    return obj.tolist()
  return obj


def _read_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path: Path, data: dict):
  REPORT_DIR.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(_json_safe(data), f, indent=2, ensure_ascii=False)
  tmp.replace(path)


def load_config() -> dict:
  from gui.paper_settings import load_pm_config
  return load_pm_config()


def save_ui_settings(
  *,
  use_learning: bool,
  kb_profile: str,
  kb_snapshot: int | str | None,
  spread_pips: float,
  slippage_pips: float,
  interval_minutes: int,
) -> None:
  """Alias — dùng gui.paper_settings.save_ui_settings."""
  from gui.paper_settings import save_ui_settings as _save
  _save(
    use_learning=use_learning,
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
    interval_minutes=interval_minutes,
  )


def load_saved_state() -> dict | None:
  return _read_json(STATE_PATH)


def is_background_enabled() -> bool:
  cfg = load_config()
  return bool(cfg.get("enabled")) and int(cfg.get("interval_minutes") or 0) > 0


def get_background_status() -> dict:
  cfg = load_config()
  alive = _thread is not None and _thread.is_alive()
  next_run_at = cfg.get("next_run_at")
  return {
    "enabled": bool(cfg.get("enabled")),
    "interval_minutes": int(cfg.get("interval_minutes") or 0),
    "running": alive and bool(cfg.get("enabled")),
    "last_run_at": cfg.get("last_run_at"),
    "next_run_at": next_run_at,
    "seconds_until_next": seconds_until_next(next_run_at),
    "last_error": cfg.get("last_error"),
    "updated_at": (_read_json(STATE_PATH) or {}).get("updated_at"),
  }


def seconds_until_next(next_run_at: str | None) -> int | None:
  """Giây còn lại đến lần reload tiếp theo (>= 0)."""
  if not next_run_at:
    return None
  try:
    nxt = datetime.fromisoformat(str(next_run_at))
    now = datetime.now(nxt.tzinfo) if nxt.tzinfo else datetime.now().astimezone()
    return max(0, int((nxt - now).total_seconds()))
  except Exception:
    return None


def _update_config_meta(**fields):
  with _lock:
    cfg = load_config()
    cfg.update(fields)
    _write_json(CONFIG_PATH, cfg)


def _run_cycle(cfg: dict, *, force_refresh: bool = False) -> dict:
  from config import DEFAULT_START_DATE
  from data_loader import download_gbpusd_h1
  from gui.services import get_paper_monitor

  # Background: chỉ tải lại khi cache cũ hơn ~1h. Manual: cố tải mới, lỗi thì dùng cache.
  interval = max(1, int(cfg.get("interval_minutes") or 15))
  max_age = max(1.0, interval / 60.0)
  download_gbpusd_h1(
    DEFAULT_START_DATE,
    force_refresh=force_refresh,
    allow_stale_on_error=True,
    max_cache_age_hours=None if force_refresh else max_age,
  )
  state = get_paper_monitor(
    use_learning=bool(cfg.get("use_learning")),
    kb_profile=cfg.get("kb_profile") or "default",
    kb_snapshot=cfg.get("kb_snapshot"),
    spread_pips=float(cfg.get("spread_pips", 1.0)),
    slippage_pips=float(cfg.get("slippage_pips", 0.3)),
  )
  state["updated_at"] = _now_iso()
  state["background"] = True
  _write_json(STATE_PATH, state)
  return state


def run_cycle_now(cfg: dict | None = None, *, force_refresh: bool = False) -> dict:
  """Chạy một vòng cập nhật ngay (đồng bộ)."""
  from datetime import timedelta

  cfg = cfg or load_config()
  try:
    state = _run_cycle(cfg, force_refresh=force_refresh)
    interval = int(cfg.get("interval_minutes") or 15)
    nxt = (datetime.now(timezone.utc) + timedelta(minutes=interval)).astimezone()
    _update_config_meta(
      last_run_at=_now_iso(),
      next_run_at=nxt.isoformat(timespec="seconds"),
      last_error=None,
    )
    return state
  except Exception as e:
    _update_config_meta(last_error=str(e), last_run_at=_now_iso())
    raise


def _worker_loop():
  while not _stop.is_set():
    cfg = load_config()
    if not cfg.get("enabled"):
      break
    interval = max(1, int(cfg.get("interval_minutes") or 15))
    if _stop.wait(interval * 60):
      break
    if _stop.is_set():
      break
    try:
      run_cycle_now(load_config())
    except Exception:
      pass


def stop_background():
  global _thread
  _stop.set()
  if _thread and _thread.is_alive():
    _thread.join(timeout=3)
  _thread = None
  _update_config_meta(enabled=False, interval_minutes=0, running=False)


def start_background(
  interval_minutes: int,
  *,
  use_learning: bool = False,
  kb_profile: str = "default",
  kb_snapshot: int | str | None = None,
  spread_pips: float = 1.0,
  slippage_pips: float = 0.3,
  run_immediately: bool = True,
):
  """Bật worker nền với chu kỳ phút."""
  global _thread
  if interval_minutes <= 0:
    stop_background()
    return

  stop_background()
  _stop.clear()

  cfg = {
    "enabled": True,
    "interval_minutes": interval_minutes,
    "use_learning": use_learning,
    "kb_profile": kb_profile,
    "kb_snapshot": kb_snapshot,
    "spread_pips": spread_pips,
    "slippage_pips": slippage_pips,
    "last_run_at": None,
    "next_run_at": None,
    "last_error": None,
    "running": True,
  }
  _write_json(CONFIG_PATH, cfg)

  if run_immediately:
    try:
      run_cycle_now(cfg)
    except Exception:
      pass

  _thread = threading.Thread(target=_worker_loop, name="paper-monitor-bg", daemon=True)
  _thread.start()


def sync_background_config(
  interval_minutes: int,
  *,
  use_learning: bool = False,
  kb_profile: str = "default",
  kb_snapshot: int | str | None = None,
  spread_pips: float = 1.0,
  slippage_pips: float = 0.3,
):
  """Đồng bộ cấu hình background (idempotent — gọi mỗi lần render OK)."""
  if interval_minutes <= 0:
    stop_background()
    return

  cfg = load_config()
  was_off = not cfg.get("enabled")
  new_cfg = {
    **cfg,
    "enabled": True,
    "interval_minutes": interval_minutes,
    "use_learning": use_learning,
    "kb_profile": kb_profile,
    "kb_snapshot": kb_snapshot,
    "spread_pips": spread_pips,
    "slippage_pips": slippage_pips,
    "running": True,
  }
  _write_json(CONFIG_PATH, new_cfg)
  ensure_background_running()
  if was_off:
    try:
      run_cycle_now(new_cfg)
    except Exception:
      pass


def update_background_config(
  interval_minutes: int,
  *,
  use_learning: bool = False,
  kb_profile: str = "default",
  kb_snapshot: int | str | None = None,
  spread_pips: float = 1.0,
  slippage_pips: float = 0.3,
):
  """Alias — cập nhật cấu hình background."""
  sync_background_config(
    interval_minutes,
    use_learning=use_learning,
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
    spread_pips=spread_pips,
    slippage_pips=slippage_pips,
  )


def ensure_background_running():
  """Khôi phục worker sau khi restart server Streamlit."""
  cfg = load_config()
  if not cfg.get("enabled") or int(cfg.get("interval_minutes") or 0) <= 0:
    return
  global _thread
  if _thread is not None and _thread.is_alive():
    return
  _stop.clear()
  _thread = threading.Thread(target=_worker_loop, name="paper-monitor-bg", daemon=True)
  _thread.start()
