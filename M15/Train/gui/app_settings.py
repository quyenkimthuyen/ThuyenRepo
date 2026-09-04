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
# Chỉ era 6 tháng. Reset không đưa lại học 12 tháng (2025-full).
DEFAULT_LEARNING_ERAS = [
  {
    "key": "2025-h1",
    "label": "2025 (6 tháng đầu)",
    "learn_from": "2025-01-01",
    "learn_until": "2025-06-30",
    "kb_profile": "era_2025_h1",
  },
  {
    "key": "2025-h2",
    "label": "2025 (6 tháng cuối)",
    "learn_from": "2025-07-01",
    "learn_until": "2025-12-31",
    "kb_profile": "era_2025_h2",
  },
]

# Cửa sổ kiểm chứng Grid Search (mọi desk). Combo KB×OOS bị bỏ nếu khoảng học trùng OOS.
# Không còn OOS 12 tháng (2026-01-01 → 2026-12-31).
OOS_WINDOW_CATALOG = [
  {
    "key": "2026-h1",
    "label": "2026 (6 tháng đầu)",
    "oos_from": "2026-01-01",
    "oos_to": "2026-06-30",
  },
  {
    "key": "2025-h2",
    "label": "2025 (6 tháng cuối)",
    "oos_from": "2025-07-01",
    "oos_to": "2025-12-31",
  },
]
PRIMARY_OOS_KEY = "2026-h1"
DEFAULT_OOS_WINDOW_KEYS = [PRIMARY_OOS_KEY]

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
  "strategy_train_weeks": [8],
  "learning_eras": [dict(e) for e in DEFAULT_LEARNING_ERAS],
  "learning_era_keys": ["2025-h1"],
  "learning_loops": 3,
  "oos_windows": [dict(w) for w in OOS_WINDOW_CATALOG],
  "oos_window_keys": list(DEFAULT_OOS_WINDOW_KEYS),
  "backtest_from": "2026-01-01",
  "backtest_to": "2026-06-30",
  "spread_pips": DEFAULT_SPREAD_PIPS,
  "slippage_pips": DEFAULT_SLIPPAGE_PIPS,
  "grid_objective": "quality",
  # EUR 6m recipe. Desk g23 override in default_settings_for_desk().
  "mining_presets": ["eur_fill_ss_more"],
  "updated_at": None,
}

TRAIN_WEEK_OPTIONS = [3, 4, 5, 6, 7, 8, 9, 12]
# Compatibility import for removed comparison views.
TRAIN_MONTH_OPTIONS = TRAIN_WEEK_OPTIONS


def default_settings_for_desk() -> dict:
  """Reset-target for the running desk (EUR Bid/Ask vs GBP)."""
  import os

  out = dict(DEFAULT_SETTINGS)
  out["learning_eras"] = _normalize_era_catalog(
    [dict(e) for e in DEFAULT_LEARNING_ERAS] + [dict(e) for e in OOS_WALKFORWARD_ERAS]
  )
  out["oos_windows"] = [dict(w) for w in OOS_WINDOW_CATALOG]
  out["oos_window_keys"] = list(DEFAULT_OOS_WINDOW_KEYS)
  out["backtest_from"] = "2026-01-01"
  out["backtest_to"] = "2026-06-30"
  out["spread_pips"] = float(DEFAULT_SPREAD_PIPS)
  out["slippage_pips"] = float(DEFAULT_SLIPPAGE_PIPS)
  out["grid_objective"] = "quality"
  out["learning_loops"] = 3
  desk = (os.environ.get("TRAINAPP_DESK") or "").strip().lower()
  if desk.startswith("g"):
    out["strategy_train_weeks"] = [6]
    out["learning_era_keys"] = ["2025-h2"]
    out["mining_presets"] = ["gbp_fill_ss_tight"]
  else:
    out["strategy_train_weeks"] = [8]
    out["learning_era_keys"] = ["2025-h1"]
    out["mining_presets"] = ["eur_fill_ss_more"]
  return out


