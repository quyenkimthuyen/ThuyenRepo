"""Grid search engine — quét tham số backtest walk-forward."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from config import (
  DEFAULT_SLIPPAGE_PIPS,
  DEFAULT_SPREAD_PIPS,
  DEFAULT_START_DATE,
  DEFAULT_TF,
  TARGET_TRADES_PER_WEEK,
)
from data_loader import load_eurusd_m15
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
  "quality": "Chất lượng (R/DD + PF + WR)",
}


@dataclass
class GridSpec:
  train_weeks: int
  use_kb: bool
  kb_profile: str | None
  kb_snapshot: int | None  # None = latest
  oos_from: str
  oos_to: str
  spread_pips: float = DEFAULT_SPREAD_PIPS
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS
  # Opt-in only. None keeps legacy grid keys / default MiningSearchSpace.
  mining_preset: str | None = None

  def key(self) -> str:
    snap = "latest" if self.kb_snapshot is None else f"ep{self.kb_snapshot:03d}"
    kb = self.kb_profile or "off"
    raw = f"{DEFAULT_TF}|{self.train_weeks}w|{kb}|{snap}|{self.oos_from}|{self.oos_to}"
    if self.mining_preset:
      raw += f"|msp:{self.mining_preset}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]

  def label(self) -> str:
    from gui.glossary import build_trade_profile_label
    if not self.use_kb:
      base = build_trade_profile_label({
        "train_weeks": self.train_weeks,
        "use_kb": False,
        "oos_from": self.oos_from,
        "oos_to": self.oos_to,
      })
    else:
      base = build_trade_profile_label({
        "train_weeks": self.train_weeks,
        "use_kb": True,
        "kb_profile": self.kb_profile,
        "kb_snapshot": self.kb_snapshot,
        "oos_from": self.oos_from,
        "oos_to": self.oos_to,
      })
    if self.mining_preset:
      return f"{base} · preset {self.mining_preset}"
    return base

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
  train_weeks: list[int],
  kb_profiles: list[str],
  include_kb_off: bool = True,
  epoch_mode: str = "latest",
  selected_epochs: dict[str, list[int | None]] | None = None,
  oos_from: str,
  oos_to: str,
  spread_pips: float = DEFAULT_SPREAD_PIPS,
  slippage_pips: float = DEFAULT_SLIPPAGE_PIPS,
  max_runs: int = 60,
  mining_presets: list[str] | None = None,
) -> list[GridSpec]:
  """Sinh danh sách GridSpec; cắt bớt nếu vượt max_runs.

  ``mining_presets`` is opt-in. Empty/None → one combo per train×KB (legacy).
  Non-empty → cartesian product with those presets (existing keys unchanged
  when preset is omitted from a given spec).
  """
  specs: list[GridSpec] = []
  base = dict(oos_from=oos_from, oos_to=oos_to, spread_pips=spread_pips, slippage_pips=slippage_pips)
  preset_names: list[str | None] = [None]
  if mining_presets:
    preset_names = list(mining_presets)

  for tm in train_weeks:
    for preset in preset_names:
      preset_kw = {"mining_preset": preset} if preset else {}
      if include_kb_off:
        specs.append(GridSpec(
          train_weeks=tm, use_kb=False, kb_profile=None, kb_snapshot=None,
          **base, **preset_kw,
        ))

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
            train_weeks=tm, use_kb=True, kb_profile=pid, kb_snapshot=snap,
            **base, **preset_kw,
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
  trains = len(kw.get("train_weeks") or [])
  profiles = len(kw.get("kb_profiles") or [])
  loops = int(kw.get("learning_loops") or 4)
  mining = kw.get("mining_presets") or []
  # build_grid: empty/None → one baseline slot; non-empty → len(presets)
  mining_n = len(mining) if mining else 1
  if kw.get("include_kb_off"):
    return trains * (1 + profiles * loops) * mining_n
  return trains * profiles * loops * mining_n


def grid_readiness(settings: dict | None = None) -> dict:
  """Kiểm tra điều kiện trước Grid Search."""
  from gui.app_settings import grid_build_kwargs, resolve_learning_eras
  from kb_profiles import get_profile

  kw = grid_build_kwargs(settings)
  eras = resolve_learning_eras(settings)
  missing = []
  not_ready = []
  for era in eras:
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
  # KB xong = đủ epoch cho mọi giai đoạn Settings — không so ready==expected
  # (mining presets nhân số combo, không liên quan học KB).
  kb_complete = bool(eras) and not missing and not not_ready
  return {
    "expected_combos": expected,
    "ready_combos": ready,
    "missing_profiles": missing,
    "under_trained": not_ready,
    "can_run": ready > 0 and kb_complete,
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
    frequency = float(row.get("trades_per_week") or 0)
    if str(DEFAULT_TF or "").upper() == "M5":
      # Allow M15-like snipers (~2–4 tpw) and denser stretch books.
      lo = max(1.5, TARGET_TRADES_PER_WEEK * 0.15)
      hi = max(TARGET_TRADES_PER_WEEK * 1.6, 8.0)
    else:
      lo, hi = 7.0, 10.0
    if r <= 0 or not lo <= frequency <= hi:
      return -1e12
    return r / max(dd, 0.5)
  if objective == "quality":
    r = float(row.get("total_r") or 0)
    dd = float(row.get("max_drawdown_r") or 1)
    pf = float(row.get("profit_factor") or 0)
    wr = float(row.get("win_rate_pct") or 0)
    n = int(row.get("n_trades") or 0)
    tpw = float(row.get("trades_per_week") or 0)
    m5 = str(DEFAULT_TF or "").upper() == "M5"
    min_n = 25 if m5 else 40
    if r <= 0 or pf < 1.2 or n < min_n:
      return -1e12
    wr_w = 1.6 if m5 else 0.8
    score = (r / max(dd, 0.5)) * 2.0 + pf * 25.0 + wr * wr_w + r * 0.04
    if m5 and tpw > 6.0:
      score -= (tpw - 6.0) * 6.0
    return score
  return float(row.get("total_r") or 0)


def run_single(spec: GridSpec) -> dict:
  from mining_presets import get_preset
  from strategy_miner import mining_search_space_from_dict

  df = load_eurusd_m15(DEFAULT_START_DATE)
  reset_kb_cache()
  if spec.use_kb and spec.kb_profile:
    set_kb_profile(spec.kb_profile, spec.kb_snapshot)
  space_dict = get_preset(spec.mining_preset) if spec.mining_preset else None
  search_space = (
    mining_search_space_from_dict(space_dict) if space_dict is not None else None
  )
  result = run_walk_forward(
    df,
    use_learning=spec.use_kb,
    train_weeks=spec.train_weeks,
    spread_pips=spec.spread_pips,
    slippage_pips=spec.slippage_pips,
    kb_profile=spec.kb_profile if spec.use_kb else None,
    kb_snapshot=spec.kb_snapshot if spec.use_kb else None,
    oos_from=spec.oos_from,
    oos_to=spec.oos_to,
    search_space=search_space,
    verbose=False,
  )
  o = result.get("overall_oos", {})
  row = {
    "key": spec.key(),
    "label": spec.label(),
    "train_weeks": spec.train_weeks,
    "use_kb": spec.use_kb,
    "kb_profile": spec.kb_profile,
    "kb_snapshot": spec.kb_snapshot,
    "oos_from": spec.oos_from,
    "oos_to": spec.oos_to,
    "mining_preset": spec.mining_preset,
    "mining_search_space": space_dict,
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
  on_progress: Callable[[int, int, str], None] | None = None,
  workers: int = 1,
) -> list[dict]:
  rows: list[dict] = []
  total = len(specs)
  workers = max(1, int(workers or 1))

  def _safe(spec: GridSpec) -> dict:
    try:
      return run_single(spec)
    except Exception as e:
      return {
        "key": spec.key(),
        "label": spec.label(),
        "train_weeks": spec.train_weeks,
        "use_kb": spec.use_kb,
        "kb_profile": spec.kb_profile,
        "kb_snapshot": spec.kb_snapshot,
        "error": str(e),
      }

  if workers <= 1 or total <= 1:
    for i, spec in enumerate(specs):
      if on_progress:
        on_progress(i + 1, total, spec.label())
      rows.append(_safe(spec))
  else:
    from concurrent.futures import ProcessPoolExecutor, as_completed
    done = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
      futs = {pool.submit(run_single, spec): spec for spec in specs}
      for fut in as_completed(futs):
        spec = futs[fut]
        done += 1
        if on_progress:
          on_progress(done, total, spec.label())
        try:
          rows.append(fut.result())
        except Exception as e:
          rows.append({
            "key": spec.key(),
            "label": spec.label(),
            "train_weeks": spec.train_weeks,
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


def apply_objective_to_run(
  run_payload: dict | None,
  objective: str,
  *,
  persist: bool = True,
) -> dict | None:
  """Re-rank an existing Grid run by ``objective`` and optionally rewrite files.

  Does not re-compute walk-forward — only reorders rows / best for display & TM.
  """
  if not run_payload:
    return None
  rows = [dict(r) for r in (run_payload.get("rows") or [])]
  # Ensure risk_adjusted column exists for ranking / table.
  for r in rows:
    if r.get("error"):
      continue
    if r.get("risk_adjusted") is None:
      r["risk_adjusted"] = round(_score(r, "risk_adjusted"), 3)
  valid = [r for r in rows if not r.get("error")]
  errors = [r for r in rows if r.get("error")]
  valid.sort(key=lambda r: _score(r, objective or "total_r"), reverse=True)
  ordered = valid + errors
  out = dict(run_payload)
  out["objective"] = objective
  out["rows"] = ordered
  out["best"] = ordered[0] if ordered else None
  out["n_runs"] = len(ordered)
  out["updated_at"] = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
  if persist:
    rid = str(out.get("run_id") or "").strip()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    if rid:
      path = RUNS_DIR / f"{rid}.json"
      with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    latest = load_latest_grid_run() or {}
    if not rid or latest.get("run_id") == rid or not latest:
      with open(LATEST_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
  return out


def load_latest_grid_run() -> dict | None:
  if not LATEST_PATH.exists():
    return None
  try:
    with open(LATEST_PATH, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def load_grid_run(run_id: str | None) -> dict | None:
  """Load one archived run by id. ``None`` / ``latest`` → latest.json."""
  if not run_id or str(run_id).strip().lower() in ("latest", "current", ""):
    return load_latest_grid_run()
  rid = str(run_id).strip()
  path = RUNS_DIR / f"{rid}.json"
  if not path.exists():
    # Allow passing bare timestamp id without gs_ prefix mismatch
    alt = RUNS_DIR / rid
    path = alt if alt.exists() else path
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def summarize_grid_config(config: dict | None) -> dict:
  """Normalize saved grid ``config`` into display-friendly fields."""
  cfg = config or {}
  trains = cfg.get("train_weeks") or []
  if isinstance(trains, (int, float)):
    trains = [int(trains)]
  trains = [int(t) for t in trains]

  kb_profiles = list(cfg.get("kb_profiles") or [])
  era_keys = list(cfg.get("learning_era_keys") or [])
  selected = cfg.get("selected_epochs") or {}
  loops = cfg.get("learning_loops")
  epoch_bits = []
  if isinstance(selected, dict) and selected:
    for pid, eps in selected.items():
      ep_txt = ",".join(str(e) if e is not None else "latest" for e in (eps or []))
      short = str(pid).replace("era_", "")
      epoch_bits.append(f"{short}:[{ep_txt}]")
  elif loops:
    epoch_bits.append(f"ep1–{loops}")

  mining = cfg.get("mining_presets")
  if mining is None:
    mining_txt = "baseline miner"
  elif not mining:
    mining_txt = "baseline miner"
  else:
    mining_txt = ", ".join(str(p) for p in mining)

  oos_from = str(cfg.get("oos_from") or "—")[:10]
  oos_to = str(cfg.get("oos_to") or "—")[:10]
  return {
    "train_weeks": trains,
    "train_txt": ",".join(str(t) for t in trains) + (" tuần" if trains else "—"),
    "kb_profiles": kb_profiles,
    "kb_txt": ", ".join(p.replace("era_", "") for p in kb_profiles) or (
      ", ".join(era_keys) if era_keys else "—"
    ),
    "learning_era_keys": era_keys,
    "epochs_txt": "; ".join(epoch_bits) if epoch_bits else "—",
    "learning_loops": loops,
    "oos_from": oos_from,
    "oos_to": oos_to,
    "oos_txt": f"{oos_from} → {oos_to}",
    "mining_presets": list(mining) if isinstance(mining, list) else mining,
    "mining_txt": mining_txt,
    "spread_pips": cfg.get("spread_pips"),
    "slippage_pips": cfg.get("slippage_pips"),
    "cost_txt": (
      f"spread {cfg.get('spread_pips', '—')} / slip {cfg.get('slippage_pips', '—')}"
    ),
    "settings_signature": cfg.get("settings_signature"),
  }


def list_grid_runs(*, limit: int = 40) -> list[dict]:
  """Summaries of archived Grid Search runs, newest first.

  Each item: run_id, updated_at, objective, n_runs, best_*, config summary fields, path, is_latest.
  """
  if not RUNS_DIR.exists():
    return []
  latest = load_latest_grid_run() or {}
  latest_id = latest.get("run_id")
  seen: set[str] = set()
  out: list[dict] = []

  paths = list(RUNS_DIR.glob("gs_*.json"))
  loaded: list[tuple[str, dict, str]] = []
  for path in paths:
    try:
      with open(path, encoding="utf-8") as f:
        data = json.load(f)
    except Exception:
      continue
    rid = str(data.get("run_id") or path.stem)
    loaded.append((rid, data, str(path)))

  loaded.sort(
    key=lambda item: str(item[1].get("updated_at") or ""),
    reverse=True,
  )

  for rid, data, path_str in loaded:
    if rid in seen:
      continue
    seen.add(rid)
    best = data.get("best") or (data.get("rows") or [None])[0] or {}
    rows = data.get("rows") or []
    n_ok = sum(1 for r in rows if not r.get("error"))
    summary = summarize_grid_config(data.get("config"))
    out.append({
      "run_id": rid,
      "updated_at": data.get("updated_at") or "",
      "objective": data.get("objective") or "total_r",
      "n_runs": int(data.get("n_runs") or len(rows)),
      "n_ok": n_ok,
      "best_total_r": best.get("total_r"),
      "best_win_rate_pct": best.get("win_rate_pct"),
      "best_label": best.get("label"),
      "settings_signature": summary.get("settings_signature"),
      "path": path_str,
      "is_latest": rid == latest_id,
      **summary,
    })
    if len(out) >= limit:
      break
  return out


def delete_grid_run(run_id: str) -> dict:
  """Delete one archived Grid Search run (``gs_*.json``).

  If that run is also ``latest.json``, promote the next newest archive to
  latest — or remove ``latest.json`` when no archives remain.
  """
  rid = str(run_id or "").strip()
  if not rid or rid in ("__latest__", "latest", "current"):
    raise ValueError("Chọn một run cụ thể (gs_…) để xóa.")
  if not rid.startswith("gs_"):
    # tolerate ids without prefix if file is gs_{id}.json
    candidate = RUNS_DIR / f"gs_{rid}.json"
    if candidate.exists():
      rid = f"gs_{rid}"

  path = RUNS_DIR / f"{rid}.json"
  if not path.exists():
    raise FileNotFoundError(f"Không tìm thấy Grid run `{rid}`.")

  latest = load_latest_grid_run() or {}
  was_latest = latest.get("run_id") == rid

  path.unlink()
  cleared = [path.name]

  if was_latest and LATEST_PATH.exists():
    LATEST_PATH.unlink()
    cleared.append(LATEST_PATH.name)

  # Promote next newest archive to latest.json when we removed current latest.
  remaining = list_grid_runs(limit=1)
  promoted = None
  if was_latest and remaining:
    nxt = load_grid_run(remaining[0]["run_id"])
    if nxt:
      RUNS_DIR.mkdir(parents=True, exist_ok=True)
      with open(LATEST_PATH, "w", encoding="utf-8") as f:
        json.dump(nxt, f, indent=2, ensure_ascii=False)
      promoted = nxt.get("run_id")

  return {
    "deleted": rid,
    "cleared": cleared,
    "was_latest": was_latest,
    "promoted_latest": promoted,
    "remaining": len(list_grid_runs(limit=10_000)),
  }


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
