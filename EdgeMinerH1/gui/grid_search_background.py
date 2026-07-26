"""Grid Search background worker — chạy nền, tiến trình lưu file."""
from __future__ import annotations

import json
import threading
from dataclasses import asdict
from datetime import datetime, timezone

from gui.grid_search_engine import (
  GridSpec,
  RUNS_DIR,
  _score,
  run_single,
  save_grid_run,
)

JOB_STATE_PATH = RUNS_DIR / "job_state.json"

_lock = threading.Lock()
_thread: threading.Thread | None = None
_cancel = threading.Event()


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path) -> dict | None:
  if not path.exists():
    return None
  try:
    with open(path, encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None


def _write_json(path, data: dict):
  RUNS_DIR.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
  tmp.replace(path)


def spec_to_dict(spec: GridSpec) -> dict:
  return asdict(spec)


def spec_from_dict(data: dict) -> GridSpec:
  return GridSpec(**data)


def load_job_state() -> dict | None:
  return _read_json(JOB_STATE_PATH)


def is_grid_running() -> bool:
  state = load_job_state()
  if not state or state.get("status") != "running":
    return False
  return _thread is not None and _thread.is_alive()


def get_grid_status() -> dict:
  state = load_job_state() or {}
  alive = _thread is not None and _thread.is_alive()
  status = state.get("status", "idle")
  if status == "running" and not alive:
    status = "interrupted"
  total = int(state.get("total") or 0)
  done = int(state.get("done") or 0)
  pct = (done / total * 100) if total else 0
  return {
    "status": status,
    "running": alive and status == "running",
    "run_id": state.get("run_id"),
    "objective": state.get("objective"),
    "total": total,
    "done": done,
    "pct": round(pct, 1),
    "current_label": state.get("current_label") or "",
    "started_at": state.get("started_at"),
    "updated_at": state.get("updated_at"),
    "finished_at": state.get("finished_at"),
    "error": state.get("error"),
    "n_rows": len(state.get("rows") or []),
  }


def _sort_rows(rows: list[dict], objective: str) -> list[dict]:
  return sorted(rows, key=lambda r: _score(r, objective), reverse=True)


def _save_state(state: dict):
  state["updated_at"] = _now_iso()
  with _lock:
    _write_json(JOB_STATE_PATH, state)


def _worker(run_id: str, specs_data: list[dict], objective: str, config: dict, start_at: int = 0):
  specs = [spec_from_dict(s) for s in specs_data]
  rows: list[dict] = []
  state = load_job_state() or {}
  if start_at > 0:
    rows = list(state.get("rows") or [])

  try:
    for i in range(start_at, len(specs)):
      if _cancel.is_set():
        rows = _sort_rows(rows, objective)
        seed = (config or {}).get("seed_rows") or []
        if seed:
          from gui.grid_search_engine import merge_grid_results
          rows = merge_grid_results(seed, rows, objective=objective)
        if rows:
          save_grid_run(rows, config=config, objective=objective, run_id=run_id)
        state["status"] = "cancelled"
        state["finished_at"] = _now_iso()
        state["rows"] = _sort_rows(rows, objective)
        _save_state(state)
        return

      spec = specs[i]
      state.update({
        "status": "running",
        "run_id": run_id,
        "objective": objective,
        "config": config,
        "specs": specs_data,
        "total": len(specs),
        "done": i,
        "current_label": spec.label(),
        "rows": rows,
      })
      _save_state(state)

      try:
        rows.append(run_single(spec))
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

      rows = _sort_rows(rows, objective)
      state["done"] = i + 1
      state["rows"] = rows
      state["current_label"] = spec.label()
      _save_state(state)

    rows = _sort_rows(rows, objective)
    seed = (config or {}).get("seed_rows") or []
    if seed:
      from gui.grid_search_engine import merge_grid_results
      rows = merge_grid_results(seed, rows, objective=objective)
    save_grid_run(rows, config=config, objective=objective, run_id=run_id)
    state.update({
      "status": "completed",
      "done": len(specs),
      "rows": rows,
      "current_label": "",
      "finished_at": _now_iso(),
      "error": None,
    })
    _save_state(state)
  except Exception as e:
    state = load_job_state() or state
    state.update({
      "status": "error",
      "error": str(e),
      "finished_at": _now_iso(),
      "rows": rows,
    })
    _save_state(state)


def start_grid_search(
  specs: list[GridSpec],
  *,
  objective: str,
  config: dict,
  run_id: str | None = None,
) -> str:
  """Khởi chạy grid search nền. Trả về run_id."""
  global _thread

  if is_grid_running():
    raise RuntimeError("Grid search đang chạy — hủy hoặc đợi hoàn thành.")

  if not specs:
    raise RuntimeError(
      "Không có combo để chạy — huấn luyện đủ 3 giai đoạn KB (theo Cài đặt) trước."
    )

  stop_grid_search(wait=True)

  ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
  rid = run_id or f"gs_{ts}"
  specs_data = [spec_to_dict(s) for s in specs]

  state = {
    "status": "running",
    "run_id": rid,
    "objective": objective,
    "config": config,
    "specs": specs_data,
    "total": len(specs),
    "done": 0,
    "current_label": "",
    "rows": [],
    "started_at": _now_iso(),
    "updated_at": _now_iso(),
    "finished_at": None,
    "error": None,
  }
  _save_state(state)

  _cancel.clear()
  _thread = threading.Thread(
    target=_worker,
    args=(rid, specs_data, objective, config),
    name="grid-search-bg",
    daemon=True,
  )
  _thread.start()
  return rid


def stop_grid_search(*, wait: bool = True):
  """Hủy grid search đang chạy."""
  global _thread
  _cancel.set()
  if _thread and _thread.is_alive():
    if wait:
      _thread.join(timeout=5)
  _thread = None


def ensure_grid_worker_running():
  """Khôi phục worker nếu server restart giữa chừng."""
  global _thread
  state = load_job_state()
  if not state or state.get("status") != "running":
    return
  if _thread is not None and _thread.is_alive():
    return

  done = int(state.get("done") or 0)
  total = int(state.get("total") or 0)
  if done >= total:
    state["status"] = "completed"
    state["finished_at"] = _now_iso()
    _save_state(state)
    return

  specs_data = state.get("specs") or []
  if not specs_data:
    state["status"] = "error"
    state["error"] = "Thiếu danh sách specs — không thể tiếp tục."
    _save_state(state)
    return

  _cancel.clear()
  _thread = threading.Thread(
    target=_worker,
    args=(
      state["run_id"],
      specs_data,
      state.get("objective", "total_r"),
      state.get("config") or {},
      done,
    ),
    name="grid-search-bg",
    daemon=True,
  )
  _thread.start()