def _slug(text: str, *, fallback: str = "era") -> str:
  slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(text or "").strip().lower()).strip("-")
  return (slug or fallback)[:48]


def make_era_key(label: str, learn_from: str, learn_until: str) -> str:
  base = _slug(label) or f"{str(learn_from)[:4]}-{str(learn_until)[:4]}"
  return base[:40]


def make_kb_profile(era_key: str) -> str:
  return "era_" + re.sub(r"[^a-zA-Z0-9_]+", "_", era_key).strip("_")


def make_oos_key(label: str, oos_from: str, oos_to: str) -> str:
  return make_era_key(label, oos_from, oos_to)


def oos_window_option(window: dict) -> str:
  return f"{window['label']} ({window['oos_from']} → {window['oos_to']})"


def _normalize_oos_window(raw: dict | None) -> dict | None:
  if not isinstance(raw, dict):
    return None
  oos_from = str(raw.get("oos_from") or "").strip()[:10]
  oos_to = str(raw.get("oos_to") or "").strip()[:10]
  if not oos_from or not oos_to:
    return None
  label = str(raw.get("label") or "").strip() or f"{oos_from} → {oos_to}"
  key = str(raw.get("key") or "").strip() or make_oos_key(label, oos_from, oos_to)
  return {
    "key": key,
    "label": label,
    "oos_from": oos_from,
    "oos_to": oos_to,
  }


def _normalize_oos_catalog(raw_windows) -> list[dict]:
  out: list[dict] = []
  seen: set[str] = set()
  for item in raw_windows or []:
    window = _normalize_oos_window(item)
    if not window or window["key"] in seen:
      continue
    seen.add(window["key"])
    out.append(window)
  return out or [dict(w) for w in OOS_WINDOW_CATALOG]


def get_oos_window_catalog(settings: dict | None = None) -> list[dict]:
  """Catalog cửa sổ OOS (thêm/bớt trong Cài đặt)."""
  if settings is None:
    data = _read_json(SETTINGS_PATH) or {}
    return _normalize_oos_catalog(data.get("oos_windows") or OOS_WINDOW_CATALOG)
  return _normalize_oos_catalog(settings.get("oos_windows") or OOS_WINDOW_CATALOG)


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
  oos_catalog = _normalize_oos_catalog(out.get("oos_windows") or OOS_WINDOW_CATALOG)
  bf = str(out.get("backtest_from") or "")[:10]
  bt = str(out.get("backtest_to") or "")[:10]
  catalog_spans = {(w["oos_from"], w["oos_to"]) for w in oos_catalog}
  if bf and bt and bf <= bt and (bf, bt) not in catalog_spans:
    extra = _normalize_oos_window({
      "label": f"{bf} → {bt}",
      "oos_from": bf,
      "oos_to": bt,
    })
    if extra and extra["key"] not in {w["key"] for w in oos_catalog}:
      oos_catalog.append(extra)
  out["oos_windows"] = oos_catalog
  allowed_oos = {w["key"] for w in oos_catalog}
  oos_keys = [k for k in (out.get("oos_window_keys") or []) if k in allowed_oos]
  out["oos_window_keys"] = oos_keys or [oos_catalog[0]["key"]]
  by_oos = {w["key"]: w for w in oos_catalog}
  active_oos = [by_oos[k] for k in out["oos_window_keys"] if k in by_oos]
  primary = next((w for w in active_oos if w["key"] == PRIMARY_OOS_KEY), None)
  if primary is None and active_oos:
    primary = active_oos[0]
  if primary:
    out["backtest_from"] = primary["oos_from"]
    out["backtest_to"] = primary["oos_to"]
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


