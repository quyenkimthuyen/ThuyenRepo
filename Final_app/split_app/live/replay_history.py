"""Archive / list / reset Live OOS replay (parity) history."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from live_config import MT5_ROOT, RESULTS_DIR

HISTORY_DIR = RESULTS_DIR / "replay_history"
INDEX_PATH = HISTORY_DIR / "index.json"

# Current (latest) replay artifacts — wiped by reset_replay_history
CURRENT_GLOBS = (
  "parity_*.json",
  "parity_oos_batch.json",
  "replay_last.json",
  "replay_oos_*.json",
  "replay_oos_batch.json",
  "replay_oos_batch.log",
  "replay_oos_batch.pid",
  "replay_strategy_stats.json",
  "live_preflight.json",
  "remine_gate_last.json",
  "remine_gate_alerts.jsonl",
  "risk_cap_last.json",
  "risk_cap_alerts.jsonl",
  "risk_cap.lock",
  "risk_cap_reservations",
)


def _now() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read(path: Path) -> Any:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (OSError, json.JSONDecodeError):
    return None


def _write(path: Path, data: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(
    json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  tmp.replace(path)


def _rm(path: Path) -> bool:
  if not path.exists():
    return False
  try:
    if path.is_dir():
      import shutil
      shutil.rmtree(path)
    else:
      path.unlink()
    return True
  except OSError:
    return False


def _summarize_batch(payload: dict) -> dict[str, Any]:
  books = payload.get("books") or []
  models = []
  total_r = 0.0
  n_ok = n_fail = 0
  for b in books:
    for m in b.get("models") or []:
      mid = m.get("model_id")
      models.append({
        "model_id": mid,
        "label": m.get("label") or mid,
        "symbol": b.get("symbol") or m.get("symbol"),
        "timeframe": b.get("timeframe") or m.get("timeframe"),
        "total_r": m.get("total_r"),
        "lab_total_r": m.get("lab_total_r"),
        "delta_r": m.get("delta_r"),
        "win_rate_pct": m.get("win_rate_pct"),
        "lab_win_rate_pct": m.get("lab_win_rate_pct"),
        "n_trades": m.get("n_trades"),
        "ok": m.get("ok"),
        "error": m.get("error"),
      })
      if m.get("ok"):
        n_ok += 1
        try:
          total_r += float(m.get("total_r") or 0)
        except (TypeError, ValueError):
          pass
      else:
        n_fail += 1
  return {
    "n_books": len(books),
    "n_models": len(models),
    "n_ok": n_ok,
    "n_fail": n_fail,
    "total_r": round(total_r, 3),
    "models": models,
  }


def archive_parity_batch(payload: dict) -> dict[str, Any]:
  """Save a completed parity batch into replay_history/ and refresh index."""
  HISTORY_DIR.mkdir(parents=True, exist_ok=True)
  stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
  run_id = f"run_{stamp}"
  summary = _summarize_batch(payload)
  mode = str(payload.get("mode") or "schedule_parity")
  entry = {
    "run_id": run_id,
    "created_at": payload.get("updated_at") or _now(),
    "oos_from": payload.get("oos_from"),
    "oos_to": payload.get("oos_to"),
    "ok": payload.get("ok"),
    "mode": mode,
    **{k: summary[k] for k in ("n_books", "n_models", "n_ok", "n_fail", "total_r")},
  }
  full = {**payload, "run_id": run_id, "summary": summary, "mode": mode}
  path = HISTORY_DIR / f"{run_id}.json"
  _write(path, full)

  index = _read(INDEX_PATH) or {"runs": []}
  runs = [r for r in (index.get("runs") or []) if r.get("run_id") != run_id]
  runs.insert(0, {**entry, "file": path.name})
  # keep last 50 runs in index
  index = {"updated_at": _now(), "runs": runs[:50]}
  _write(INDEX_PATH, index)
  return entry


def archive_live_like_run(payload: dict | None = None) -> dict[str, Any]:
  """Archive a Live-like (paper/inline) batch into replay_history/."""
  from replay_control import load_strategy_stats, paper_results_summary

  paper = payload or paper_results_summary()
  stats = load_strategy_stats()
  HISTORY_DIR.mkdir(parents=True, exist_ok=True)
  stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
  run_id = f"run_{stamp}"
  models = []
  for b in paper.get("books") or []:
    for lab in b.get("labels") or [f"{b.get('symbol')} {b.get('timeframe')}"]:
      models.append({
        "label": lab,
        "symbol": b.get("symbol"),
        "timeframe": b.get("timeframe"),
        "n_fills": b.get("n_fills"),
        "n_signals": b.get("n_signals"),
        "ok": b.get("ok"),
        "status": b.get("status"),
      })
  summary = {
    "n_books": paper.get("n_books"),
    "n_models": paper.get("n_models"),
    "n_ok": paper.get("n_ok"),
    "n_fail": max(int(paper.get("n_models") or 0) - int(paper.get("n_ok") or 0), 0),
    "total_r": None,
    "n_fills": paper.get("n_fills"),
    "n_signals": paper.get("n_signals"),
    "models": models,
    "strategy_stats": {
      "schedule_hits": stats.get("schedule_hits"),
      "remine_count": stats.get("remine_count"),
      "skip_count": stats.get("skip_count"),
      "force_remine": stats.get("force_remine"),
    },
  }
  entry = {
    "run_id": run_id,
    "created_at": paper.get("updated_at") or _now(),
    "oos_from": paper.get("oos_from"),
    "oos_to": paper.get("oos_to"),
    "ok": paper.get("ok"),
    "mode": "live_like",
    "n_books": summary["n_books"],
    "n_models": summary["n_models"],
    "n_ok": summary["n_ok"],
    "n_fail": summary["n_fail"],
    "total_r": summary["total_r"],
    "n_fills": summary["n_fills"],
  }
  full = {
    **paper,
    "run_id": run_id,
    "summary": summary,
    "mode": "live_like",
    "strategy_stats": stats,
  }
  path = HISTORY_DIR / f"{run_id}.json"
  _write(path, full)
  index = _read(INDEX_PATH) or {"runs": []}
  runs = [r for r in (index.get("runs") or []) if r.get("run_id") != run_id]
  runs.insert(0, {**entry, "file": path.name})
  index = {"updated_at": _now(), "runs": runs[:50]}
  _write(INDEX_PATH, index)
  return entry


def list_replay_runs(*, limit: int = 30) -> list[dict[str, Any]]:
  index = _read(INDEX_PATH) or {}
  runs = list(index.get("runs") or [])
  if runs:
    return runs[:limit]
  # fallback: scan files if index missing
  if not HISTORY_DIR.exists():
    return []
  found = []
  for p in sorted(HISTORY_DIR.glob("run_*.json"), reverse=True):
    data = _read(p) or {}
    summ = data.get("summary") or _summarize_batch(data)
    found.append({
      "run_id": data.get("run_id") or p.stem,
      "created_at": data.get("updated_at") or data.get("created_at"),
      "oos_from": data.get("oos_from"),
      "oos_to": data.get("oos_to"),
      "ok": data.get("ok"),
      "n_books": summ.get("n_books"),
      "n_models": summ.get("n_models"),
      "n_ok": summ.get("n_ok"),
      "n_fail": summ.get("n_fail"),
      "total_r": summ.get("total_r"),
      "file": p.name,
    })
    if len(found) >= limit:
      break
  return found


def load_replay_run(run_id: str) -> dict[str, Any] | None:
  rid = str(run_id or "").strip()
  if not rid:
    return None
  if not re.fullmatch(r"run_\d{8}_\d{6}", rid):
    # still allow if file exists with that stem
    pass
  path = HISTORY_DIR / f"{rid}.json"
  if not path.exists() and not rid.endswith(".json"):
    # try via index
    for r in list_replay_runs(limit=50):
      if r.get("run_id") == rid and r.get("file"):
        path = HISTORY_DIR / str(r["file"])
        break
  return _read(path)


def latest_parity_snapshot() -> dict[str, Any] | None:
  """Current (non-archived) last batch if present."""
  batch = _read(RESULTS_DIR / "parity_oos_batch.json")
  if batch:
    return batch
  return _read(RESULTS_DIR / "replay_last.json")


def reset_replay_history(
  *,
  stop_replay_proc: bool = True,
  clear_archive: bool = True,
  clear_current: bool = True,
  clear_sim_journals: bool = True,
) -> dict[str, Any]:
  """Wipe replay/parity results (and optionally archived runs). Keeps packages/roster/OHLC."""
  out: dict[str, Any] = {
    "updated_at": _now(),
    "removed": [],
    "errors": [],
    "ok": True,
  }
  if stop_replay_proc:
    try:
      from replay_control import stop_replay
      stop_replay()
    except Exception as exc:
      out["errors"].append(f"stop_replay: {exc}")

  if clear_current:
    for pattern in CURRENT_GLOBS:
      for p in RESULTS_DIR.glob(pattern):
        if _rm(p):
          out["removed"].append(p.name)

  if clear_sim_journals and MT5_ROOT.exists():
    for bdir in MT5_ROOT.iterdir():
      if not bdir.is_dir() or not bdir.name.startswith("bridge_sim_live"):
        continue
      for name in (
        "fills.jsonl", "ea_fills.jsonl", "trades.json", "sim_control.json",
        "fill.json", "bar.json", "bars.json", "decision.json", "comm_log.jsonl",
      ):
        if _rm(bdir / name):
          out["removed"].append(f"{bdir.name}/{name}")
      dec = bdir / "decisions"
      if dec.is_dir():
        for child in list(dec.iterdir()):
          if _rm(child):
            out["removed"].append(f"{bdir.name}/decisions/{child.name}")

  if clear_archive and HISTORY_DIR.exists():
    n = 0
    for p in list(HISTORY_DIR.iterdir()):
      if _rm(p):
        n += 1
        out["removed"].append(f"replay_history/{p.name}")
    out["archive_files_removed"] = n

  out["ok"] = len(out["errors"]) == 0
  try:
    _write(RESULTS_DIR / "last_replay_reset.json", out)
  except OSError:
    pass
  return out
