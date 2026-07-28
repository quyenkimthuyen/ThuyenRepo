"""App Settings — TF-aware defaults for Grid Search & Learning (H1 ≠ M15)."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS, get_active_tf
from run_backtest import REPORT_DIR

SETTINGS_PATH = REPORT_DIR / "app_settings.json"

TRAIN_OPTIONS = [3, 6, 9]

LEARNING_ERA_OPTIONS_BY_TF: dict[str, list[dict]] = {
  "M15": [
    {
      "key": "2025-full",
      "label": "2025 (12 tháng)",
      "learn_from": "2025-01-01",
      "learn_until": "2025-12-31",
      "kb_profile": "era_2025_full",
    },
    {
      "key": "2025-h2",
      "label": "2025 (6 tháng cuối)",
      "learn_from": "2025-07-01",
      "learn_until": "2025-12-31",
      "kb_profile": "era_2025_h2",
    },
  ],
  "H1": [
    {
      "key": "2023-2025",
      "label": "2023–2025",
      "learn_from": "2023-01-01",
      "learn_until": "2025-12-31",
      "kb_profile": "era_2023_2025",
    },
    {
      "key": "2024-2025",
      "label": "2024–2025",
      "learn_from": "2024-01-01",
      "learn_until": "2025-12-31",
      "kb_profile": "era_2024_2025",
    },
  ],
}

DEFAULT_SETTINGS_BY_TF: dict[str, dict] = {
  "M15": {
    "id": "default",
    "label": "Cài đặt mặc định",
    "strategy_train_weeks": [3, 6, 9],
    "learning_era_keys": ["2025-full", "2025-h2"],
    "learning_loops": 4,
    "backtest_from": "2026-01-01",
    "backtest_to": "2026-12-31",
    "spread_pips": DEFAULT_SPREAD_PIPS,
    "slippage_pips": DEFAULT_SLIPPAGE_PIPS,
    "grid_objective": "risk_adjusted",
    "updated_at": None,
  },
  "H1": {
    "id": "default",
    "label": "Cài đặt mặc định",
    "strategy_train_months": [3, 6, 9],
    "learning_era_keys": ["2023-2025", "2024-2025"],
    "learning_loops": 4,
    "backtest_from": "2025-01-01",
    "backtest_to": "2026-12-31",
    "spread_pips": DEFAULT_SPREAD_PIPS,
    "slippage_pips": DEFAULT_SLIPPAGE_PIPS,
    "grid_objective": "total_r",
    "updated_at": None,
  },
}

# Legacy EdgeMiner1 profile id → settings era key
LEGACY_KB_PROFILE_MAP = {
  "era_2022_2024": "2023-2025",
  "era_2023_2024": "2023-2025",
  "era_2024": "2024-2025",
  "era_2022_2023": "2023-2025",
}

# Back-compat module aliases (resolve for active TF via helpers below)
LEARNING_ERA_OPTIONS = LEARNING_ERA_OPTIONS_BY_TF["M15"]
DEFAULT_SETTINGS = DEFAULT_SETTINGS_BY_TF["M15"]
TRAIN_WEEK_OPTIONS = TRAIN_OPTIONS
TRAIN_MONTH_OPTIONS = TRAIN_OPTIONS


def _tf() -> str:
  return str(get_active_tf()).upper()


def train_unit_for(tf: str | None = None) -> str:
  from runtime_profiles import get_tf_defaults
  return get_tf_defaults(tf or _tf()).train_unit


def learning_era_options(tf: str | None = None) -> list[dict]:
  t = str(tf or _tf()).upper()
  return list(LEARNING_ERA_OPTIONS_BY_TF.get(t, LEARNING_ERA_OPTIONS_BY_TF["M15"]))


def default_settings_for(tf: str | None = None) -> dict:
  t = str(tf or _tf()).upper()
  return dict(DEFAULT_SETTINGS_BY_TF.get(t, DEFAULT_SETTINGS_BY_TF["M15"]))


def train_field_name(tf: str | None = None) -> str:
  return "strategy_train_months" if train_unit_for(tf) == "months" else "strategy_train_weeks"


def _sanitize_settings(data: dict, tf: str | None = None) -> dict:
  """Keep only valid values for the active TF schema (H1 months ≠ M15 weeks)."""
  t = str(tf or _tf()).upper()
  eras = learning_era_options(t)
  allowed_era_keys = {e["key"] for e in eras}
  defaults = default_settings_for(t)
  out = {**defaults, **(data or {})}
  field = train_field_name(t)
  other = "strategy_train_weeks" if field == "strategy_train_months" else "strategy_train_months"
  raw_trains = out.get(field) or out.get(other) or []
  trains = [t_ for t_ in raw_trains if t_ in TRAIN_OPTIONS]
  out[field] = trains or list(TRAIN_OPTIONS)
  out.pop(other, None)
  era_keys = [k for k in (out.get("learning_era_keys") or []) if k in allowed_era_keys]
  out["learning_era_keys"] = era_keys or [e["key"] for e in eras]
  out["learning_loops"] = max(1, min(12, int(out.get("learning_loops") or 4)))
  if t == "H1" and out.get("grid_objective") not in (
    "total_r", "win_rate_pct", "profit_factor", "risk_adjusted",
  ):
    out["grid_objective"] = "total_r"
  return out


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


def era_by_key(key: str, tf: str | None = None) -> dict | None:
  for e in learning_era_options(tf):
    if e["key"] == key:
      return e
  # Cross-TF lookup (models / legacy)
  for opts in LEARNING_ERA_OPTIONS_BY_TF.values():
    for e in opts:
      if e["key"] == key:
        return e
  return None


def era_by_kb_profile(kb_profile_id: str | None, tf: str | None = None) -> dict | None:
  if not kb_profile_id:
    return None
  pid = str(kb_profile_id)
  for e in learning_era_options(tf):
    if e["kb_profile"] == pid:
      return e
  for opts in LEARNING_ERA_OPTIONS_BY_TF.values():
    for e in opts:
      if e["kb_profile"] == pid:
        return e
  legacy_key = LEGACY_KB_PROFILE_MAP.get(pid)
  if legacy_key:
    return era_by_key(legacy_key, tf)
  return None


def kb_profile_label(profile_id: str | None) -> str:
  era = era_by_kb_profile(profile_id)
  if era:
    return era["label"]
  return str(profile_id or "—")


def canonical_kb_profile(profile_id: str | None) -> str | None:
  era = era_by_kb_profile(profile_id)
  return era["kb_profile"] if era else profile_id


def resolve_learning_eras(settings: dict | None = None, tf: str | None = None) -> list[dict]:
  settings = settings or load_settings(tf=tf)
  keys = settings.get("learning_era_keys") or []
  return [e for k in keys if (e := era_by_key(k, tf))]


def settings_kb_profile_ids(settings: dict | None = None, tf: str | None = None) -> list[str]:
  return [e["kb_profile"] for e in resolve_learning_eras(settings, tf)]


def default_learning_era(settings: dict | None = None, tf: str | None = None) -> dict:
  eras = resolve_learning_eras(settings, tf)
  opts = learning_era_options(tf)
  return eras[0] if eras else opts[0]


def settings_backtest_period(settings: dict | None = None, tf: str | None = None) -> tuple[str, str]:
  s = settings or load_settings(tf=tf)
  d = default_settings_for(tf)
  return (
    s.get("backtest_from", d["backtest_from"]),
    s.get("backtest_to", d["backtest_to"]),
  )


def era_to_compare_spec(era: dict, settings: dict | None = None, tf: str | None = None) -> dict:
  s = settings or load_settings(tf=tf)
  oos_from, oos_to = settings_backtest_period(s, tf)
  loops = int(s.get("learning_loops") or 4)
  return {
    "key": era["kb_profile"],
    "label": f"Học {era['label']} → Kiểm chứng {oos_from[:4]}–{oos_to[:4]}",
    "kb_profile": era["kb_profile"],
    "kb_name": era["label"],
    "learn_from": era["learn_from"],
    "learn_until": era["learn_until"],
    "oos_from": oos_from,
    "oos_to": oos_to,
    "epochs": loops,
    "oos_group": f"{oos_from[:4]}-{oos_to[:4]}",
    "settings_era_key": era["key"],
  }


def settings_era_specs(settings: dict | None = None, tf: str | None = None) -> list[dict]:
  s = settings or load_settings(tf=tf)
  return [era_to_compare_spec(e, s, tf) for e in resolve_learning_eras(s, tf)]


def settings_era_presets(settings: dict | None = None, tf: str | None = None) -> list[tuple[str, str, str, str, str, str]]:
  s = settings or load_settings(tf=tf)
  oos_from, oos_to = settings_backtest_period(s, tf)
  out = []
  for era in resolve_learning_eras(s, tf):
    label = f"{era['label']} → test {oos_from[:4]}–{oos_to[:4]}"
    out.append((label, era["kb_profile"], era["learn_from"], era["learn_until"], oos_from, oos_to))
  return out


def load_settings(tf: str | None = None) -> dict:
  # REPORT_DIR follows active TF via tf_context / set_active_tf
  data = _read_json(SETTINGS_PATH)
  if not data:
    return default_settings_for(tf)
  return _sanitize_settings(data, tf)


def save_settings(settings: dict):
  from datetime import datetime, timezone
  settings = dict(settings)
  settings["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  _write_json(SETTINGS_PATH, settings)
  st.session_state.pop("app_settings", None)
  st.session_state.pop("app_settings_tf", None)
  st.session_state.pop("settings_grid_signature", None)
  st.session_state.pop("settings_grid_signature_M15", None)
  st.session_state.pop("settings_grid_signature_H1", None)


def get_settings() -> dict:
  """Cached settings for active TF — reloads when TF changes."""
  tf = _tf()
  if st.session_state.get("app_settings_tf") != tf or "app_settings" not in st.session_state:
    st.session_state["app_settings"] = load_settings(tf=tf)
    st.session_state["app_settings_tf"] = tf
  return st.session_state["app_settings"]


def clear_settings_cache() -> None:
  st.session_state.pop("app_settings", None)
  st.session_state.pop("app_settings_tf", None)
  st.session_state.pop("settings_grid_signature", None)
  st.session_state.pop("settings_grid_signature_M15", None)
  st.session_state.pop("settings_grid_signature_H1", None)


def update_settings(**fields) -> dict:
  s = dict(get_settings())
  s.update({k: v for k, v in fields.items() if v is not None})
  s = _sanitize_settings(s)
  save_settings(s)
  st.session_state["app_settings"] = s
  st.session_state["app_settings_tf"] = _tf()
  return s


def settings_grid_signature(settings: dict | None = None) -> str:
  """Chữ ký cấu hình — khớp format EdgeMinerH1/M15 (mỗi TF có results riêng)."""
  s = settings or get_settings()
  field = train_field_name()
  trains = sorted(s.get(field) or [])
  eras = sorted(s.get("learning_era_keys") or [])
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


def _normalize_grid_signature(sig: str | None) -> str:
  """Strip optional TF/field prefixes added by older unified builds."""
  if not sig:
    return ""
  parts = str(sig).split("|")
  # Legacy / EdgeMiner: 7 parts. Unified briefly used TF|field|… (9 parts).
  if len(parts) >= 9 and parts[0] in ("H1", "M15") and parts[1].startswith("strategy_train_"):
    parts = parts[2:]
  return "|".join(parts)


def _grid_signature_session_key(tf: str | None = None) -> str:
  return f"settings_grid_signature_{str(tf or _tf()).upper()}"


def settings_changed_since_last_grid() -> bool:
  """True only when current TF settings differ from that TF's last grid run."""
  key = _grid_signature_session_key()
  last_sig = st.session_state.get(key)
  if not last_sig:
    # Compat: old shared session key
    last_sig = st.session_state.get("settings_grid_signature")
  if not last_sig:
    from gui.grid_search_engine import load_latest_grid_run
    run = load_latest_grid_run()
    cfg = (run or {}).get("config") or {}
    last_sig = cfg.get("settings_signature")
    # Fallback: rebuild from stored OOS / trains if signature missing
    if not last_sig and run:
      unit = cfg.get("train_unit") or train_unit_for()
      trains = cfg.get("train_months") if unit == "months" else cfg.get("train_weeks")
      eras = cfg.get("learning_era_keys") or []
      last_sig = "|".join([
        ",".join(str(t) for t in sorted(trains or [])),
        ",".join(sorted(eras)),
        str(cfg.get("learning_loops", 4)),
        str(cfg.get("oos_from") or ""),
        str(cfg.get("oos_to") or ""),
        str(cfg.get("spread_pips", 1.0)),
        str(cfg.get("slippage_pips", 0.3)),
      ])
  if not last_sig:
    return False
  return _normalize_grid_signature(last_sig) != _normalize_grid_signature(
    settings_grid_signature()
  )


