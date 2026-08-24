"""Long-running tasks — backtest, học KB, so sánh — chạy nền."""
from __future__ import annotations

from config import DEFAULT_FEATURE_PROFILE, DEFAULT_TF

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
  "model_health": "Sức khỏe Trade Model (KB ON/OFF)",
  "remine_health": "Sức khỏe Remine ON/OFF",
  "mining_space_health": "Mining space vs baseline miner",
  "model_checks_suite": "Check Trade Model (tất cả phần thiếu)",
  "kb_then_grid": "Pipeline: học KB → Grid Search",
  "compare_trade": "Compare Trade (multi-model)",
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
  """Atomic-ish JSON write that survives Windows file locks (WinError 5)."""
  import os
  import time
  import shutil

  path.parent.mkdir(parents=True, exist_ok=True)
  payload = json.dumps(data, indent=2, ensure_ascii=False)
  tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
  with open(tmp, "w", encoding="utf-8", newline="\n") as f:
    f.write(payload)
    f.flush()
    try:
      os.fsync(f.fileno())
    except OSError:
      pass

  last_err: OSError | None = None
  for attempt in range(10):
    try:
      os.replace(str(tmp), str(path))
      return
    except OSError as err:
      last_err = err
      time.sleep(0.05 * (attempt + 1))

  try:
    shutil.copyfile(str(tmp), str(path))
    tmp.unlink(missing_ok=True)
    return
  except OSError as err:
    last_err = err

  # Last resort: overwrite destination in place (non-atomic but unlocks UI/jobs).
  try:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
      f.write(payload)
      f.flush()
    tmp.unlink(missing_ok=True)
    return
  except OSError as err:
    last_err = err
  finally:
    try:
      tmp.unlink(missing_ok=True)
    except OSError:
      pass
  if last_err is not None:
    raise last_err
  raise OSError(f"Failed to write {path}")


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
  suite = state.get("_suite")
  if isinstance(suite, dict) and suite.get("n"):
    n = max(int(suite["n"]), 1)
    i = int(suite.get("i") or 0)
    inner = float(done) / max(float(total), 1.0)
    frac = (i + min(max(inner, 0.0), 1.0)) / n
    done = int(round(frac * 1000))
    total = 1000
    label = str(suite.get("label") or "")
    if label:
      text = f"[{i + 1}/{n}] {label}" + (f" · {text}" if text else "")
  state["done"] = done
  state["total"] = max(total, 1)
  if text:
    state["progress_text"] = text
  _save_state(state)


def _complete_or_return(state: dict, result: dict) -> dict:
  """Finish job unless suite runner asked to chain more steps."""
  if state.get("_defer_finish"):
    return result
  _finish(state, status="completed", result=result)
  return result


def is_task_running() -> bool:
  state = load_job_state()
  if not state or state.get("status") != "running":
    return False
  return _thread is not None and _thread.is_alive()


