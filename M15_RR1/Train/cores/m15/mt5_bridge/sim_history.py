"""Archive Simulate (History Feed) runs so UI can browse past results.

Live EA I/O stays in ``mt5/bridge_sim*``. Snapshots land under
``results/simulate_runs/<run_id>/`` (run.json + trades.json).
"""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mt5_bridge.protocol import BRIDGE_SIM_DIR, atomic_write_json, ensure_bridge_dir
from mt5_bridge.trade_journal import compute_stats, load_trades
from run_backtest import REPORT_DIR

SIM_HISTORY_ROOT = REPORT_DIR / "simulate_runs"
LATEST_PATH = SIM_HISTORY_ROOT / "latest.json"


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write_json(path: Path, data: dict) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  atomic_write_json(path, data)


def new_sim_run_id() -> str:
  stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
  return f"sim_{stamp}_{uuid.uuid4().hex[:6]}"


def run_dir(run_id: str) -> Path:
  return SIM_HISTORY_ROOT / str(run_id)


def load_sim_run(run_id: str) -> dict | None:
  path = run_dir(run_id) / "run.json"
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return None


def _latest_run_id() -> str | None:
  if not LATEST_PATH.exists():
    return None
  try:
    meta = json.loads(LATEST_PATH.read_text(encoding="utf-8"))
  except Exception:
    return None
  rid = meta.get("run_id")
  return str(rid) if rid else None


def summarize_sim_run(run: dict, *, is_latest: bool = False) -> dict[str, Any]:
  stats = run.get("stats") or {}
  mids = run.get("model_ids") or ([] if not run.get("model_id") else [run.get("model_id")])
  return {
    "run_id": run.get("run_id"),
    "status": run.get("status"),
    "model_id": run.get("model_id"),
    "model_ids": list(mids),
    "n_models": len(mids),
    "risk_pct": run.get("risk_pct"),
    "date_from": run.get("date_from"),
    "date_to": run.get("date_to"),
    "delay_ms": run.get("delay_ms"),
    "bars_done": run.get("bars_done"),
    "bars_total": run.get("bars_total"),
    "n_fills": run.get("n_fills") or stats.get("n_trades"),
    "total_r": stats.get("total_r"),
    "win_rate_pct": stats.get("win_rate_pct"),
    "started_at": run.get("started_at"),
    "finished_at": run.get("finished_at"),
    "updated_at": run.get("updated_at") or run.get("finished_at") or run.get("started_at"),
    "error": run.get("error"),
    "is_latest": bool(is_latest),
  }


def list_sim_runs(*, limit: int = 50) -> list[dict[str, Any]]:
  if not SIM_HISTORY_ROOT.exists():
    return []
  latest_id = _latest_run_id()
  dirs = [
    p for p in SIM_HISTORY_ROOT.iterdir()
    if p.is_dir() and (p / "run.json").exists()
  ]
  dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
  out: list[dict[str, Any]] = []
  for path in dirs[: max(1, int(limit))]:
    run = load_sim_run(path.name)
    if not run:
      continue
    rid = str(run.get("run_id") or path.name)
    out.append(summarize_sim_run(run, is_latest=(rid == latest_id)))
  return out


def delete_sim_run(run_id: str) -> bool:
  rid = str(run_id or "").strip()
  if not rid or "/" in rid or "\\" in rid or rid in (".", ".."):
    return False
  path = run_dir(rid)
  if not path.is_dir() or not (path / "run.json").exists():
    return False
  was_latest = _latest_run_id() == rid
  shutil.rmtree(path, ignore_errors=True)
  if was_latest:
    remaining = list_sim_runs(limit=1)
    if remaining:
      _write_json(LATEST_PATH, {
        "run_id": remaining[0]["run_id"],
        "updated_at": remaining[0].get("updated_at") or _now(),
      })
    elif LATEST_PATH.exists():
      LATEST_PATH.unlink(missing_ok=True)
  return True


def archived_trades_dir(run_id: str) -> Path:
  """Directory that contains trades.json for an archived run."""
  return ensure_bridge_dir(run_dir(run_id))


def archive_sim_run(
  *,
  bridge_dir: Path | None = None,
  state: dict | None = None,
  status: str | None = None,
  force: bool = False,
) -> dict | None:
  """Snapshot current bridge_sim trades into simulate_runs/<run_id>/.

  Returns the run manifest, or None if there is nothing useful to archive
  (unless ``force`` and a run_id is already assigned).
  """
  from mt5_bridge.ea_simulator import load_sim_state, write_sim_state

  bridge_dir = ensure_bridge_dir(bridge_dir or BRIDGE_SIM_DIR)
  st = dict(state or load_sim_state() or {})
  if st.get("archived") and not force:
    existing = load_sim_run(str(st.get("run_id") or ""))
    return existing

  trades = load_trades(bridge_dir)
  bars_done = int(st.get("bars_done") or 0)
  if not force and not trades and bars_done <= 0:
    return None

  rid = str(st.get("run_id") or "").strip() or new_sim_run_id()
  dest = run_dir(rid)
  dest.mkdir(parents=True, exist_ok=True)

  # Copy trades.json as-is when present
  src_trades = bridge_dir / "trades.json"
  if src_trades.exists():
    try:
      shutil.copy2(src_trades, dest / "trades.json")
    except OSError:
      _write_json(dest / "trades.json", {"trades": trades})
  else:
    _write_json(dest / "trades.json", {"trades": trades})

  stats = compute_stats(trades, mode="auto", use_exit_time=False)
  model_ids = list(st.get("model_ids") or [])
  if not model_ids and st.get("model_id"):
    model_ids = [str(st.get("model_id"))]
  per_model = []
  for mid in model_ids:
    ms = compute_stats(trades, mode="auto", model_id=mid, use_exit_time=False)
    per_model.append({
      "model_id": mid,
      "n_trades": ms.get("n_trades"),
      "total_r": ms.get("total_r"),
      "win_rate_pct": ms.get("win_rate_pct"),
      "max_drawdown_r": ms.get("max_drawdown_r"),
      "avg_r": ms.get("avg_r"),
    })
  finished = status in ("completed", "stopped", "error") or st.get("status") in (
    "completed", "stopped", "error",
  )
  run = {
    "run_id": rid,
    "status": status or st.get("status") or ("completed" if finished else "running"),
    "model_id": st.get("model_id") or (model_ids[0] if model_ids else None),
    "model_ids": model_ids,
    "risk_pct": st.get("risk_pct"),
    "date_from": st.get("date_from"),
    "date_to": st.get("date_to"),
    "delay_ms": st.get("delay_ms"),
    "request_id": st.get("request_id"),
    "bars_done": bars_done,
    "bars_total": int(st.get("bars_total") or 0),
    "progress": st.get("progress"),
    "n_fills": len(trades),
    "stats": {
      "total_r": stats.get("total_r"),
      "win_rate_pct": stats.get("win_rate_pct"),
      "n_trades": stats.get("n_trades"),
      "max_drawdown_r": stats.get("max_drawdown_r"),
      "avg_r": stats.get("avg_r"),
    },
    "per_model": per_model,
    "error": st.get("error"),
    "started_at": st.get("started_at") or st.get("updated_at") or _now(),
    "finished_at": _now() if finished else st.get("finished_at"),
    "updated_at": _now(),
    "source": "ea_history_feed",
    "bridge_dir": str(bridge_dir),
  }
  _write_json(dest / "run.json", run)
  _write_json(LATEST_PATH, {"run_id": rid, "updated_at": run["updated_at"]})
  write_sim_state({
    "run_id": rid,
    "archived": True,
    "archive_path": str(dest),
  })
  return run
