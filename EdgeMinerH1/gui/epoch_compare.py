"""So sánh backtest OOS theo từng KB epoch snapshot."""
from __future__ import annotations

import json
import re
from pathlib import Path

from config import DEFAULT_START_DATE, DEFAULT_SLIPPAGE_PIPS, DEFAULT_SPREAD_PIPS
from data_loader import load_eurusd_h1
from kb_profiles import list_snapshots
from optimizer import reset_kb_cache, set_kb_profile
from run_backtest import REPORT_DIR, run_walk_forward

SWEEP_DIR = REPORT_DIR / "epoch_sweeps"


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


def sweep_cache_key(profile_id: str, oos_from: str, oos_to: str) -> str:
  pid = re.sub(r"[^a-zA-Z0-9_-]+", "_", profile_id)
  oos_f = (oos_from or "auto")[:10].replace("-", "")
  oos_t = (oos_to or "auto")[:10].replace("-", "")
  return f"{pid}__{oos_f}_{oos_t}"


def sweep_cache_path(profile_id: str, oos_from: str, oos_to: str) -> Path:
  return SWEEP_DIR / f"{sweep_cache_key(profile_id, oos_from, oos_to)}.json"


def load_epoch_sweep_cache(profile_id: str, oos_from: str, oos_to: str) -> dict | None:
  return _read_json(sweep_cache_path(profile_id, oos_from, oos_to))


def save_epoch_sweep_cache(
  profile_id: str,
  oos_from: str,
  oos_to: str,
  reports: dict[str, dict],
  snapshots: list[dict],
):
  from datetime import datetime, timezone
  payload = {
    "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "kb_profile": profile_id,
    "oos_from": oos_from,
    "oos_to": oos_to,
    "snapshots": snapshots,
    "reports": reports,
  }
  _write_json(sweep_cache_path(profile_id, oos_from, oos_to), payload)


def snapshot_key(s: dict) -> str:
  return "latest" if s.get("cumulative") is None else str(int(s["cumulative"]))


def _snapshot_key(s: dict) -> str:
  return snapshot_key(s)


def run_single_epoch_backtest(
  kb_profile: str,
  kb_snapshot: int | None,
  oos_from: str,
  oos_to: str,
) -> dict:
  df = load_eurusd_h1(DEFAULT_START_DATE)
  reset_kb_cache()
  set_kb_profile(kb_profile, kb_snapshot)
  return run_walk_forward(
    df,
    use_learning=True,
    spread_pips=DEFAULT_SPREAD_PIPS,
    slippage_pips=DEFAULT_SLIPPAGE_PIPS,
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
    oos_from=oos_from,
    oos_to=oos_to,
    verbose=False,
  )


def run_epoch_sweep(
  profile_id: str,
  oos_from: str,
  oos_to: str,
  on_progress=None,
) -> dict[str, dict]:
  """Backtest OOS cho mọi snapshot của profile."""
  snaps = list_snapshots(profile_id, include_latest=True)
  reports: dict[str, dict] = {}
  for i, s in enumerate(snaps):
    key = _snapshot_key(s)
    if on_progress:
      on_progress(i + 1, len(snaps), key)
    cum = s.get("cumulative")
    snap = None if cum is None else int(cum)
    reports[key] = run_single_epoch_backtest(profile_id, snap, oos_from, oos_to)
  save_epoch_sweep_cache(profile_id, oos_from, oos_to, reports, snaps)
  return reports


def sweep_metrics_table(snapshots: list[dict], reports: dict[str, dict]) -> list[dict]:
  rows = []
  for s in snapshots:
    key = _snapshot_key(s)
    rep = reports.get(key)
    ep = "Latest" if s.get("cumulative") is None else f"ep{s['cumulative']:03d}"
    row = {
      "Epoch": ep,
      "WR% in-sample": s.get("win_rate_pct"),
      "R in-sample": s.get("total_r"),
    }
    if rep:
      o = rep.get("overall_oos", {})
      row.update({
        "OOS lệnh": o.get("n_trades"),
        "OOS WR%": o.get("win_rate_pct"),
        "OOS Total R": o.get("total_r"),
        "OOS DD": o.get("max_drawdown_r"),
        "OOS PF": o.get("profit_factor"),
      })
    else:
      row.update({"OOS lệnh": "—", "OOS WR%": "—", "OOS Total R": "—", "OOS DD": "—", "OOS PF": "—"})
    rows.append(row)
  return rows


def best_oos_epoch(snapshots: list[dict], reports: dict[str, dict]) -> tuple[str | None, float | None]:
  """Epoch có OOS Total R cao nhất."""
  best_key, best_r = None, None
  for s in snapshots:
    key = _snapshot_key(s)
    rep = reports.get(key)
    if not rep:
      continue
    r = rep.get("overall_oos", {}).get("total_r")
    if r is None:
      continue
    if best_r is None or r > best_r:
      best_r = float(r)
      best_key = key
  return best_key, best_r


def epoch_key_to_snapshot(epoch_key: str) -> int | None:
  if epoch_key == "latest":
    return None
  try:
    return int(epoch_key)
  except ValueError:
    return None