def get_task_status() -> dict:
  state = load_job_state() or {}
  alive = _thread is not None and _thread.is_alive()
  status = state.get("status", "idle")
  total = int(state.get("total") or 0)
  done = int(state.get("done") or 0)
  if status == "running" and not alive:
    # Restart giữa chừng: nếu đã xong hết step thì coi như completed.
    if total > 0 and done >= total:
      status = "completed"
      state["status"] = "completed"
      state["finished_at"] = state.get("finished_at") or _now_iso()
      state["error"] = None
      _save_state(state)
    else:
      status = "interrupted"
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
  from gui.trade_model import save_model_report

  p = state["params"]
  target_model_id = p.get("model_id")
  # Pin report to the model that started the job — never to whichever
  # model happens to be active when the background worker finishes.
  sync_active = not bool(target_model_id)

  def on_prog(step, total, _ws):
    _check_cancel()
    _update_progress(state, step, total, f"WF {step}/{total}")

  report = execute_backtest(
    use_learning=p["use_learning"],
    train_weeks=p["train_weeks"],
    start_date=p.get("start_date", "2022-01-01"),
    spread_pips=p["spread_pips"],
    slippage_pips=p["slippage_pips"],
    holdout_months=int(p.get("holdout_months") or 0),
    kb_profile=p.get("kb_profile"),
    kb_snapshot=p.get("kb_snapshot"),
    oos_from=p.get("oos_from"),
    oos_to=p.get("oos_to"),
    feature_profile=p.get("feature_profile"),
    mining_search_space=p.get("mining_search_space"),
    on_progress=on_prog,
    archive=bool(p.get("archive")),
    archive_label=p.get("archive_label"),
    sync_workspace=sync_active,
  )
  if target_model_id:
    save_model_report(target_model_id, report)

  result = {
    "total_r": (report.get("overall_oos") or {}).get("total_r"),
    "kb_compare": False,
    "model_id": target_model_id,
  }

  if p.get("compare_kb_off"):
    _check_cancel()
    _update_progress(state, 0, 1, "KB OFF…")

    def on_prog2(step, total, _ws):
      _check_cancel()
      _update_progress(state, step, total, f"KB OFF · WF {step}/{total}")

    report_off = execute_backtest(
      use_learning=False,
      train_weeks=p["train_weeks"],
      start_date=p.get("start_date", "2022-01-01"),
      spread_pips=p["spread_pips"],
      slippage_pips=p["slippage_pips"],
      holdout_months=int(p.get("holdout_months") or 0),
      oos_from=p.get("oos_from"),
      oos_to=p.get("oos_to"),
      feature_profile=p.get("feature_profile"),
      mining_search_space=p.get("mining_search_space"),
      on_progress=on_prog2,
      archive=bool(p.get("archive")),
      sync_workspace=False,
    )
    aux = JOBS_DIR / f"{state['job_id']}_kb_compare.json"
    _write_json(aux, {"kb_on": report, "kb_off": report_off})
    result["kb_compare"] = True

  _finish(state, status="completed", result=result)


def _worker_model_health(state: dict):
  """Backtest KB ON (+ optional refresh) and KB OFF for the same Trade Model OOS."""
  from gui.services import execute_backtest
  from gui.trade_model import (
    get_model_by_id,
    save_model_kb_off_report,
    save_model_report,
  )

  p = state["params"]
  model_id = p["model_id"]
  model = get_model_by_id(model_id)
  if not model:
    raise ValueError(f"Trade model `{model_id}` không tồn tại.")

  start_date = p.get("start_date") or "2022-01-01"
  train_weeks = int(p.get("train_weeks") or model.get("train_weeks") or 6)
  spread = float(p.get("spread_pips") or model.get("spread_pips") or 1.0)
  slip = float(p.get("slippage_pips") or model.get("slippage_pips") or 0.3)
  oos_from = p.get("oos_from") or model.get("oos_from")
  oos_to = p.get("oos_to") or model.get("oos_to")
  kb_profile = p.get("kb_profile") or model.get("kb_profile")
  kb_snapshot = p.get("kb_snapshot", model.get("kb_snapshot"))
  refresh_on = bool(p.get("refresh_kb_on", True))
  feature_profile = (
    p.get("feature_profile")
    or model.get("feature_profile")
    or DEFAULT_FEATURE_PROFILE
  )
  mining_search_space = (
    p.get("mining_search_space")
    if "mining_search_space" in p
    else model.get("mining_search_space")
  )

  report_on = None
  if refresh_on:
    def on_prog(step, total, _ws):
      _check_cancel()
      _update_progress(state, step, max(total * 2, 1), f"KB ON · WF {step}/{total}")

    report_on = execute_backtest(
      use_learning=True,
      train_weeks=train_weeks,
      start_date=start_date,
      spread_pips=spread,
      slippage_pips=slip,
      holdout_months=0,
      kb_profile=kb_profile,
      kb_snapshot=kb_snapshot,
      kb_pin_path=model.get("kb_pin_path"),
      oos_from=oos_from,
      oos_to=oos_to,
      feature_profile=feature_profile,
      mining_search_space=mining_search_space,
      on_progress=on_prog,
      archive=False,
      sync_workspace=False,
    )
    save_model_report(model_id, report_on)

  def on_prog_off(step, total, _ws):
    _check_cancel()
    base = total if refresh_on else 0
    _update_progress(
      state, base + step, max((total * 2) if refresh_on else total, 1),
      f"KB OFF · WF {step}/{total}",
    )

  report_off = execute_backtest(
    use_learning=False,
    train_weeks=train_weeks,
    start_date=start_date,
    spread_pips=spread,
    slippage_pips=slip,
    holdout_months=0,
    oos_from=oos_from,
    oos_to=oos_to,
    feature_profile=feature_profile,
    mining_search_space=mining_search_space,
    on_progress=on_prog_off,
    archive=False,
    sync_workspace=False,
  )
  save_model_kb_off_report(model_id, report_off)

  on_r = (report_on or {}).get("overall_oos", {}).get("total_r") if report_on else None
  off_r = (report_off.get("overall_oos") or {}).get("total_r")
  from mt5_bridge.models import conditions_fingerprint, describe_strategy_conditions, get_model_run_params
  run_params = get_model_run_params(model, model_id)
  # Prefer explicit job params (already sourced from same helper in analysis_support).
  if p.get("mining_search_space") is not None or p.get("feature_profile"):
    run_params = {
      **run_params,
      "train_weeks": train_weeks,
      "spread_pips": spread,
      "slippage_pips": slip,
      "oos_from": oos_from,
      "oos_to": oos_to,
      "kb_profile": kb_profile,
      "kb_snapshot": kb_snapshot,
      "feature_profile": feature_profile,
      "mining_search_space": mining_search_space,
    }
  fp = conditions_fingerprint(run_params)
  return _complete_or_return(state, {
    "model_id": model_id,
    "kb_on_total_r": on_r,
    "kb_off_total_r": off_r,
    "conditions_fp": fp,
    "conditions": describe_strategy_conditions(run_params),
  })


