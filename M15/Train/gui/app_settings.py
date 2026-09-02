"""App Settings — cấu hình mặc định cho grid search & học (thay trade profile sidebar)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import streamlit as st

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from run_backtest import REPORT_DIR

SETTINGS_PATH = REPORT_DIR / "app_settings.json"

# Seed mặc định — sau đó catalog lưu trong app_settings.json (learning_eras).
DEFAULT_LEARNING_ERAS = [
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
]

# Walk-forward OOS validation: era 6m → OOS 6m kế tiếp (M15 pipeline ooswalk).
OOS_WALKFORWARD_ERAS = [
  {
    "key": "2024-h1",
    "label": "2024 (6 tháng đầu)",
    "learn_from": "2024-01-01",
    "learn_until": "2024-06-30",
    "oos_from": "2024-07-01",
    "oos_to": "2024-12-31",
    "kb_profile": "era_2024_h1",
  },
  {
    "key": "2024-h2",
    "label": "2024 (6 tháng cuối)",
    "learn_from": "2024-07-01",
    "learn_until": "2024-12-31",
    "oos_from": "2025-01-01",
    "oos_to": "2025-06-30",
    "kb_profile": "era_2024_h2",
  },
  {
    "key": "2025-h1",
    "label": "2025 (6 tháng đầu)",
    "learn_from": "2025-01-01",
    "learn_until": "2025-06-30",
    "oos_from": "2025-07-01",
    "oos_to": "2025-12-31",
    "kb_profile": "era_2025_h1",
  },
]

# Backward-compat name used by older imports.
LEARNING_ERA_OPTIONS = DEFAULT_LEARNING_ERAS

# ID profile cũ (EdgeMiner1) → key Settings
LEGACY_KB_PROFILE_MAP = {
  "era_2022_2024": "2022-2025",
  "era_2023_2024": "2023-2025",
  "era_2024": "2024-2025",
  "era_2022_2023": "2022-2025",
}

DEFAULT_SETTINGS = {
  "id": "default",
  "label": "Cài đặt mặc định",
  "strategy_train_weeks": [8, 12],
  "learning_eras": [dict(e) for e in DEFAULT_LEARNING_ERAS],
  "learning_era_keys": ["2025-full"],
  "learning_loops": 3,
  "backtest_from": "2026-01-01",
  "backtest_to": "2026-12-31",
  "spread_pips": DEFAULT_SPREAD_PIPS,
  "slippage_pips": DEFAULT_SLIPPAGE_PIPS,
  "grid_objective": "quality",
  # EUR Bid/Ask fill-aware. Desk g23 override in default_settings_for_desk().
  "mining_presets": ["eur_fill_ss_lab"],
  "updated_at": None,
}

TRAIN_WEEK_OPTIONS = [3, 4, 5, 6, 7, 8, 9, 12]
# Compatibility import for removed comparison views.
TRAIN_MONTH_OPTIONS = TRAIN_WEEK_OPTIONS


def default_settings_for_desk() -> dict:
  """Reset-target for the running desk (EUR Bid/Ask vs GBP)."""
  import os
  from mining_presets import recommended_preset

  out = dict(DEFAULT_SETTINGS)
  out["learning_eras"] = [dict(e) for e in DEFAULT_LEARNING_ERAS] + [
    dict(e) for e in OOS_WALKFORWARD_ERAS
  ]
  out["learning_era_keys"] = ["2025-full"]
  out["backtest_from"] = "2026-01-01"
  out["backtest_to"] = "2026-12-31"
  out["spread_pips"] = float(DEFAULT_SPREAD_PIPS)
  out["slippage_pips"] = float(DEFAULT_SLIPPAGE_PIPS)
  out["mining_presets"] = [recommended_preset()]
  out["grid_objective"] = "quality"
  out["learning_loops"] = 3
  desk = (os.environ.get("TRAINAPP_DESK") or "").strip().lower()
  if desk.startswith("g"):
    # 4–5w fill_book n mỏng R<0; 12w confirm n=6–10. Densify 6+8 quanh ss_more.
    out["strategy_train_weeks"] = [6, 8]
  else:
    out["strategy_train_weeks"] = [8, 12]
  return out


def _slug(text: str, *, fallback: str = "era") -> str:
  slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(text or "").strip().lower()).strip("-")
  return (slug or fallback)[:48]


def make_era_key(label: str, learn_from: str, learn_until: str) -> str:
  base = _slug(label) or f"{str(learn_from)[:4]}-{str(learn_until)[:4]}"
  return base[:40]


def make_kb_profile(era_key: str) -> str:
  return "era_" + re.sub(r"[^a-zA-Z0-9_]+", "_", era_key).strip("_")


def _normalize_era(raw: dict | None) -> dict | None:
  if not isinstance(raw, dict):
    return None
  learn_from = str(raw.get("learn_from") or "").strip()[:10]
  learn_until = str(raw.get("learn_until") or "").strip()[:10]
  if not learn_from or not learn_until:
    return None
  label = str(raw.get("label") or "").strip() or f"{learn_from[:4]}–{learn_until[:4]}"
  key = str(raw.get("key") or "").strip() or make_era_key(label, learn_from, learn_until)
  kb_profile = str(raw.get("kb_profile") or "").strip() or make_kb_profile(key)
  oos_from = str(raw.get("oos_from") or "").strip()[:10] or None
  oos_to = str(raw.get("oos_to") or "").strip()[:10] or None
  era = {
    "key": key,
    "label": label,
    "learn_from": learn_from,
    "learn_until": learn_until,
    "kb_profile": kb_profile,
  }
  if oos_from and oos_to:
    era["oos_from"] = oos_from
    era["oos_to"] = oos_to
  return era


def _normalize_era_catalog(raw_eras) -> list[dict]:
  out: list[dict] = []
  seen: set[str] = set()
  for item in raw_eras or []:
    era = _normalize_era(item)
    if not era or era["key"] in seen:
      continue
    seen.add(era["key"])
    out.append(era)
  return out or [dict(e) for e in DEFAULT_LEARNING_ERAS]


def get_learning_era_catalog(settings: dict | None = None) -> list[dict]:
  """Catalog giai đoạn học (có thể thêm/bớt) — lưu trong settings."""
  if settings is None:
    data = _read_json(SETTINGS_PATH) or {}
    return _normalize_era_catalog(data.get("learning_eras") or DEFAULT_LEARNING_ERAS)
  return _normalize_era_catalog(settings.get("learning_eras") or DEFAULT_LEARNING_ERAS)


def _sanitize_settings(data: dict) -> dict:
  """Chỉ giữ giá trị hợp lệ theo schema Settings."""
  out = {**DEFAULT_SETTINGS, **data}
  catalog = _normalize_era_catalog(out.get("learning_eras") or DEFAULT_LEARNING_ERAS)
  out["learning_eras"] = catalog
  allowed_era_keys = {e["key"] for e in catalog}
  legacy_trains = out.get("strategy_train_months") or []
  trains = [t for t in (out.get("strategy_train_weeks") or legacy_trains) if t in TRAIN_WEEK_OPTIONS]
  out["strategy_train_weeks"] = trains or list(TRAIN_WEEK_OPTIONS)
  out.pop("strategy_train_months", None)
  eras = [k for k in (out.get("learning_era_keys") or []) if k in allowed_era_keys]
  out["learning_era_keys"] = eras or [e["key"] for e in catalog]
  out["learning_loops"] = max(1, min(12, int(out.get("learning_loops") or 4)))
  try:
    from mining_presets import list_presets, recommended_preset
    known = set(list_presets())
    raw_presets = out.get("mining_presets")
    if raw_presets is None:
      presets = [recommended_preset()]
    else:
      presets = [p for p in list(raw_presets or []) if p in known]
    out["mining_presets"] = presets
  except Exception:
    out["mining_presets"] = list(out.get("mining_presets") or [])
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


def era_by_key(key: str, settings: dict | None = None) -> dict | None:
  for e in get_learning_era_catalog(settings):
    if e["key"] == key:
      return e
  return None


def era_by_kb_profile(kb_profile_id: str | None, settings: dict | None = None) -> dict | None:
  """Map profile ID → giai đoạn Settings (hỗ trợ ID cũ)."""
  if not kb_profile_id:
    return None
  pid = str(kb_profile_id)
  for e in get_learning_era_catalog(settings):
    if e["kb_profile"] == pid:
      return e
  legacy_key = LEGACY_KB_PROFILE_MAP.get(pid)
  if legacy_key:
    return era_by_key(legacy_key, settings)
  return None


def kb_profile_label(profile_id: str | None) -> str:
  era = era_by_kb_profile(profile_id)
  if era:
    return era["label"]
  return str(profile_id or "—")


def canonical_kb_profile(profile_id: str | None) -> str | None:
  """Chuẩn hóa ID cũ → ID mới theo Settings."""
  era = era_by_kb_profile(profile_id)
  return era["kb_profile"] if era else profile_id


def resolve_learning_eras(settings: dict | None = None) -> list[dict]:
  settings = settings or load_settings()
  keys = settings.get("learning_era_keys") or []
  catalog = {e["key"]: e for e in get_learning_era_catalog(settings)}
  return [catalog[k] for k in keys if k in catalog]


def settings_kb_profile_ids(settings: dict | None = None) -> list[str]:
  return [e["kb_profile"] for e in resolve_learning_eras(settings)]


def default_learning_era(settings: dict | None = None) -> dict:
  eras = resolve_learning_eras(settings)
  if eras:
    return eras[0]
  catalog = get_learning_era_catalog(settings)
  return catalog[0] if catalog else dict(DEFAULT_LEARNING_ERAS[0])


def settings_backtest_period(settings: dict | None = None) -> tuple[str, str]:
  s = settings or load_settings()
  return s.get("backtest_from", "2026-01-01"), s.get("backtest_to", "2026-12-31")


def era_to_compare_spec(era: dict, settings: dict | None = None) -> dict:
  """Chuyển giai đoạn học trong Settings → spec so sánh/backtest."""
  s = settings or load_settings()
  if era.get("oos_from") and era.get("oos_to"):
    oos_from, oos_to = str(era["oos_from"])[:10], str(era["oos_to"])[:10]
  else:
    oos_from, oos_to = settings_backtest_period(s)
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


def settings_era_specs(settings: dict | None = None) -> list[dict]:
  """Danh sách giai đoạn — chỉ từ Settings (không preset cũ)."""
  s = settings or load_settings()
  return [era_to_compare_spec(e, s) for e in resolve_learning_eras(s)]


def settings_era_presets(settings: dict | None = None) -> list[tuple[str, str, str, str, str, str]]:
  """Preset (label, kb_id, learn_from, learn_until, oos_from, oos_to) từ Settings."""
  s = settings or load_settings()
  oos_from, oos_to = settings_backtest_period(s)
  out = []
  for era in resolve_learning_eras(s):
    label = f"{era['label']} → test {oos_from[:4]}–{oos_to[:4]}"
    out.append((label, era["kb_profile"], era["learn_from"], era["learn_until"], oos_from, oos_to))
  return out


def load_settings() -> dict:
  data = _read_json(SETTINGS_PATH)
  if not data:
    return dict(DEFAULT_SETTINGS)
  if not data.get("learning_eras"):
    data["learning_eras"] = [dict(e) for e in DEFAULT_LEARNING_ERAS]
  return _sanitize_settings(data)


def save_settings(settings: dict):
  from datetime import datetime, timezone
  settings = dict(settings)
  settings["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  _write_json(SETTINGS_PATH, settings)
  try:
    st.session_state.pop("app_settings", None)
    st.session_state.pop("settings_grid_signature", None)
  except Exception:
    pass


def get_settings() -> dict:
  if "app_settings" not in st.session_state:
    st.session_state["app_settings"] = load_settings()
  return st.session_state["app_settings"]


def update_settings(**fields) -> dict:
  s = dict(get_settings())
  s.update({k: v for k, v in fields.items() if v is not None})
  s = _sanitize_settings(s)
  save_settings(s)
  st.session_state["app_settings"] = s
  return s


def add_learning_era(
  *,
  label: str,
  learn_from: str,
  learn_until: str,
  activate: bool = True,
) -> dict:
  """Thêm giai đoạn học vào catalog (và optionally bật trong learning_era_keys)."""
  s = dict(get_settings())
  catalog = list(get_learning_era_catalog(s))
  key = make_era_key(label, learn_from, learn_until)
  existing_keys = {e["key"] for e in catalog}
  n = 2
  base_key = key
  while key in existing_keys:
    key = f"{base_key}-{n}"
    n += 1
  era = _normalize_era({
    "key": key,
    "label": label,
    "learn_from": learn_from,
    "learn_until": learn_until,
    "kb_profile": make_kb_profile(key),
  })
  if not era:
    raise ValueError("Giai đoạn học không hợp lệ.")
  if learn_from > learn_until:
    raise ValueError("Ngày bắt đầu phải trước ngày kết thúc.")
  catalog.append(era)
  s["learning_eras"] = catalog
  keys = list(s.get("learning_era_keys") or [])
  if activate and era["key"] not in keys:
    keys.append(era["key"])
  s["learning_era_keys"] = keys
  return update_settings(**s)


def remove_learning_era(era_key: str) -> dict:
  """Xóa giai đoạn khỏi catalog (không cho xóa hết)."""
  s = dict(get_settings())
  catalog = [e for e in get_learning_era_catalog(s) if e["key"] != era_key]
  if not catalog:
    raise ValueError("Phải giữ ít nhất một giai đoạn học.")
  s["learning_eras"] = catalog
  s["learning_era_keys"] = [
    k for k in (s.get("learning_era_keys") or []) if k != era_key
  ] or [catalog[0]["key"]]
  return update_settings(**s)


def settings_grid_signature(settings: dict | None = None) -> str:
  """Chữ ký cấu hình — đổi khi cần chạy lại grid."""
  s = settings or get_settings()
  eras = sorted(s.get("learning_era_keys") or [])
  trains = sorted(s.get("strategy_train_weeks") or [])
  catalog = {
    e["key"]: (
      f"{e['learn_from']}:{e['learn_until']}:{e['kb_profile']}"
      f":{e.get('oos_from', '')}:{e.get('oos_to', '')}"
    )
    for e in get_learning_era_catalog(s)
  }
  era_sig = ",".join(f"{k}={catalog.get(k, '')}" for k in eras)
  presets = ",".join(sorted(str(p) for p in (s.get("mining_presets") or [])))
  parts = [
    ",".join(str(t) for t in trains),
    era_sig,
    str(s.get("learning_loops", 4)),
    s.get("backtest_from", ""),
    s.get("backtest_to", ""),
    str(s.get("spread_pips", 1.0)),
    str(s.get("slippage_pips", 0.3)),
    f"msp:{presets}",
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
  trains = ", ".join(f"{t} tuần" for t in sorted(s.get("strategy_train_weeks") or []))
  eras = ", ".join(
    era_by_key(k, s)["label"] if era_by_key(k, s) else k
    for k in (s.get("learning_era_keys") or [])
  )
  oos = f"{s.get('backtest_from', '?')[:4]}–{s.get('backtest_to', '?')[:4]}"
  try:
    from mining_presets import preset_label
    msp = ", ".join(
      preset_label(p) for p in (s.get("mining_presets") or [])
    ) or "baseline miner"
  except Exception:
    msp = ", ".join(s.get("mining_presets") or []) or "baseline miner"
  return (
    f"Học chiến lược: **{trains}** · Giai đoạn học: **{eras}** · "
    f"Vòng học: **{s.get('learning_loops', 4)}** · Kiểm chứng: **{oos}** · "
    f"Fill Bid/Ask: **{s.get('spread_pips')} / {s.get('slippage_pips')} pip** · "
    f"Mining: **{msp}**"
  )


def merge_learning_eras_into_catalog(
  eras: list[dict],
  *,
  active_keys: list[str] | None = None,
) -> dict:
  """Gộp era vào catalog Settings (CLI-safe, không cần Streamlit session)."""
  s = _sanitize_settings(load_settings())
  catalog = {e["key"]: e for e in get_learning_era_catalog(s)}
  for raw in eras:
    era = _normalize_era(raw)
    if era:
      catalog[era["key"]] = era
  s["learning_eras"] = list(catalog.values())
  if active_keys is not None:
    allowed = set(catalog)
    s["learning_era_keys"] = [k for k in active_keys if k in allowed]
  s = _sanitize_settings(s)
  save_settings(s)
  return s


def grid_build_kwargs(settings: dict | None = None) -> dict:
  """Tham số build_grid từ settings."""
  s = settings or get_settings()
  eras = resolve_learning_eras(s)
  kb_profiles = [e["kb_profile"] for e in eras]
  loops = int(s.get("learning_loops") or 4)
  oos_by_profile: dict[str, tuple[str, str]] = {}
  for e in eras:
    of, ot = e.get("oos_from"), e.get("oos_to")
    if of and ot:
      oos_by_profile[e["kb_profile"]] = (str(of)[:10], str(ot)[:10])
  return {
    "train_weeks": list(s.get("strategy_train_weeks") or [8, 12]),
    "kb_profiles": kb_profiles,
    "include_kb_off": False,
    "epoch_mode": "selected",
    "selected_epochs": {e["kb_profile"]: list(range(1, loops + 1)) for e in eras},
    "oos_from": s.get("backtest_from", "2026-01-01"),
    "oos_to": s.get("backtest_to", "2026-12-31"),
    "oos_by_profile": oos_by_profile or None,
    "spread_pips": float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "max_runs": 200,
    "settings_signature": settings_grid_signature(s),
    "learning_era_keys": list(s.get("learning_era_keys") or []),
    "learning_loops": loops,
    # Opt-in only; empty keeps legacy grid combo count / keys.
    "mining_presets": list(s.get("mining_presets") or []) or None,
  }


def ensure_settings_loaded():
  get_settings()
  if not SETTINGS_PATH.exists():
    save_settings(dict(DEFAULT_SETTINGS))
