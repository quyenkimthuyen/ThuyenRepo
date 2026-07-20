"""Long-running tasks — backtest, học KB, so sánh — chạy nền."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from run_backtest import REPORT_DIR

JOBS_DIR = REPORT_DIR / "jobs"
JOB_STATE_PATH = JOBS_DIR / "long_task_state.json"

JOB_LABELS = {
  "backtest": "Kiểm chứng backtest",
  "learning": "Huấn luyện bộ nhớ",
  "era_learn": "Học profile giai đoạn",
  "era_compare": "So sánh giai đoạn",
  "epoch_sweep": "Kiểm chứng từng vòng học",
  "train_window": "So sánh cửa sổ học",
}

_lock = threading.Lock()
_thread: threading.Thread | None = None
_cancel = threading.Event()


class JobCancelled(Exception):
  pass


def _now_iso() -> str:
  return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def load_job_state() -> dict | None:
  return _read_json(JOB_STATE_PATH)


def _save_state(state: dict):
  state["updated_at"] = _now_iso()
  with _lock:
    _write_json(JOB_STATE_PATH, state)


def _check_cancel():
  if _cancel.is_set():
    raise JobCancelled()


def _update_progress(state: dict, done: int, total: int, text: str = ""):
  state["done"] = done
  state["total"] = max(total, 1)
  state["progress_text"] = text
  _save_state(state)


def is_task_running() -> bool:
  state = load_job_state()
  if not state or state.get("status") != "running":
    return False
  return _thread is not None and _thread.is_alive()


def get_task_status() -> dict:
  state = load_job_state() or {}
  alive = _thread is not None and _thread.is_alive()
  status = state.get("status", "idle")
  if status == "running" and not alive:
    status = "interrupted"
  total = int(state.get("total") or 0)
  done = int(state.get("done") or 0)
  pct = (done / total * 100) if total else 0
  jt = state.get("job_type") or ""
  return {
    "status": status,
    "running": alive and status == "running",
    "job_type": jt,
    "job_label": state.get("label") or JOB_LABELS.get(jt, jt or "Task"),
    "job_id": state.get("job_id"),
    "total": total,
    "done": done,
    "pct": round(pct, 1),
    "progress_text": state.get("progress_text") or "",
    "started_at": state.get("started_at"),
    "updated_at": state.get("updated_at"),
    "finished_at": state.get("finished_at"),
    "error": state.get("error"),
    "result": state.get("result"),
    "params": state.get("params"),
  }


def _finish(state: dict, *, status: str, error: str | None = None, result: dict | None = None):
  state["status"] = status
  state["error"] = error
  state["finished_at"] = _now_iso()
  if result is not None:
    state["result"] = result
  if status in ("completed", "cancelled", "error"):
    state["progress_text"] = ""
  _save_state(state)


def _worker_backtest(state: dict):
  from gui.services import execute_backtest

  p = state["params"]

  def on_prog(step, total, _ws):
    _check_cancel()
    _update_progress(state, step, total, f"WF {step}/{total}")

  report = execute_backtest(
    use_learning=p["use_learning"],
    train_months=p["train_months"],
    start_date=p.get("start_date", "2022-01-01"),
    spread_pips=p["spread_pips"],
    slippage_pips=p["slippage_pips"],
    holdout_months=int(p.get("holdout_months") or 0),
    kb_profile=p.get("kb_profile"),
    kb_snapshot=p.get("kb_snapshot"),
    oos_from=p.get("oos_from"),
    oos_to=p.get("oos_to"),
    on_progress=on_prog,
    archive=bool(p.get("archive")),
    archive_label=p.get("archive_label"),
    sync_workspace=True,
  )

  result = {
    "total_r": (report.get("overall_oos") or {}).get("total_r"),
    "kb_compare": False,
  }

  if p.get("compare_kb_off"):
    _check_cancel()
    _update_progress(state, 0, 1, "KB OFF…")

    def on_prog2(step, total, _ws):
      _check_cancel()
      _update_progress(state, step, total, f"KB OFF · WF {step}/{total}")

    report_off = execute_backtest(
      use_learning=False,
      train_months=p["train_months"],
      start_date=p.get("start_date", "2022-01-01"),
      spread_pips=p["spread_pips"],
      slippage_pips=p["slippage_pips"],
      holdout_months=int(p.get("holdout_months") or 0),
      oos_from=p.get("oos_from"),
      oos_to=p.get("oos_to"),
      on_progress=on_prog2,
      archive=bool(p.get("archive")),
      sync_workspace=False,
    )
    aux = JOBS_DIR / f"{state['job_id']}_kb_compare.json"
    _write_json(aux, {"kb_on": report, "kb_off": report_off})
    result["kb_compare"] = True

  _finish(state, status="completed", result=result)


def _worker_learning(state: dict):
  from gui.services import execute_learning

  p = state["params"]

  def on_ep(ep, total, _):
    _check_cancel()
    _update_progress(state, ep, total, f"Epoch {ep}/{total}")

  report = execute_learning(
    epochs=int(p["epochs"]),
    reset_kb=bool(p.get("reset_kb")),
    kb_profile=p["kb_profile"],
    kb_name=p.get("kb_name"),
    from_date=p["from_date"],
    until_date=p.get("until_date"),
    on_epoch_done=on_ep,
  )
  _finish(state, status="completed", result={
    "kb_profile": report.get("kb_profile"),
    "epochs": report.get("epochs"),
  })


def _worker_era_learn(state: dict):
  from gui.era_compare import discover_era_specs, ensure_profile_learned

  p = state["params"]
  era_key = p["era_key"]
  catalog = {s["key"]: s for s in discover_era_specs()}
  spec = catalog.get(era_key)
  if not spec:
    raise ValueError(f"Không tìm thấy giai đoạn `{era_key}`.")
  _update_progress(state, 0, 1, p.get("label") or era_key)
  _check_cancel()
  ensure_profile_learned(spec, epochs=int(p["epochs"]), reset=bool(p.get("reset")))
  _finish(state, status="completed", result={"era_key": era_key})


def _worker_era_compare(state: dict):
  from gui.era_compare import run_era_compare_backtests

  p = state["params"]

  def on_prog(i, total, label):
    _check_cancel()
    _update_progress(state, i + 1, total, label)

  reports = run_era_compare_backtests(
    on_progress=on_prog,
    epoch_by_key=p.get("epoch_by_key"),
    profile_keys=p.get("profile_keys"),
  )
  _finish(state, status="completed", result={"keys": list(reports.keys())})


def _worker_epoch_sweep(state: dict):
  from gui.epoch_compare import run_epoch_sweep

  p = state["params"]

  def on_prog(step, total, key):
    _check_cancel()
    _update_progress(state, step, total, f"Epoch {step}/{total}: {key}")

  reports = run_epoch_sweep(
    p["profile_id"],
    p["oos_from"],
    p["oos_to"],
    on_progress=on_prog,
  )
  _finish(state, status="completed", result={
    "profile_id": p["profile_id"],
    "n_epochs": len(reports),
  })


def _worker_train_window(state: dict):
  from gui.train_window_compare import run_train_window_matrix

  p = state["params"]

  def on_prog(step, total, label):
    _check_cancel()
    _update_progress(state, step, total, label)

  reports = run_train_window_matrix(
    p["train_months_list"],
    oos_from=p["oos_from"],
    oos_to=p["oos_to"],
    kb_profile=p["kb_profile"],
    on_progress=on_prog,
  )
  _finish(state, status="completed", result={
    "n_runs": len(reports),
    "train_months": p["train_months_list"],
  })


_DISPATCH = {
  "backtest": _worker_backtest,
  "learning": _worker_learning,
  "era_learn": _worker_era_learn,
  "era_compare": _worker_era_compare,
  "epoch_sweep": _worker_epoch_sweep,
  "train_window": _worker_train_window,
}


def _worker_main():
  state = load_job_state() or {}
  try:
    fn = _DISPATCH.get(state.get("job_type", ""))
    if not fn:
      raise ValueError(f"Job type không hỗ trợ: {state.get('job_type')}")
    fn(state)
  except JobCancelled:
    _finish(load_job_state() or state, status="cancelled")
  except Exception as e:
    _finish(load_job_state() or state, status="error", error=str(e))


def start_job(
  job_type: str,
  params: dict,
  *,
  label: str | None = None,
  job_id: str | None = None,
) -> str:
  """Khởi chạy task nền. Trả về job_id."""
  global _thread

  if job_type not in _DISPATCH:
    raise ValueError(f"Job type không hỗ trợ: {job_type}")
  if is_task_running():
    raise RuntimeError("Đang có task chạy nền — đợi hoặc hủy trước.")

  cancel_task(wait=True)

  ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
  jid = job_id or f"job_{job_type}_{ts}"
  state = {
    "status": "running",
    "job_type": job_type,
    "job_id": jid,
    "label": label or JOB_LABELS.get(job_type, job_type),
    "params": params,
    "total": 0,
    "done": 0,
    "progress_text": "Khởi động…",
    "result": None,
    "started_at": _now_iso(),
    "updated_at": _now_iso(),
    "finished_at": None,
    "error": None,
  }
  _save_state(state)

  _cancel.clear()
  _thread = threading.Thread(target=_worker_main, name=f"long-task-{job_type}", daemon=True)
  _thread.start()
  return jid


def cancel_task(*, wait: bool = True):
  """Hủy task đang chạy."""
  global _thread
  _cancel.set()
  if _thread and _thread.is_alive():
    if wait:
      _thread.join(timeout=8)
  _thread = None


def ensure_task_worker_running():
  """Đánh dấu interrupted nếu server restart giữa chừng (không tự chạy lại)."""
  state = load_job_state()
  if not state or state.get("status") != "running":
    return
  if _thread is not None and _thread.is_alive():
    return
  state["status"] = "interrupted"
  state["finished_at"] = _now_iso()
  state["error"] = "Server restart — chạy lại task."
  _save_state(state)


def sync_completed_job_to_session():
  """Đồng bộ kết quả task hoàn thành vào session_state (gọi khi render trang)."""
  import streamlit as st

  state = load_job_state()
  if not state or state.get("status") != "completed":
    return

  jid = state.get("job_id")
  if st.session_state.get("_synced_job_id") == jid:
    return

  jt = state.get("job_type")
  if jt == "backtest":
    from gui.services import load_backtest_report
    report = load_backtest_report(workspace_aware=True)
    if report:
      st.session_state["backtest_report"] = report
    aux = JOBS_DIR / f"{jid}_kb_compare.json"
    if aux.exists():
      st.session_state["lab_kb_compare"] = _read_json(aux)
    else:
      st.session_state.pop("lab_kb_compare", None)
  elif jt == "learning":
    from gui.services import load_learning_report
    lr = load_learning_report()
    if lr:
      st.session_state["learning_report"] = lr
  elif jt == "era_compare":
    from gui.era_compare import load_era_compare_cache
    cache = load_era_compare_cache()
    if cache:
      st.session_state["era_compare_reports"] = cache.get("reports")
      st.session_state["era_compare_epochs"] = (cache.get("meta") or {}).get("epoch_by_key")
  elif jt == "epoch_sweep":
    from gui.epoch_compare import load_epoch_sweep_cache
    p = state.get("params") or {}
    cache = load_epoch_sweep_cache(
      p.get("profile_id", ""),
      p.get("oos_from", ""),
      p.get("oos_to", ""),
    )
    if cache:
      st.session_state["epoch_sweep_reports"] = cache.get("reports")
      st.session_state["epoch_sweep_ctx"] = {
        "profile": cache.get("kb_profile"),
        "oos_from": cache.get("oos_from"),
        "oos_to": cache.get("oos_to"),
      }
  elif jt == "train_window":
    from gui.train_window_compare import load_train_window_cache
    cache = load_train_window_cache()
    if cache:
      st.session_state["tw_reports"] = cache.get("reports")

  st.session_state["_synced_job_id"] = jid