def _worker_remine_health(state: dict):
  """Remine ON (weekly mine) vs Remine OFF (freeze first-week strategy)."""
  from gui.services import execute_backtest
  from gui.trade_model import (
    get_model_by_id,
    save_model_remine_off_report,
    save_model_report,
  )

  p = state["params"]
  model_id = p["model_id"]
  model = get_model_by_id(model_id)
  if not model:
    raise ValueError(f"Trade model `{model_id}` không tồn tại.")

  start_date = p.get("start_date") or "2022-01-01"
  train_weeks = int(p.get("train_weeks") or model.get("train_weeks") or 6)
  spread = float(p.get("spread_pips") or model.get("spread_pips") or 1.0)
  slip = float(p.get("slippage_pips") or model.get("slippage_pips") or 0.3)
  oos_from = p.get("oos_from") or model.get("oos_from")
  oos_to = p.get("oos_to") or model.get("oos_to")
  kb_profile = p.get("kb_profile") or model.get("kb_profile")
  kb_snapshot = p.get("kb_snapshot", model.get("kb_snapshot"))
  refresh_on = bool(p.get("refresh_remine_on", False))
  use_kb = bool(model.get("use_kb", True))
  feature_profile = (
    p.get("feature_profile")
    or model.get("feature_profile")
    or DEFAULT_FEATURE_PROFILE
  )
  mining_search_space = (
    p.get("mining_search_space")
    if "mining_search_space" in p
    else model.get("mining_search_space")
  )

  report_on = None
  if refresh_on:
    def on_prog_on(step, total, _ws):
      _check_cancel()
      _update_progress(
        state, step, max(total * 2, 1), f"Remine ON · WF {step}/{total}",
      )

    report_on = execute_backtest(
      use_learning=use_kb,
      train_weeks=train_weeks,
      start_date=start_date,
      spread_pips=spread,
      slippage_pips=slip,
      holdout_months=0,
      kb_profile=kb_profile,
      kb_snapshot=kb_snapshot,
      kb_pin_path=model.get("kb_pin_path"),
      oos_from=oos_from,
      oos_to=oos_to,
      feature_profile=feature_profile,
      mining_search_space=mining_search_space,
      remine_each_week=True,
      on_progress=on_prog_on,
      archive=False,
      sync_workspace=False,
    )
    save_model_report(model_id, report_on)

  def on_prog_off(step, total, _ws):
    _check_cancel()
    base = total if refresh_on else 0
    _update_progress(
      state, base + step, max((total * 2) if refresh_on else total, 1),
      f"Remine OFF · WF {step}/{total}",
    )

  report_off = execute_backtest(
    use_learning=use_kb,
    train_weeks=train_weeks,
    start_date=start_date,
    spread_pips=spread,
    slippage_pips=slip,
    holdout_months=0,
    kb_profile=kb_profile,
    kb_snapshot=kb_snapshot,
    kb_pin_path=model.get("kb_pin_path"),
    oos_from=oos_from,
    oos_to=oos_to,
    feature_profile=feature_profile,
    mining_search_space=mining_search_space,
    remine_each_week=False,
    on_progress=on_prog_off,
    archive=False,
    sync_workspace=False,
  )
  save_model_remine_off_report(model_id, report_off)

  on_r = (report_on or {}).get("overall_oos", {}).get("total_r") if report_on else None
  off_r = (report_off.get("overall_oos") or {}).get("total_r")
  return _complete_or_return(state, {
    "model_id": model_id,
    "remine_on_total_r": on_r,
    "remine_off_total_r": off_r,
    "remine_mode_off": "freeze_first",
  })


