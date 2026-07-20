"""So sánh backtest giữa các ERA profile (KB + OOS cố định)."""
from __future__ import annotations

import json
from pathlib import Path

from run_backtest import REPORT_DIR

COMPARE_PATH = REPORT_DIR / "era_dual_compare.json"

# Các profile ERA để so sánh (cùng OOS 2025–2026 khi có thể)
ERA_COMPARE_PROFILES = [
  {
    "key": "era_2022_2023",
    "label": "Học 2022–2023 → Kiểm chứng 2024",
    "kb_profile": "era_2022_2023",
    "kb_name": "Giai đoạn 2022–2023",
    "learn_from": "2022-01-01",
    "learn_until": "2023-12-31",
    "oos_from": "2024-01-01",
    "oos_to": "2024-12-31",
    "epochs": None,
    "oos_group": "2024",
  },
  {
    "key": "era_2023_2024",
    "label": "Học 2023–2024 → Kiểm chứng 2025–2026",
    "kb_profile": "era_2023_2024",
    "kb_name": "Giai đoạn 2023–2024",
    "learn_from": "2023-01-01",
    "learn_until": "2024-12-31",
    "oos_from": "2025-01-01",
    "oos_to": "2026-12-31",
    "epochs": 4,
    "oos_group": "2025-2026",
  },
  {
    "key": "era_2022_2024",
    "label": "Học 2022–2024 → Kiểm chứng 2025–2026",
    "kb_profile": "era_2022_2024",
    "kb_name": "Giai đoạn 2022–2024",
    "learn_from": "2022-01-01",
    "learn_until": "2024-12-31",
    "oos_from": "2025-01-01",
    "oos_to": "2026-12-31",
    "epochs": 3,
    "oos_group": "2025-2026",
  },
  {
    "key": "era_2024",
    "label": "Học 2024 (1 năm) → Kiểm chứng 2025–2026",
    "kb_profile": "era_2024",
    "kb_name": "Giai đoạn 2024",
    "learn_from": "2024-01-01",
    "learn_until": "2024-12-31",
    "oos_from": "2025-01-01",
    "oos_to": "2026-12-31",
    "epochs": 4,
    "oos_group": "2025-2026",
  },
]

ERA_DUAL_PROFILES = ERA_COMPARE_PROFILES  # alias


def discover_era_specs(
  oos_from: str = "2025-01-01",
  oos_to: str = "2026-12-31",
) -> list[dict]:
  """Preset ERA + mọi profile KB đã học (để chọn/so sánh trên GUI)."""
  from kb_profiles import DEFAULT_PROFILE_ID, is_legacy_kb_profile, list_profiles
  from gui.glossary import format_memory_profile

  specs = [dict(s) for s in ERA_COMPARE_PROFILES]
  known = {s["kb_profile"] for s in specs}
  for p in list_profiles():
    pid = p["id"]
    if is_legacy_kb_profile(pid) or not p.get("exists") or pid in known:
      continue
    tf = p.get("trained_from") or "?"
    tt = p.get("trained_to") or "?"
    specs.append({
      "key": pid,
      "label": f"{format_memory_profile(pid)} · học {tf[:10]}→{tt[:10]}",
      "kb_profile": pid,
      "kb_name": p.get("name") or format_memory_profile(pid),
      "learn_from": p.get("trained_from"),
      "learn_until": p.get("trained_to"),
      "oos_from": oos_from,
      "oos_to": oos_to,
      "epochs": p.get("epochs"),
      "oos_group": "custom",
    })
  return specs


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


def load_era_compare_cache() -> dict | None:
  return _read_json(COMPARE_PATH)


def save_era_compare_cache(reports: dict[str, dict], meta: dict | None = None):
  from datetime import datetime, timezone
  payload = {
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "profiles": ERA_COMPARE_PROFILES,
    "reports": reports,
    "meta": meta or {},
  }
  _write_json(COMPARE_PATH, payload)


def profile_exists(profile_id: str) -> bool:
  from kb_profiles import get_profile
  p = get_profile(profile_id)
  return bool(p and p.get("exists"))


