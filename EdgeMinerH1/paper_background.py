"""Single Paper Monitor cycle used by the detached Paper service."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from run_backtest import REPORT_DIR

CONFIG_PATH = REPORT_DIR / "paper_monitor_config.json"
STATE_PATH = REPORT_DIR / "paper_monitor_state.json"

_lock = threading.Lock()


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
  from paper_service import load_config as _load
  return _load()


def load_saved_state() -> dict | None:
  return _read_json(STATE_PATH)


def _update_config_meta(**fields):
  with _lock:
    cfg = load_config()
    cfg.update(fields)
    _write_json(CONFIG_PATH, cfg)


def _run_cycle(cfg: dict, *, force_refresh: bool = False) -> dict:
  from gui.services import get_paper_monitor
  from mt5_bridge.history_sync import start_history_sync

  if force_refresh:
    start_history_sync(force=True)
  state = get_paper_monitor(
    use_learning=bool(cfg.get("use_learning")),
    kb_profile=cfg.get("kb_profile") or "default",
    kb_snapshot=cfg.get("kb_snapshot"),
    spread_pips=float(cfg.get("spread_pips", 1.0)),
    slippage_pips=float(cfg.get("slippage_pips", 0.3)),
    risk_pct=float(cfg.get("risk_pct", 1.0)),
  )
  state["model_id"] = cfg.get("model_id")
  state["updated_at"] = _now_iso()
  state["background"] = True
  _write_json(STATE_PATH, state)
  return state


def run_cycle_now(cfg: dict | None = None, *, force_refresh: bool = False) -> dict:
  """Chạy một vòng cập nhật ngay (đồng bộ)."""
  cfg = cfg or load_config()
  try:
    state = _run_cycle(cfg, force_refresh=force_refresh)
    _update_config_meta(
      last_run_at=_now_iso(),
      last_error=None,
    )
    return state
  except Exception as e:
    _update_config_meta(last_error=str(e), last_run_at=_now_iso())
    raise