def _worker_mining_space_health(state: dict):
  """Same KB/train/OOS as model, but mining space = baseline miner for A/B."""
  from gui.services import execute_backtest
  from gui.trade_model import (
    get_model_by_id,
    save_model_mining_baseline_report,
    save_model_report,
  )
  from mining_presets import get_preset

  p = state["params"]
  model_id = p["model_id"]
  model = get_model_by_id(model_id)
  if not model:
    raise ValueError(f"Trade model `{model_id}` không tồn tại.")

  start_date = p.get("start_date") or "2022-01-01"
  train_weeks = int(p.get("train_weeks") or model.get("train_weeks") or 6)
  spread = float(p.get("spread_pips") or model.get("spread_pips") or 1.0)
  slip = float(p.get("slippage_pips") or model.get("slippage_pips") or 0.3)
  oos_from = p.get("oos_from") or model.get("oos_from")
  oos_to = p.get("oos_to") or model.get("oos_to")
  kb_profile = p.get("kb_profile") or model.get("kb_profile")
  kb_snapshot = p.get("kb_snapshot", model.get("kb_snapshot"))
  feature_profile = (
    p.get("feature_profile")
    or model.get("feature_profile")
    or DEFAULT_FEATURE_PROFILE
  )
  active_space = (
    p.get("mining_search_space")
    if "mining_search_space" in p
    else model.get("mining_search_space")
  )
  refresh_active = bool(p.get("refresh_active", False))
  baseline_space = get_preset("baseline")

  report_active = None
  if refresh_active:
    def on_prog_active(step, total, _ws):
      _check_cancel()
      _update_progress(
        state, step, max(total * 2, 1), f"Active space · WF {step}/{total}",
      )

    report_active = execute_backtest(
      use_learning=bool(model.get("use_kb", True)),
      train_weeks=train_weeks,
      start_date=start_date,
      spread_pips=spread,
      slippage_pips=slip,
      holdout_months=0,
      kb_profile=kb_profile if model.get("use_kb", True) else None,
      kb_snapshot=kb_snapshot if model.get("use_kb", True) else None,
      kb_pin_path=model.get("kb_pin_path") if model.get("use_kb", True) else None,
      oos_from=oos_from,
      oos_to=oos_to,
      feature_profile=feature_profile,
      mining_search_space=active_space,
      on_progress=on_prog_active,
      archive=False,
      sync_workspace=False,
    )
    save_model_report(model_id, report_active)

  def on_prog_base(step, total, _ws):
    _check_cancel()
    base = total if refresh_active else 0
    _update_progress(
      state,
      base + step,
      max((total * 2) if refresh_active else total, 1),
      f"Baseline miner · WF {step}/{total}",
    )

  report_base = execute_backtest(
    use_learning=bool(model.get("use_kb", True)),
    train_weeks=train_weeks,
    start_date=start_date,
    spread_pips=spread,
    slippage_pips=slip,
    holdout_months=0,
    kb_profile=kb_profile if model.get("use_kb", True) else None,
    kb_snapshot=kb_snapshot if model.get("use_kb", True) else None,
    kb_pin_path=model.get("kb_pin_path") if model.get("use_kb", True) else None,
    oos_from=oos_from,
    oos_to=oos_to,
    feature_profile=feature_profile,
    mining_search_space=baseline_space,
    on_progress=on_prog_base,
    archive=False,
    sync_workspace=False,
  )
  save_model_mining_baseline_report(model_id, report_base)

  active_r = (
    (report_active or {}).get("overall_oos", {}).get("total_r")
    if report_active else None
  )
  base_r = (report_base.get("overall_oos") or {}).get("total_r")
  return _complete_or_return(state, {
    "model_id": model_id,
    "active_total_r": active_r,
    "baseline_total_r": base_r,
    "compared_presets": ["active", "baseline"],
  })


