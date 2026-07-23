"""So sánh backtest giữa các giai đoạn trong Settings."""
from __future__ import annotations

import json
from pathlib import Path

from run_backtest import REPORT_DIR

COMPARE_PATH = REPORT_DIR / "era_dual_compare.json"


def discover_era_specs(
  oos_from: str | None = None,
  oos_to: str | None = None,
) -> list[dict]:
  """Chỉ các giai đoạn học đã chọn trong Settings."""
  from gui.app_settings import get_settings, settings_era_specs

  s = get_settings()
  specs = settings_era_specs(s)
  if oos_from or oos_to:
    bf, bt = oos_from or s.get("backtest_from"), oos_to or s.get("backtest_to")
    return [{**spec, "oos_from": bf, "oos_to": bt} for spec in specs]
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
    "profiles": discover_era_specs(),
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
  """Backtest các giai đoạn Settings; lưu cache."""
  catalog = {s["key"]: s for s in discover_era_specs()}
  if profile_keys:
    specs = [catalog[k] for k in profile_keys if k in catalog]
  else:
    specs = list(catalog.values())
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
