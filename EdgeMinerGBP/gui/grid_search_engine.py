"""Grid search engine — quét tham số backtest walk-forward."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from config import DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS, DEFAULT_START_DATE
from data_loader import load_gbpusd_h1
from kb_profiles import list_snapshots, list_profiles, kb_valid_for_backtest
from optimizer import reset_kb_cache, set_kb_profile
from run_backtest import REPORT_DIR, run_walk_forward

RUNS_DIR = REPORT_DIR / "grid_search"
LATEST_PATH = RUNS_DIR / "latest.json"

OBJECTIVES = {
  "total_r": "Tổng R (cao nhất)",
  "win_rate_pct": "Tỷ lệ thắng % (cao nhất)",
  "profit_factor": "Hệ số lợi nhuận (cao nhất)",
  "risk_adjusted": "R / sụt giảm (cao nhất)",
}


@dataclass
class GridSpec:
  train_months: int
  use_kb: bool
  kb_profile: str | None
  kb_snapshot: int | None  # None = latest
  oos_from: str
  oos_to: str
  spread_pips: float = DEFAULT_SPREAD_PIPS
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS

  def key(self) -> str:
    snap = "latest" if self.kb_snapshot is None else f"ep{self.kb_snapshot:03d}"
    kb = self.kb_profile or "off"
    raw = f"{self.train_months}|{kb}|{snap}|{self.oos_from}|{self.oos_to}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

  def label(self) -> str:
    from gui.glossary import build_trade_profile_label
    if not self.use_kb:
      return build_trade_profile_label({
        "train_months": self.train_months,
        "use_kb": False,
        "oos_from": self.oos_from,
        "oos_to": self.oos_to,
      })
    return build_trade_profile_label({
      "train_months": self.train_months,
      "use_kb": True,
      "kb_profile": self.kb_profile,
      "kb_snapshot": self.kb_snapshot,
      "oos_from": self.oos_from,
      "oos_to": self.oos_to,
    })

  def _snap_label(self) -> str:
    return "latest" if self.kb_snapshot is None else f"ep{self.kb_snapshot:03d}"


def available_kb_profiles() -> list[str]:
  from kb_profiles import list_era_profiles
  return [p["id"] for p in list_era_profiles()]


def snapshots_for_profile(profile_id: str, *, include_latest: bool = True) -> list[int | None]:
  snaps = list_snapshots(profile_id, include_latest=include_latest)
  out: list[int | None] = []
  for s in snaps:
    cum = s.get("cumulative")
    out.append(None if cum is None else int(cum))
  return out or [None]


def build_grid(
  *,
  train_months: list[int],
  kb_profiles: list[str],
  include_kb_off: bool = True,
  epoch_mode: str = "latest",
  selected_epochs: dict[str, list[int | None]] | None = None,
  oos_from: str,
  oos_to: str,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  max_runs: int = 60,
) -> list[GridSpec]:
  """Sinh danh sách GridSpec; cắt bớt nếu vượt max_runs."""
  specs: list[GridSpec] = []
  base = dict(oos_from=oos_from, oos_to=oos_to, spread_pips=spread_pips, slippage_pips=slippage_pips)

  for tm in train_months:
    if include_kb_off:
      specs.append(GridSpec(train_months=tm, use_kb=False, kb_profile=None, kb_snapshot=None, **base))

    for pid in kb_profiles:
      ok, _ = kb_valid_for_backtest(pid, oos_from, oos_to)
      if not ok:
        continue
      if epoch_mode == "latest":
        epochs: list[int | None] = [None]
      elif epoch_mode == "all":
        epochs = snapshots_for_profile(pid)
      else:
        epochs = (selected_epochs or {}).get(pid) or [None]

      for snap in epochs:
        specs.append(GridSpec(
          train_months=tm, use_kb=True, kb_profile=pid, kb_snapshot=snap, **base,
        ))

  if len(specs) > max_runs:
    specs = specs[:max_runs]
  return specs


def estimate_grid_count(**kwargs) -> tuple[int, int]:
  """Returns (count, capped_count)."""
  max_runs = kwargs.get("max_runs", 60)
  full = build_grid(**{**kwargs, "max_runs": 10_000})
  capped = min(len(full), max_runs)
  return len(full), capped


def expected_grid_count_from_settings(settings: dict | None = None) -> int:
  """Số combo lý thuyết theo Settings (không cần KB đã học)."""
  from gui.app_settings import grid_build_kwargs
  kw = grid_build_kwargs(settings)
  trains = len(kw.get("train_months") or [])
  profiles = len(kw.get("kb_profiles") or [])
  loops = int(kw.get("learning_loops") or 4)
  if kw.get("include_kb_off"):
    return trains * (1 + profiles * loops)
  return trains * profiles * loops


def grid_readiness(settings: dict | None = None) -> dict:
  """Kiểm tra điều kiện trước Grid Search."""
  from gui.app_settings import grid_build_kwargs, resolve_learning_eras
  from kb_profiles import get_profile

  kw = grid_build_kwargs(settings)
  missing = []
  not_ready = []
  for era in resolve_learning_eras(settings):
    pid = era["kb_profile"]
    p = get_profile(pid)
    loops = int(kw.get("learning_loops") or 4)
    if not p or not p.get("exists"):
      missing.append({"id": pid, "label": era["label"], "epochs_needed": loops})
      continue
    have = int(p.get("epochs") or 0)
    if have < loops:
      not_ready.append({
        "id": pid, "label": era["label"],
        "epochs_have": have, "epochs_needed": loops,
      })

  specs, _ = build_grid_from_settings(settings)
  expected = expected_grid_count_from_settings(settings)
  ready = len(specs)
  kb_complete = (
    expected > 0
    and ready == expected
    and not missing
    and not not_ready
  )
  return {
    "expected_combos": expected,
    "ready_combos": ready,
    "missing_profiles": missing,
    "under_trained": not_ready,
    "can_run": ready > 0,
    "kb_complete": kb_complete,
  }


def _score(row: dict, objective: str) -> float:
  if objective == "total_r":
    return float(row.get("total_r") or 0)
  if objective == "win_rate_pct":
    return float(row.get("win_rate_pct") or 0)
  if objective == "profit_factor":
    return float(row.get("profit_factor") or 0)
  if objective == "risk_adjusted":
    r = float(row.get("total_r") or 0)
    dd = float(row.get("max_drawdown_r") or 1)
    return r / max(dd, 0.5)
  return float(row.get("total_r") or 0)


def run_single(spec: GridSpec, *, reopt_period: str = "week") -> dict:
  df = load_gbpusd_h1(DEFAULT_START_DATE)
  reset_kb_cache()
  if spec.use_kb and spec.kb_profile:
    set_kb_profile(spec.kb_profile, spec.kb_snapshot)
  result = run_walk_forward(
    df,
    use_learning=spec.use_kb,
    train_months=spec.train_months,
    spread_pips=spec.spread_pips,
    slippage_pips=spec.slippage_pips,
    kb_profile=spec.kb_profile if spec.use_kb else None,
    kb_snapshot=spec.kb_snapshot if spec.use_kb else None,
    oos_from=spec.oos_from,
    oos_to=spec.oos_to,
    reopt_period=reopt_period,
    verbose=False,
  )
  o = result.get("overall_oos", {})
  row = {
    "key": spec.key(),
    "label": spec.label(),
    "train_months": spec.train_months,
    "use_kb": spec.use_kb,
    "kb_profile": spec.kb_profile,
    "kb_snapshot": spec.kb_snapshot,
    "oos_from": spec.oos_from,
    "oos_to": spec.oos_to,
    "n_trades": o.get("n_trades"),
    "win_rate_pct": o.get("win_rate_pct"),
    "avg_rr": o.get("avg_rr"),
    "total_r": o.get("total_r"),
    "max_drawdown_r": o.get("max_drawdown_r"),
    "profit_factor": o.get("profit_factor"),
    "trades_per_week": o.get("trades_per_week"),
    "error": None,
  }
  row["risk_adjusted"] = round(_score(row, "risk_adjusted"), 3)
  return row


def run_grid(
  specs: list[GridSpec],
  *,
  objective: str = "total_r",
  reopt_period: str = "week",
  on_progress: Callable[[int, int, str], None] | None = None,
) -> list[dict]:
  rows: list[dict] = []
  total = len(specs)
  for i, spec in enumerate(specs):
    if on_progress:
      on_progress(i + 1, total, spec.label())
    try:
      rows.append(run_single(spec, reopt_period=reopt_period))
    except Exception as e:
      rows.append({
        "key": spec.key(),
        "label": spec.label(),
        "train_months": spec.train_months,
        "use_kb": spec.use_kb,
        "kb_profile": spec.kb_profile,
        "kb_snapshot": spec.kb_snapshot,
        "error": str(e),
      })
  rows.sort(key=lambda r: _score(r, objective), reverse=True)
  return rows


def save_grid_run(
  rows: list[dict],
  *,
  config: dict,
  objective: str,
  run_id: str | None = None,
) -> str:
  RUNS_DIR.mkdir(parents=True, exist_ok=True)
  ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
  rid = run_id or f"gs_{ts}"
  payload = {
    "run_id": rid,
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "objective": objective,
    "config": config,
    "n_runs": len(rows),
    "best": rows[0] if rows else None,
    "rows": rows,
  }
  path = RUNS_DIR / f"{rid}.json"
  with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)
  with open(LATEST_PATH, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)
  return rid


def load_latest_grid_run() -> dict | None:
  if not LATEST_PATH.exists():
    return None
  try:
    with open(LATEST_PATH, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def existing_row_keys(rows: list[dict] | None) -> set[str]:
  """Key combo đã chạy thành công — dùng cho grid tăng dần."""
  if not rows:
    return set()
  return {
    r["key"] for r in rows
    if r.get("key") and not r.get("error")
  }


def filter_specs_for_incremental(
  specs: list[GridSpec],
  existing_rows: list[dict] | None,
) -> tuple[list[GridSpec], list[dict]]:
  """Chỉ giữ combo chưa có kết quả; trả về (specs_mới, rows_giữ_lại)."""
  keys = existing_row_keys(existing_rows)
  kept = [r for r in (existing_rows or []) if r.get("key") in keys or not r.get("error")]
  new_specs = [s for s in specs if s.key() not in keys]
  return new_specs, kept


def build_grid_from_settings(settings: dict | None = None) -> tuple[list[GridSpec], dict]:
  from gui.app_settings import grid_build_kwargs
  kwargs = grid_build_kwargs(settings)
  sig = kwargs.pop("settings_signature", None)
  era_keys = kwargs.pop("learning_era_keys", [])
  loops = kwargs.pop("learning_loops", 4)
  kwargs.pop("reopt_period", None)
  specs = build_grid(**kwargs)
  config = {
    **{k: v for k, v in kwargs.items()},
    "settings_signature": sig,
    "learning_era_keys": era_keys,
    "learning_loops": loops,
    "source": "app_settings",
  }
  return specs, config


def merge_grid_results(
  existing_rows: list[dict],
  new_rows: list[dict],
  *,
  objective: str = "total_r",
) -> list[dict]:
  by_key: dict[str, dict] = {}
  for r in existing_rows + new_rows:
    k = r.get("key")
    if not k:
      continue
    prev = by_key.get(k)
    if not prev or (prev.get("error") and not r.get("error")):
      by_key[k] = r
  merged = list(by_key.values())
  merged.sort(key=lambda r: _score(r, objective), reverse=True)
  return merged


def apply_best_to_profile(row: dict, *, run_id: str | None = None):
  from gui.trade_model import create_trade_model
  return create_trade_model(row, run_id=run_id, set_active=True)


apply_best_to_workspace = apply_best_to_profile


def apply_best_as_new_trade_profile(row: dict, *, run_id: str | None = None, label: str | None = None):
  from gui.trade_model import create_trade_model
  return create_trade_model(row, run_id=run_id, label=label, set_active=True)