def _worker_model_checks_suite(state: dict):
  """Run missing health checks sequentially (one background slot)."""
  steps = [str(x) for x in (state.get("params") or {}).get("steps") or []]
  allowed = {"model_health", "remine_health", "mining_space_health"}
  steps = [s for s in steps if s in allowed]
  if not steps:
    raise ValueError("Không có bước check nào để chạy.")

  runners = {
    "model_health": _worker_model_health,
    "remine_health": _worker_remine_health,
    "mining_space_health": _worker_mining_space_health,
  }
  by_step: dict = {}
  state["_defer_finish"] = True
  try:
    for i, step in enumerate(steps):
      _check_cancel()
      state["_suite"] = {
        "i": i,
        "n": len(steps),
        "label": JOB_LABELS.get(step, step),
      }
      _update_progress(state, 0, 1, "bắt đầu")
      # Per-step refresh flags already on params from analysis_support
      by_step[step] = runners[step](state) or {}
    state.pop("_suite", None)
  finally:
    state.pop("_defer_finish", None)
    state.pop("_suite", None)

  _finish(state, status="completed", result={
    "model_id": (state.get("params") or {}).get("model_id"),
    "steps_done": steps,
    "by_step": by_step,
    "n_steps": len(steps),
  })


def _worker_learning(state: dict):
  import os
  import sys

  # Background thread under Streamlit can have stdout/stderr is None → tqdm/.write crash.
  for name in ("stdout", "stderr"):
    if getattr(sys, name, None) is None:
      setattr(sys, name, open(os.devnull, "w", encoding="utf-8", errors="replace"))

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


def _worker_kb_then_grid(state: dict):
  """Học mọi giai đoạn trong Cài đặt → chạy Grid Search theo Settings."""
  import os
  import sys

  for name in ("stdout", "stderr"):
    if getattr(sys, name, None) is None:
      setattr(sys, name, open(os.devnull, "w", encoding="utf-8", errors="replace"))

  from gui.app_settings import get_settings, resolve_learning_eras, settings_grid_signature
  from gui.era_compare import ensure_profile_learned
  from gui.grid_search_engine import (
    build_grid_from_settings,
    expected_grid_count_from_settings,
    run_grid,
    save_grid_run,
  )
  from gui.grid_search_background import is_grid_running

  if is_grid_running():
    raise RuntimeError("Grid Search đang chạy riêng — hủy/đợi trước khi chạy pipeline.")

  p = state["params"]
  reset = bool(p.get("reset_kb"))
  settings = get_settings()
  eras = resolve_learning_eras(settings)
  if not eras:
    raise ValueError("Cài đặt chưa chọn giai đoạn học nào.")
  loops = int(settings.get("learning_loops") or 4)
  expected_grid = expected_grid_count_from_settings(settings)
  # Progress units: 1 per era learn phase + 1 per grid combo.
  total_units = max(len(eras) + max(expected_grid, 1), 1)
  done_units = 0

  learned = []
  skipped = []
  for era in eras:
    _check_cancel()
    label = era.get("label") or era.get("kb_profile")
    _update_progress(
      state, done_units, total_units,
      f"Học KB · {label} ({loops} vòng)",
    )
    spec = {
      "kb_profile": era["kb_profile"],
      "kb_name": era.get("label") or era["kb_profile"],
      "learn_from": era["learn_from"],
      "learn_until": era["learn_until"],
    }
    out = ensure_profile_learned(spec, epochs=loops, reset=reset)
    if out.get("skipped"):
      skipped.append(era["kb_profile"])
    else:
      learned.append(era["kb_profile"])
    done_units += 1
    _update_progress(
      state, done_units, total_units,
      f"Xong KB · {label}",
    )

  _check_cancel()
  specs, config = build_grid_from_settings(settings)
  if not specs:
    raise RuntimeError("Không có combo Grid — kiểm tra Cài đặt (train / era / mining).")

  # Re-scale remaining progress to actual combo count.
  total_units = done_units + len(specs)
  objective = str(
    p.get("objective")
    or settings.get("grid_objective")
    or "risk_adjusted"
  )

  def on_prog(i, total, label):
    _check_cancel()
    _update_progress(
      state,
      done_units + i,
      done_units + total,
      f"Grid {i}/{total}: {label}",
    )

  rows = run_grid(specs, objective=objective, on_progress=on_prog)
  rid = save_grid_run(
    rows,
    config={
      **config,
      "timeframe": DEFAULT_TF,
      "source": "kb_then_grid",
      "settings_signature": settings_grid_signature(settings),
    },
    objective=objective,
  )
  ok = [x for x in rows if not x.get("error")]
  best = ok[0] if ok else None
  _finish(state, status="completed", result={
    "run_id": rid,
    "n_combos": len(rows),
    "n_ok": len(ok),
    "learned": learned,
    "skipped": skipped,
    "best_label": (best or {}).get("label"),
    "best_total_r": (best or {}).get("total_r"),
    "best_win_rate_pct": (best or {}).get("win_rate_pct"),
  })