def periods_overlap(a_from, a_to, b_from, b_to) -> bool:
  """Inclusive date overlap. Adjacent ranges (…06-30 vs 07-01) do not overlap."""
  a0, a1 = str(a_from or "")[:10], str(a_to or "")[:10]
  b0, b1 = str(b_from or "")[:10], str(b_to or "")[:10]
  if not a0 or not a1 or not b0 or not b1:
    return False
  return a0 <= b1 and b0 <= a1


def kb_learn_overlaps_oos(learn_from, learn_until, oos_from, oos_to) -> bool:
  """True when KB learn span shares any calendar day with the OOS window."""
  return periods_overlap(learn_from, learn_until, oos_from, oos_to)


def resolve_oos_windows(settings: dict | None = None) -> list[dict]:
  """Cửa sổ OOS đang bật trong Settings (Grid / pipeline)."""
  s = settings if settings is not None else load_settings()
  catalog = get_oos_window_catalog(s)
  by_key = {w["key"]: dict(w) for w in catalog}
  keys = list(s.get("oos_window_keys") or [])
  out: list[dict] = []
  seen: set[tuple[str, str]] = set()
  for k in keys:
    w = by_key.get(k)
    if not w:
      continue
    sig = (w["oos_from"], w["oos_to"])
    if sig in seen:
      continue
    seen.add(sig)
    out.append(w)
  if out:
    return out
  if catalog:
    return [dict(catalog[0])]
  return [dict(OOS_WINDOW_CATALOG[0])]


def describe_kb_oos_pairs(settings: dict | None = None) -> list[dict]:
  """Era × OOS windows with overlap flag — for Settings preview / readiness."""
  s = settings if settings is not None else load_settings()
  rows: list[dict] = []
  for era in resolve_learning_eras(s):
    for w in resolve_oos_windows(s):
      overlap = kb_learn_overlaps_oos(
        era["learn_from"], era["learn_until"], w["oos_from"], w["oos_to"],
      )
      rows.append({
        "era_key": era["key"],
        "era_label": era["label"],
        "kb_profile": era["kb_profile"],
        "learn_from": era["learn_from"],
        "learn_until": era["learn_until"],
        "oos_key": w["key"],
        "oos_label": w["label"],
        "oos_from": w["oos_from"],
        "oos_to": w["oos_to"],
        "overlap": overlap,
        "ok": not overlap,
      })
  return rows


def count_valid_kb_oos_slots(settings: dict | None = None) -> int:
  """Số cặp giai đoạn học × cửa sổ OOS không trùng ngày."""
  return sum(1 for row in describe_kb_oos_pairs(settings) if row["ok"])


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
  return s.get("backtest_from", "2026-01-01"), s.get("backtest_to", "2026-06-30")


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
  else:
    st.session_state["app_settings"] = _sanitize_settings(st.session_state["app_settings"])
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


def _append_oos_window(
  s: dict,
  *,
  label: str,
  oos_from: str,
  oos_to: str,
  activate: bool = True,
) -> dict:
  """CLI-safe: thêm cửa sổ OOS vào catalog (không cần Streamlit)."""
  s = dict(s)
  catalog = list(get_oos_window_catalog(s))
  oos_from = str(oos_from)[:10]
  oos_to = str(oos_to)[:10]
  if oos_from > oos_to:
    raise ValueError("Ngày bắt đầu phải trước ngày kết thúc.")
  for w in catalog:
    if w["oos_from"] == oos_from and w["oos_to"] == oos_to:
      raise ValueError("Cửa sổ OOS này đã có trong danh sách.")
  key = make_oos_key(label, oos_from, oos_to)
  existing = {w["key"] for w in catalog}
  n = 2
  base_key = key
  while key in existing:
    key = f"{base_key}-{n}"
    n += 1
  window = _normalize_oos_window({
    "key": key,
    "label": label,
    "oos_from": oos_from,
    "oos_to": oos_to,
  })
  if not window:
    raise ValueError("Cửa sổ OOS không hợp lệ.")
  catalog.append(window)
  s["oos_windows"] = catalog
  keys = list(s.get("oos_window_keys") or [])
  if activate and window["key"] not in keys:
    keys.append(window["key"])
  s["oos_window_keys"] = keys
  return _sanitize_settings(s)