def ensure_profile_learned(spec: dict, epochs: int, reset: bool = False) -> dict:
  """Học KB profile theo spec nếu chưa đủ epoch."""
  from gui.services import execute_learning
  p = spec["kb_profile"]
  if profile_exists(p) and not reset:
    from kb_profiles import get_profile
    meta = get_profile(p) or {}
    if int(meta.get("epochs") or 0) >= epochs:
      return {"skipped": True, "profile": p, "epochs": meta.get("epochs")}
  return execute_learning(
    epochs=epochs,
    reset_kb=reset,
    kb_profile=p,
    kb_name=spec["kb_name"],
    from_date=spec["learn_from"],
    until_date=spec["learn_until"],
  )


def ensure_era_2023_2024_learned(epochs: int = 4, reset: bool = False) -> dict:
  return ensure_profile_learned(ERA_COMPARE_PROFILES[1], epochs, reset)


def ensure_era_2022_2024_learned(epochs: int = 3, reset: bool = False) -> dict:
  return ensure_profile_learned(ERA_COMPARE_PROFILES[2], epochs, reset)


def ensure_era_2024_learned(epochs: int = 4, reset: bool = False) -> dict:
  return ensure_profile_learned(ERA_COMPARE_PROFILES[3], epochs, reset)


def run_era_backtest(spec: dict, kb_snapshot: int | str | None = None, on_progress=None) -> dict:
  from gui.services import execute_backtest
  snap = kb_snapshot if kb_snapshot is not None else spec.get("kb_snapshot")
  label = spec["label"]
  if snap is not None:
    label = f"{label} · ep{snap}"
  return execute_backtest(
    use_learning=True,
    kb_profile=spec["kb_profile"],
    kb_snapshot=snap,
    oos_from=spec["oos_from"],
    oos_to=spec["oos_to"],
    on_progress=on_progress,
    archive=True,
    archive_label=label,
    sync_workspace=False,
  )


def run_era_compare_backtests(
  on_progress=None,
  epoch_by_key: dict[str, int | str | None] | None = None,
  profile_keys: list[str] | None = None,
) -> dict[str, dict]:
  """Backtest các ERA profile; lưu cache."""
  catalog = {s["key"]: s for s in discover_era_specs()}
  if profile_keys:
    specs = [catalog[k] for k in profile_keys if k in catalog]
  else:
    specs = list(ERA_COMPARE_PROFILES)
  reports = {}
  for i, spec in enumerate(specs):
    if on_progress:
      on_progress(i, len(specs), spec["label"])
    snap = (epoch_by_key or {}).get(spec["key"], spec.get("kb_snapshot"))
    reports[spec["key"]] = run_era_backtest(spec, kb_snapshot=snap, on_progress=None)
  save_era_compare_cache(reports, meta={"epoch_by_key": epoch_by_key or {}, "keys": [s["key"] for s in specs]})
  return reports


def run_dual_era_backtests(
  on_progress=None,
  epoch_by_key: dict[str, int | str | None] | None = None,
) -> dict[str, dict]:
  """Alias — backtest tất cả profile trong ERA_COMPARE_PROFILES."""
  return run_era_compare_backtests(on_progress=on_progress, epoch_by_key=epoch_by_key)


def metrics_row(spec: dict, report: dict | None, epoch_label: str = "") -> dict:
  if not report:
    return {"Profile": spec["label"], "Lệnh": "—", "WR%": "—", "RR": "—", "Total R": "—", "DD": "—", "PF": "—"}
  o = report.get("overall_oos", {})
  ep_col = f" · {epoch_label}" if epoch_label else ""
  return {
    "Profile": spec["label"] + ep_col,
    "KB học": f"{spec['learn_from']} → {spec['learn_until']}",
    "OOS": f"{spec['oos_from']} → {spec['oos_to']}",
    "Lệnh": o.get("n_trades"),
    "WR%": o.get("win_rate_pct"),
    "RR": o.get("avg_rr"),
    "Total R": o.get("total_r"),
    "DD": o.get("max_drawdown_r"),
    "PF": o.get("profit_factor"),
    "Lệnh/tuần": o.get("trades_per_week"),
  }