def format_settings_summary(settings: dict | None = None) -> str:
  s = settings or get_settings()
  unit = train_unit_for()
  field = train_field_name()
  unit_label = "tháng" if unit == "months" else "tuần"
  trains = ", ".join(f"{t} {unit_label}" for t in sorted(s.get(field) or []))
  eras = ", ".join(s.get("learning_era_keys") or [])
  oos_from = str(s.get("backtest_from") or "?")[:10]
  oos_to = str(s.get("backtest_to") or "?")[:10]
  return (
    f"**{_tf()}** · Học chiến lược: **{trains}** · Giai đoạn: **{eras}** · "
    f"Vòng học: **{s.get('learning_loops', 4)}** · "
    f"Kiểm chứng: **{oos_from} → {oos_to}**"
  )


def grid_build_kwargs(settings: dict | None = None) -> dict:
  s = settings or get_settings()
  eras = resolve_learning_eras(s)
  kb_profiles = [e["kb_profile"] for e in eras]
  loops = int(s.get("learning_loops") or 4)
  unit = train_unit_for()
  field = train_field_name()
  trains = list(s.get(field) or [3, 6, 9])
  d = default_settings_for()
  kw = {
    "kb_profiles": kb_profiles,
    "include_kb_off": False,
    "epoch_mode": "selected",
    "selected_epochs": {e["kb_profile"]: list(range(1, loops + 1)) for e in eras},
    "oos_from": s.get("backtest_from", d["backtest_from"]),
    "oos_to": s.get("backtest_to", d["backtest_to"]),
    "spread_pips": float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "max_runs": 200,
    "settings_signature": settings_grid_signature(s),
    "learning_era_keys": list(s.get("learning_era_keys") or []),
    "learning_loops": loops,
    "train_unit": unit,
    "tf": _tf(),
  }
  if unit == "months":
    kw["train_months"] = trains
  else:
    kw["train_weeks"] = trains
  return kw


def ensure_settings_loaded():
  get_settings()
  if not SETTINGS_PATH.exists():
    save_settings(default_settings_for())