def _worker_compare_trade(state: dict):
  """Multi-model history compare — no EA, MT5 cache + Python paper fills."""
  import os
  import sys

  for name in ("stdout", "stderr"):
    if getattr(sys, name, None) is None:
      setattr(sys, name, open(os.devnull, "w", encoding="utf-8", errors="replace"))

  from mt5_bridge.compare_runner import run_compare

  p = state["params"]
  model_ids = list(p.get("model_ids") or [])
  date_from = str(p.get("date_from") or "")
  date_to = str(p.get("date_to") or "")
  risk_pct = float(p.get("risk_pct") or 1.0)
  if len(model_ids) < 2:
    raise ValueError("Cần ≥2 trade model để Compare Trade.")
  if not date_from or not date_to:
    raise ValueError("Thiếu date_from / date_to.")

  def on_prog(info: dict):
    _check_cancel()
    done = int(info.get("bars_done") or 0)
    total = int(info.get("bars_total") or 1)
    last = info.get("last_bar") or ""
    _update_progress(
      state, done, total,
      f"Bar {done}/{total}" + (f" · {last}" if last else ""),
    )

  try:
    run = run_compare(
      model_ids=model_ids,
      date_from=date_from,
      date_to=date_to,
      risk_pct=risk_pct,
      on_progress=on_prog,
      should_cancel=lambda: _cancel.is_set(),
    )
  except InterruptedError as e:
    raise JobCancelled(str(e)) from e
  _finish(state, status="completed", result={
    "run_id": run.get("run_id"),
    "n_models": len(model_ids),
    "bars_done": run.get("bars_done"),
    "bars_total": run.get("bars_total"),
    "per_model": run.get("per_model"),
  })


_DISPATCH = {
  "backtest": _worker_backtest,
  "model_health": _worker_model_health,
  "remine_health": _worker_remine_health,
  "mining_space_health": _worker_mining_space_health,
  "model_checks_suite": _worker_model_checks_suite,
  "learning": _worker_learning,
  "era_learn": _worker_era_learn,
  "era_compare": _worker_era_compare,
  "epoch_sweep": _worker_epoch_sweep,
  "train_window": _worker_train_window,
  "kb_then_grid": _worker_kb_then_grid,
  "compare_trade": _worker_compare_trade,
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
  if _thread is not None and _thread.is_alive():
    raise RuntimeError("Task worker chưa dừng — thử hủy lại sau vài giây.")

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
  """Hủy task đang chạy. Giữ reference nếu worker chưa chết (tránh race start lại)."""
  global _thread
  _cancel.set()
  t = _thread
  if t and t.is_alive():
    if wait:
      t.join(timeout=8)
  if t is None or not t.is_alive():
    if _thread is t:
      _thread = None


def ensure_task_worker_running():
  """Đánh dấu interrupted nếu server restart giữa chừng (không tự chạy lại)."""
  state = load_job_state()
  if not state or state.get("status") != "running":
    return
  if _thread is not None and _thread.is_alive():
    return
  total = int(state.get("total") or 0)
  done = int(state.get("done") or 0)
  if total > 0 and done >= total:
    state["status"] = "completed"
    state["finished_at"] = _now_iso()
    state["error"] = None
  else:
    state["status"] = "interrupted"
    state["finished_at"] = _now_iso()
    state["error"] = "Server restart — chạy lại task."
  _save_state(state)


def dismiss_task():
  """Xóa banner task đã xong / bị gián đoạn / lỗi."""
  state = load_job_state() or {}
  _write_json(JOB_STATE_PATH, {
    "status": "idle",
    "job_type": None,
    "job_id": None,
    "label": None,
    "params": {},
    "total": 0,
    "done": 0,
    "progress_text": "",
    "result": None,
    "started_at": None,
    "updated_at": _now_iso(),
    "finished_at": None,
    "error": None,
    "dismissed_from": state.get("job_id"),
  })


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