def add_oos_window(
  *,
  label: str,
  oos_from: str,
  oos_to: str,
  activate: bool = True,
) -> dict:
  """Thêm cửa sổ OOS vào catalog (và optionally bật cho Grid)."""
  if not str(label or "").strip():
    raise ValueError("Nhập tên cửa sổ OOS.")
  s = _append_oos_window(
    get_settings(),
    label=str(label).strip(),
    oos_from=oos_from,
    oos_to=oos_to,
    activate=activate,
  )
  return update_settings(**s)


def remove_oos_window(oos_key: str) -> dict:
  """Xóa cửa sổ OOS khỏi catalog (không cho xóa hết)."""
  s = dict(get_settings())
  catalog = [w for w in get_oos_window_catalog(s) if w["key"] != oos_key]
  if not catalog:
    raise ValueError("Phải giữ ít nhất một cửa sổ OOS.")
  s["oos_windows"] = catalog
  s["oos_window_keys"] = [
    k for k in (s.get("oos_window_keys") or []) if k != oos_key
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
  oos_cat = {
    w["key"]: f"{w['oos_from']}:{w['oos_to']}"
    for w in get_oos_window_catalog(s)
  }
  oos_keys = s.get("oos_window_keys") or []
  oos_sig = ",".join(f"{k}={oos_cat.get(k, '')}" for k in oos_keys)
  parts = [
    ",".join(str(t) for t in trains),
    era_sig,
    str(s.get("learning_loops", 4)),
    oos_sig,
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
  oos_windows = resolve_oos_windows(s)
  oos = " · ".join(w["label"] for w in oos_windows) or (
    f"{s.get('backtest_from', '?')[:4]}–{s.get('backtest_to', '?')[:4]}"
  )
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
  windows = resolve_oos_windows(s)
  oos_windows = [(w["oos_from"], w["oos_to"]) for w in windows]
  primary = windows[0] if windows else {
    "oos_from": s.get("backtest_from", "2026-01-01"),
    "oos_to": s.get("backtest_to", "2026-06-30"),
  }
  for w in windows:
    if w.get("key") == PRIMARY_OOS_KEY:
      primary = w
      break
  kb_learn_by_profile = {
    e["kb_profile"]: (str(e["learn_from"])[:10], str(e["learn_until"])[:10])
    for e in eras
  }
  return {
    "train_weeks": list(s.get("strategy_train_weeks") or [8]),
    "kb_profiles": kb_profiles,
    "include_kb_off": False,
    "epoch_mode": "selected",
    "selected_epochs": {e["kb_profile"]: list(range(1, loops + 1)) for e in eras},
    "oos_from": primary["oos_from"],
    "oos_to": primary["oos_to"],
    # Settings OOS windows apply to every era; do not let era.oos_* replace them.
    "oos_by_profile": None,
    "oos_windows": oos_windows,
    "kb_learn_by_profile": kb_learn_by_profile,
    "skip_kb_oos_overlap": True,
    "spread_pips": float(s.get("spread_pips", DEFAULT_SPREAD_PIPS)),
    "slippage_pips": float(s.get("slippage_pips", DEFAULT_SLIPPAGE_PIPS)),
    "max_runs": 200,
    "settings_signature": settings_grid_signature(s),
    "learning_era_keys": list(s.get("learning_era_keys") or []),
    "oos_window_keys": list(s.get("oos_window_keys") or DEFAULT_OOS_WINDOW_KEYS),
    "learning_loops": loops,
    # Opt-in only; empty keeps legacy grid combo count / keys.
    "mining_presets": list(s.get("mining_presets") or []) or None,
  }


def ensure_settings_loaded():
  get_settings()
  if not SETTINGS_PATH.exists():
    save_settings(dict(DEFAULT_SETTINGS))
