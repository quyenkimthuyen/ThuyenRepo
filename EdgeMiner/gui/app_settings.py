"""App Settings — cấu hình mặc định cho grid search & học (thay trade profile sidebar)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from run_backtest import REPORT_DIR

SETTINGS_PATH = REPORT_DIR / "app_settings.json"

# Giai đoạn học → kb_profile (đã học hoặc sẽ học)
LEARNING_ERA_OPTIONS = [
  {
    "key": "2022-2025",
    "label": "2022–2025",
    "learn_from": "2022-01-01",
    "learn_until": "2025-12-31",
    "kb_profile": "era_2022_2024",
  },
  {
    "key": "2023-2025",
    "label": "2023–2025",
    "learn_from": "2023-01-01",
    "learn_until": "2025-12-31",
    "kb_profile": "era_2023_2024",
  },
  {
    "key": "2024-2025",
    "label": "2024–2025",
    "learn_from": "2024-01-01",
    "learn_until": "2025-12-31",
    "kb_profile": "era_2024",
  },
]

DEFAULT_SETTINGS = {
  "id": "default",
  "label": "Cài đặt mặc định",
  "strategy_train_months": [3, 6, 9],
  "learning_era_keys": ["2022-2025", "2023-2025", "2024-2025"],
  "learning_loops": 4,
  "backtest_from": "2025-01-01",
  "backtest_to": "2026-12-31",
  "spread_pips": DEFAULT_SPREAD_PIPS,
  "slippage_pips": DEFAULT_SLIPPAGE_PIPS,
  "grid_objective": "total_r",
  "updated_at": None,
}


def _read_json(path: Path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path: Path, data: dict):
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
  tmp.replace(path)


def era_by_key(key: str) -> dict | None:
  for e in LEARNING_ERA_OPTIONS:
    if e["key"] == key:
      return e
  return None


def resolve_learning_eras(settings: dict | None = None) -> list[dict]:
  settings = settings or load_settings()
  keys = settings.get("learning_era_keys") or []
  return [e for k in keys if (e := era_by_key(k))]


def load_settings() -> dict:
  data = _read_json(SETTINGS_PATH)
  if not data:
    return dict(DEFAULT_SETTINGS)
  merged = {**DEFAULT_SETTINGS, **data}
  return merged


def save_settings(settings: dict):
  from datetime import datetime, timezone
  settings = dict(settings)
  settings["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  _write_json(SETTINGS_PATH, settings)
  st.session_state.pop("app_settings", None)
  st.session_state.pop("settings_grid_signature", None)


def get_settings() -> dict:
  if "app_settings" not in st.session_state:
    st.session_state["app_settings"] = load_settings()
  return st.session_state["app_settings"]


def update_settings(**fields) -> dict:
  s = dict(get_settings())
  s.update({k: v for k, v in fields.items() if v is not None})
  save_settings(s)
  st.session_state["app_settings"] = s
  return s


def settings_grid_signature(settings: dict | None = None) -> str:
  """Chữ ký cấu hình — đổi khi cần chạy lại grid."""
  s = settings or get_settings()
  eras = sorted(s.get("learning_era_keys") or [])
  trains = sorted(s.get("strategy_train_months") or [])
  parts = [
    ",".join(str(t) for t in trains),
    ",".join(eras),
    str(s.get("learning_loops", 4)),
    s.get("backtest_from", ""),
    s.get("backtest_to", ""),
    str(s.get("spread_pips", 1.0)),
    str(s.get("slippage_pips", 0.3)),
  ]
  return "|".join(parts)


def settings_changed_since_last_grid() -> bool:
  last_sig = st.session_state.get("settings_grid_signature")
  if not last_sig:
    from gui.grid_search_engine import load_latest_grid_run
    run = load_latest_grid_run()
    if run and run.get("config", {}).get("settings_signature"):
      last_sig = run["config"]["settings_signature"]
  return last_sig != settings_grid_signature()


def format_settings_summary(settings: dict | None = None) -> str:
  s = settings or get_settings()
  trains = ", ".join(f"{t}T" for t in sorted(s.get("strategy_train_months") or []))
  eras = ", ".join(s.get("learning_era_keys") or [])
  oos = f"{s.get('backtest_from', '?')[:4]}–{s.get('backtest_to', '?')[:4]}"
  return (
    f"Học chiến lược: **{trains}** · Giai đoạn học: **{eras}** · "
    f"Vòng học: **{s.get('learning_loops', 4)}** · Kiểm chứng: **{oos}**"
  )


def grid_build_kwargs(settings: dict | None = None) -> dict:
  """Tham số build_grid từ settings."""
  s = settings or get_settings()
  eras = resolve_learning_eras(s)
  kb_profiles = [e["kb_profile"] for e in eras]
  loops = int(s.get("learning_loops") or 4)
  return {
    "train_months": list(s.get("strategy_train_months") or [3, 6, 9]),
    "kb_profiles": kb_profiles,
    "include_kb_off": False,
    "epoch_mode": "selected",
    "selected_epochs": {e["kb_profile"]: list(range(1, loops + 1)) for e in eras},
    "oos_from": s.get("backtest_from", "2025-01-01"),
    "oos_to": s.get("backtest_to", "2026-12-31"),
    "spread_pips": float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "max_runs": 200,
    "settings_signature": settings_grid_signature(s),
    "learning_era_keys": list(s.get("learning_era_keys") or []),
    "learning_loops": loops,
  }


def ensure_settings_loaded():
  get_settings()
  if not SETTINGS_PATH.exists():
    save_settings(dict(DEFAULT_SETTINGS))
